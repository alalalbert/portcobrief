# Portcobrief

#### an easy button for analyzing VC portfolios


Understanding a VC firm's portfolio takes a lot of time. There may be dozens of portfolio companies, some doing apparently-similar work, with homepages that use opaque marketing language. The goal of Portcobrief is to give anyone the ability to understand a VC firm's portfolio without having to spend hours or days poring over the websites of individual portfolio companies.


The script will:
1. Extract company URLs from the portfolio page
2. Validate each URL as a legitimate company website
3. Scrape and summarize each company
4. Generate two output files:
   - `short_summaries.csv`: Brief company descriptions
   - `long_summaries.docx`: Detailed company analyses

## Output Files

### short_summaries.csv
Contains concise company descriptions with:
- Company name
- Website URL  
- Brief summary (50 words max)

### long_summaries.docx
Contains detailed analysis of each company including:
- Full company description
- Key products/services
- Target market
- Notable features

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## Known Limitations & Bugs

### Limitations
- Some websites with heavy JavaScript rendering don't scrape properly
- GPT-3.5 isn't great at figuring out whether a website is for a startup company or for something else
- Rate limiting may affect processing of large portfolios
- GPT-3.5 summaries may occasionally miss technical nuances
- Cookie/popup handling may fail on some sites

### Known Bugs
- Certain SSL certificates may cause scraping failures
- Progress tracking can be inconsistent if the process is interrupted during file writes
- Some non-English websites may return incomplete summaries
