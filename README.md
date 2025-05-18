# EmailGather

A collection of tools for gathering email addresses from educational institution websites.

## Overview

This repository contains scripts to scrape email addresses from:

1. Dutch schools (both public and international) - `gather.py`
2. California Department of Education (CDE) school directory - `cde_gather.py`

## Requirements

```
beautifulsoup4==4.12.3
pycurl==7.45.2
selenium==4.18.1
webdriver_manager==4.0.1
pandas (for cde_gather.py)
```

Install dependencies:

```bash
pip install -r requirements.txt
pip install pandas  # for cde_gather.py
```

## Usage

### Dutch Schools Scraper (`gather.py`)

The script can gather emails from either public Dutch schools or international schools in the Netherlands.

```bash
# For public schools:
python gather.py [true|false] -p [proxy_ip proxy_port]

# For international schools:
python gather.py [true|false] -i [proxy_ip proxy_port]
```

Parameters:
- First parameter (`true`/`false`): Whether to use Selenium for dynamic page fetching
- Second parameter (`-p`/`-i`): Target either public (`-p`) or international (`-i`) schools
- Optional proxy parameters: IP address and port for proxy (if needed)

The script will:
1. Collect school website links
2. Search for contact pages
3. Extract email addresses
4. Save results to `emails.txt`
5. Save failed URLs to `failed.txt`

### California Department of Education Scraper (`cde_gather.py`)

This script scrapes administrator information including emails and phone numbers from the California Department of Education school directory.

```bash
python cde_gather.py
```

The script will:
1. Fetch school links from the CDE directory
2. Extract administrator information, emails, and phone numbers
3. Save results to a CSV file named `cde_administrators_[timestamp].csv`

By default, it attempts to scrape all schools. The scraper has built-in delays to avoid overloading the server.

## Output Files

- `emails.txt`: List of gathered emails from Dutch schools
- `failed.txt`: List of URLs that couldn't be processed
- `cde_administrators_[timestamp].csv`: Detailed information from CDE schools

## Notes

- Both scripts use respectful scraping practices with delays between requests
- Proxy support is available for the Dutch schools scraper
- The CDE scraper extracts both emails and phone numbers 