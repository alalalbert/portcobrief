# Some things to think about adding or adjusting

1. Improved handling of javascript-heavy pages (some VCs have v. fancy websites)
2. A better prompt for the LLM to determine if a URL is a company website or not. Possibly putting this step after scraping the homepage.
3. Including companies where scraping failed or was inconclusive in the final output file.
4. Separating out the company scrape and summarize function into a separate file. This might have utility in other projects.