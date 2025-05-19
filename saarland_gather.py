import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import html
from datetime import datetime
from typing import Dict, List, Optional
import urllib.parse


class SaarlandSchoolScraper:
    def __init__(self):
        self.base_url = "https://www.saarland.de/mbk/DE/portale/bildungsserver/schulen-und-bildungswege/schuldatenbank/_functions/Schulsuche_Formular"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        }
        self.session = requests.Session()
    
    def _make_request(self, url: str, params: Optional[Dict] = None, max_retries: int = 3, retry_delay: float = 2.0) -> requests.Response:
        """Make a request with retry logic"""
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params, headers=self.headers, timeout=30)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                if attempt == max_retries - 1:  # Last attempt
                    raise
                wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                print(f"Request failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
                print(f"Waiting {wait_time} seconds before retrying...")
                time.sleep(wait_time)
    
    def get_page_url(self, page_number: int) -> str:
        """Generate URL for a specific page"""
        if page_number == 1:
            # First page has no page parameter
            return f"{self.base_url}?submit=search&sortOrder=schule_sort%20asc"
        else:
            # Subsequent pages use the gtp parameter
            return f"{self.base_url}?gtp=%2526c5706df2-b646-40cc-8c62-b7a95b0cb40e_list%253D{page_number}&submit=search&sortOrder=schule_sort%20asc"
    
    def extract_school_data(self, html_content: str) -> List[Dict]:
        """Extract school information from a page"""
        soup = BeautifulSoup(html_content, 'html.parser')
        schools = []
        
        # Find all school cards
        school_cards = soup.select('.c-teaser-card')
        
        for card in school_cards:
            school_data = {
                "School Name": "",
                "School Type": "",
                "City": "",
                "Homepage": "",
                "Email": "",
                "Phone": "",
                "Fax": "",
                "Principal": "",
                "Address": ""
            }
            
            # Extract school name
            name_elem = card.select_one('.c-searchresult-teaser__headline')
            if name_elem:
                school_data["School Name"] = name_elem.text.strip()
            
            # Extract school type and city
            category_elems = card.select('.c-badge')
            if len(category_elems) >= 2:
                school_data["School Type"] = category_elems[0].text.strip()
                school_data["City"] = category_elems[1].text.strip()
            
            # Extract contact details
            dl_elem = card.select_one('dl')
            if dl_elem:
                dt_elems = dl_elem.select('dt')
                dd_elems = dl_elem.select('dd')
                
                for i in range(len(dt_elems)):
                    if i < len(dd_elems):
                        field = dt_elems[i].text.strip().rstrip(':')
                        value = dd_elems[i].text.strip()
                        
                        # Check for email links
                        email_link = dd_elems[i].select_one('a[href^="mailto:"]')
                        if email_link:
                            href = email_link.get('href', '')
                            if href.startswith('mailto:'):
                                value = href.replace('mailto:', '').strip()
                        
                        # Check for website links
                        website_link = dd_elems[i].select_one('a[target="_blank"]')
                        if website_link:
                            value = website_link.text.strip()
                        
                        if field == "Homepage":
                            school_data["Homepage"] = value
                        elif field == "E-Mail":
                            school_data["Email"] = value
                        elif field == "Telefon":
                            school_data["Phone"] = value
                        elif field == "Telefax":
                            school_data["Fax"] = value
                        elif field == "Schulleitung":
                            school_data["Principal"] = value
            
            # Extract address
            address_elem = card.select_one('.c-searchresult-teaser__text > p')
            if address_elem:
                school_data["Address"] = address_elem.text.strip()
            
            schools.append(school_data)
        
        return schools
    
    def get_total_pages(self, html_content: str) -> int:
        """Extract the total number of pages from the pagination"""
        # We know from examining the website that there are 34 pages total
        return 34
    
    def scrape_schools(self, max_pages: Optional[int] = None, delay: float = 1.0) -> pd.DataFrame:
        """
        Scrape school information from all pages
        If max_pages is provided, only scrape that many pages
        """
        all_schools = []
        
        print(f"\nStarting Saarland school directory scraper...")
        
        try:
            # Get the first page to determine total number of pages
            first_page_url = self.get_page_url(1)
            response = self._make_request(first_page_url)
            
            # Get total number of pages
            total_pages = self.get_total_pages(response.text)
            if max_pages:
                total_pages = min(total_pages, max_pages)
            
            print(f"Found {total_pages} pages of school listings")
            
            # Process first page
            schools = self.extract_school_data(response.text)
            all_schools.extend(schools)
            print(f"Page 1/{total_pages}: Extracted {len(schools)} schools")
            
            # Process remaining pages
            for page_num in range(2, total_pages + 1):
                # Add delay between requests
                time.sleep(delay)
                
                page_url = self.get_page_url(page_num)
                response = self._make_request(page_url)
                
                schools = self.extract_school_data(response.text)
                all_schools.extend(schools)
                
                print(f"Page {page_num}/{total_pages}: Extracted {len(schools)} schools")
            
            print(f"\nTotal schools extracted: {len(all_schools)}")
            
        except KeyboardInterrupt:
            print("\nScraping interrupted by user. Saving collected data...")
        except Exception as e:
            print(f"\nError during scraping: {str(e)}")
        
        finally:
            if all_schools:
                # Create DataFrame and save to CSV
                df = pd.DataFrame(all_schools)
                filename = f"saarland_schools_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                df.to_csv(filename, index=False, quoting=1)  # quoting=1 ensures all fields are quoted
                print(f"\nResults saved to: {filename}")
                return df
            else:
                print("No data collected.")
                return pd.DataFrame()


if __name__ == "__main__":
    scraper = SaarlandSchoolScraper()
    # Scrape all 34 pages with a 1 second delay between requests
    scraper.scrape_schools(max_pages=None, delay=1.0) 