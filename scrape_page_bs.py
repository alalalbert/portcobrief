import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
import openai
import os
from dotenv import load_dotenv
from openai import OpenAI
from requests.exceptions import RequestException
import re
from urllib.robotparser import RobotFileParser
import time
import traceback

# Load environment variables from .env file
load_dotenv()

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def scrape_page(url):
    try:
        print(f"Starting scrape attempt for {url}")
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        print(f"Response status code: {response.status_code}")
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text()
        print(f"Successfully scraped {len(text)} characters from {url}")
        return text
    except requests.exceptions.SSLError as e:
        print(f"SSL Error for {url}: {str(e)}")
        return ""
    except requests.exceptions.TooManyRedirects as e:
        print(f"Too many redirects for {url}: {str(e)}")
        return ""
    except requests.exceptions.ConnectionError as e:
        print(f"Connection error for {url}: {str(e)}")
        return ""
    except RequestException as e:
        print(f"Request error for {url}: {str(e)}")
        return ""
    except Exception as e:
        print(f"Unexpected error scraping {url}: {str(e)}")
        traceback.print_exc()
        return ""

def clean_text(text):
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Remove special characters, keeping basic punctuation
    text = re.sub(r'[^a-zA-Z0-9\s.,!?-]', '', text)
    
    return text

def is_relevant_tag(tag):
    # List of classes or IDs that typically contain main content
    relevant_classes = ['content', 'main', 'article', 'post', 'entry']
    irrelevant_classes = ['header', 'footer', 'nav', 'sidebar', 'menu', 'comment']
    
    if tag.has_attr('class'):
        return any(c in tag.get('class') for c in relevant_classes) and \
               not any(c in tag.get('class') for c in irrelevant_classes)
    if tag.has_attr('id'):
        return any(c in tag.get('id') for c in relevant_classes) and \
               not any(c in tag.get('id') for c in irrelevant_classes)
    return False

def extract_visible_text(soup):
    # Remove script, style, and nav elements
    for element in soup(['script', 'style', 'nav', 'header', 'footer']):
        element.decompose()
    
    # Find the main content area
    main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
    
    if not main_content:
        main_content = soup.find_all(is_relevant_tag)
    
    if not main_content:
        main_content = [soup]  # If no main content found, use the entire body
    
    visible_text = []
    for content in main_content:
        if isinstance(content, str):
            # If content is already a string, clean and add it
            text = clean_text(content)
            if text and len(text) > 20:
                visible_text.append(text)
        else:
            # If content is a tag, process its children
            for tag in content.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']):
                if tag.string:
                    text = clean_text(tag.string)
                    if text and len(text) > 20:  # Only include text longer than 20 characters
                        visible_text.append(text)
    
    return ' '.join(visible_text)

def crawl_website(start_url, max_pages=5, timeout=60):
    visited = set()
    to_visit = [start_url]
    data = {}
    start_domain = urlparse(start_url).netloc

    print(f"Starting to crawl {start_url}")

    # Set up robots.txt parser
    rp = RobotFileParser()
    rp.set_url(urljoin(start_url, "/robots.txt"))
    rp.read()

    overall_start_time = time.time()

    while to_visit and len(visited) < max_pages:
        url = to_visit.pop(0)
        if url not in visited and rp.can_fetch("*", url):
            print(f"Scraping: {url}")
            try:
                start_time = time.time()
                response = requests.get(url, timeout=10, allow_redirects=True)
                response.raise_for_status()
                
                print(f"Retrieved {url} in {time.time() - start_time:.2f} seconds")
                
                # Check if we've been redirected to a different domain
                final_domain = urlparse(response.url).netloc
                if final_domain != start_domain:
                    print(f"Redirected to different domain: {response.url}")
                    continue
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                print(f"Extracting visible text from {url}")
                visible_content = extract_visible_text(soup)
                
                if visible_content:
                    data[url] = visible_content[:5000]  # Limit content to 5000 characters
                    visited.add(url)
                    print(f"Extracted {len(visible_content)} characters from {url}")

                    # Only add new links if we haven't reached the timeout
                    if time.time() - overall_start_time < timeout:
                        for link in soup.find_all('a', href=True):
                            new_url = urljoin(url, link['href'])
                            new_domain = urlparse(new_url).netloc
                            if new_domain == start_domain and new_url not in visited and new_url not in to_visit:
                                to_visit.append(new_url)
                    else:
                        print(f"Overall timeout reached, skipping link extraction for {url}")
                else:
                    print(f"No visible content extracted from {url}")
                
                # Check if we've exceeded the overall timeout
                if time.time() - overall_start_time > timeout:
                    print(f"Overall timeout reached after processing {url}")
                    break
                
            except requests.RequestException as e:
                print(f"Error scraping {url}: {str(e)}")
            except Exception as e:
                print(f"Unexpected error scraping {url}: {str(e)}")
                traceback.print_exc()

    print(f"Crawling completed. Visited {len(visited)} pages.")
    return data

