from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import re
import time

def is_likely_company_url(url):
    excluded_domains = ['linkedin.com', 'twitter.com', 'facebook.com', 'typeform.com', 'runtime.vc']
    return url.startswith('http') and not any(domain in url for domain in excluded_domains)

def find_company_urls(page):
    print("Scrolling page to load all content...")
    
    # Scroll to the bottom of the page
    page.evaluate('''
        () => {
            return new Promise((resolve) => {
                let totalHeight = 0;
                const distance = 100;
                const timer = setInterval(() => {
                    const scrollHeight = document.body.scrollHeight;
                    window.scrollBy(0, distance);
                    totalHeight += distance;
                    
                    if(totalHeight >= scrollHeight){
                        clearInterval(timer);
                        resolve();
                    }
                }, 100);
            });
        }
    ''')
    
    print("Finished scrolling, now collecting URLs...")
    
    # Collect all potential company URLs
    all_urls = page.evaluate('''
        () => {
            const links = document.querySelectorAll('a[href]');
            return Array.from(links).map(link => link.href);
        }
    ''')
    
    company_urls = [url for url in all_urls if is_likely_company_url(url)]
    
    return list(set(company_urls))  # Remove duplicates

def handle_popups(page):
    # Common cookie acceptance button selectors
    selectors = [
        'button[id*="accept"]',
        'button[class*="accept"]',
        'button[id*="cookie"]',
        'button[class*="cookie"]',
        '[id*="accept-cookies"]',
        '[class*="accept-cookies"]',
        'button:has-text("Accept")',
        'button:has-text("Accept All")',
        'button:has-text("I Accept")',
        'button:has-text("Allow")',
        'button:has-text("Got it")',
        'button:has-text("OK")',
    ]
    
    for selector in selectors:
        try:
            page.click(selector, timeout=2000)
            print(f"Clicked popup/cookie button matching: {selector}")
            return True
        except:
            continue
    return False

def scrape_portfolio_page(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_viewport_size({"width": 1280, "height": 1024})
        print(f"Navigating to {url}")
        
        try:
            page.goto(url, timeout=30000)
            page.wait_for_load_state('networkidle')
            
            # Try to handle any popups
            handle_popups(page)
            
            # Wait a bit after handling popups
            page.wait_for_timeout(2000)
            
        except PlaywrightTimeoutError:
            print("Page load timed out. Proceeding with partial content.")

        print("Searching for company URLs")
        company_urls = find_company_urls(page)

        print(f"\nFound {len(company_urls)} potential company URLs.")
        
        with open('company_urls.txt', 'w') as f:
            for url in company_urls:
                f.write(f"{url}\n")
        
        print(f"URLs have been written to company_urls.txt")
        browser.close()
        
        return company_urls