def get_domain(url):
    return urlparse(url).netloc.replace('www.', '')

def get_json_filename(url):
    domain = get_domain(url)
    return f'scraped_data_{domain}.json'

def save_data(data, url):
    filename = get_json_filename(url)
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filename

def load_data(url):
    domain = get_domain(url)
    filename = f'scraped_data_{domain}.json'
    with open(filename, 'r') as f:
        return json.load(f)

def generate_summary_with_openai(loaded_data):
    # Truncate or clean the loaded_data to remove repetitive content
    cleaned_data = clean_and_truncate_data(loaded_data)
    
    # Construct a more concise prompt
    prompt = f"Summarize the following company information concisely:\n\n{cleaned_data}"
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes company information."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150  # Adjust as needed
        )
        return response.choices[0].message.content.strip()
    except openai.BadRequestError as e:
        print(f"Error generating summary: {e}")
        return "Unable to generate summary due to API error."

def clean_and_truncate_data(data, max_length=1000):
    # Remove any HTML tags
    clean_data = re.sub(r'<[^>]+>', '', data)
    
    # Remove excessive whitespace
    clean_data = ' '.join(clean_data.split())
    
    # Truncate to max_length characters
    return clean_data[:max_length]

def generate_brief_summary(summary):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an objective analyst that creates neutral, factual summaries of companies."},
                {"role": "user", "content": f"Based on the following summary, create a brief, neutral summary (no more than 50 words) that objectively describes the company's main product or service, its key features, and its target market. Avoid marketing language or subjective claims. Assume the reader has a strong understanding of the industry the company operates in.:\n\n{summary}"}
            ],
            max_tokens=100  # Adjust as needed
        )
        return response.choices[0].message.content
    except openai.BadRequestError as e:
        print(f"Error generating brief summary: {e}")
        return "Unable to generate brief summary due to API error."

def get_company_name(url):
    domain = get_domain(url)
    # Remove common TLDs and split by dots or dashes
    name_parts = domain.split('.')[0].replace('-', ' ').split()
    # Capitalize each word and join
    return ' '.join(word.capitalize() for word in name_parts)

def validate_company_url(url, client):
    try:
        prompt = f"""Analyze this URL: {url}
        Question: Could this be the URL for a startup/company website, or is it obviously something else (like social media, news, etc.)?
        Please respond with ONLY 'VALID' or 'INVALID' followed by a brief reason.
        Example responses:
        'VALID: Appears to be a company domain'
        'INVALID: This is a LinkedIn profile page'"""
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a URL validator that categorizes URLs as either potential company websites or not."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=50
        )
        
        result = response.choices[0].message.content.strip()
        is_valid = result.upper().startswith('VALID')
        return is_valid, result
        
    except Exception as e:
        print(f"Error validating URL {url}: {str(e)}")
        return True, "VALID: Error during validation, proceeding with caution"

def scrape_and_summarize(company_url, max_pages=5, timeout=60):
    company_name = get_company_name(company_url)
    filename = get_json_filename(company_url)

    print(f"Processing: {company_url}")
    
    # Validate URL first
    is_valid, reason = validate_company_url(company_url, client)
    print(f"URL validation: {reason}")
    if not is_valid:
        return company_name, "Invalid company URL.", "Not a company website.", ""

    # Check if the JSON file already exists
    if os.path.exists(filename):
        print(f"Loading existing data for {company_name}")
        loaded_data = load_data(company_url)
    else:
        print(f"Scraping new data for {company_name}")
        try:
            start_time = time.time()
            scraped_data = crawl_website(company_url, max_pages=max_pages, timeout=timeout)
            
            if not scraped_data:
                print(f"No data could be scraped for {company_name}")
                return company_name, "No data could be scraped.", "No data available.", ""

            print(f"Saving data for {company_name}")
            filename = save_data(scraped_data, company_url)
            loaded_data = scraped_data

            elapsed_time = time.time() - start_time
            print(f"Scraping completed in {elapsed_time:.2f} seconds")

        except Exception as e:
            print(f"Error scraping data for {company_name}: {str(e)}")
            traceback.print_exc()
            return company_name, f"Error scraping data: {str(e)}", "Error occurred.", ""

    print(f"Generating summary for {company_name}")
    try:
        # Combine all scraped text for summarization
        combined_text = " ".join(loaded_data.values())

        summary = generate_summary_with_openai(combined_text)
        brief_summary = generate_brief_summary(summary)
        
        print(f"Summary generated for {company_name}")
        return company_name, summary, brief_summary, filename
    except Exception as e:
        print(f"Error generating summary for {company_name}: {str(e)}")
        traceback.print_exc()
        return company_name, f"Error generating summary: {str(e)}", "Error occurred.", filename
