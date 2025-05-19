import requests
from bs4 import BeautifulSoup
import pandas as pd
from typing import Dict, List, Tuple, Optional
import time
import re
import os
from datetime import datetime
import urllib.parse


class SaxonySchoolScraper:
    def __init__(self):
        self.base_url = "https://schuldatenbank.sachsen.de/index.php"
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        }
        
    def get_school_links(self, page_limit: Optional[int] = None) -> List[Tuple[str, str]]:
        """Get school names and their IDs from the directory page"""
        schools = []
        
        try:
            print(f"\nFetching school links from directory...")
            params = {
                'id': '10',
                'name': '',
                'address': '',
                'school_category_key': '',
                'educational_course': '',
                'advanced_course': '',
                'educational_concept_key': '',
                'full-day_offer': '',
                'community_key': '',
                'owner_id': '',
                'inspectorate_key': '',
                'legal_status_key': '',
                'representation': 'table'
            }
            
            response = self.session.get(self.base_url, params=params, headers=self.headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all school links in the table
            links = soup.find_all('a', href=lambda href: href and 'institution_key=' in href)
            print(f"Found {len(links)} school entries")
            
            for link in links:
                school_name = link.text.strip()
                href = link['href']
                school_id = re.search(r'institution_key=(\d+)', href)
                
                if school_id:
                    school_id_value = school_id.group(1).strip()
                    schools.append((school_name, school_id_value))
                    
                    # Limit number of schools if specified
                    if page_limit and len(schools) >= page_limit:
                        print(f"Reached limit of {page_limit} schools")
                        break
            
            print(f"Successfully extracted {len(schools)} school links")
            return schools
            
        except Exception as e:
            print(f"Error fetching school links: {str(e)}")
            return []
    
    def get_school_details(self, school_id: str, school_name: str) -> Dict[str, str]:
        """Extract information from a school's detail page"""
        params = {
            'id': '100',
            'institution_key': school_id
        }
        
        try:
            response = self.session.get(self.base_url, params=params, headers=self.headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Clean up school name - just remove quotes and handle Grundschule
            school_name = school_name.replace('"', '')  # Remove all quotes
            if school_name.endswith(', Grundschule'):
                school_name = school_name.replace(', Grundschule', ' Grundschule')
            
            school_data = {
                "School ID": school_id,
                "School Name": school_name,
                "School Type": "",
                "Address": "No address found",
                "Postal Code": "No postal code found",
                "City": "No city found",
                "Phone": "",
                "Fax": "",
                "Email": "",
                "Principal": "",
                "Website": "",
                "Additional Info": ""
            }
            
            # Find the Kontakt section
            kontakt_header = soup.find('h3', string='Kontakt')
            if kontakt_header:
                # Get all contact paragraphs
                contact_paragraphs = kontakt_header.find_next_siblings('p', class_=lambda x: x and x.startswith('contact'))
                
                for p in contact_paragraphs:
                    # Extract visitor address
                    if 'contact-visitor' in p['class']:
                        # Get raw text and split on Besucheradresse:
                        address_text = p.get_text(strip=True)
                        if 'Besucheradresse:' in address_text:
                            # Get the content span
                            content_span = p.find('span', class_='contact-content')
                            if content_span:
                                # Get all text nodes directly under the content span
                                address_lines = []
                                for node in content_span.children:
                                    if isinstance(node, str):
                                        text = node.strip()
                                        if text and not 'Zur Karte' in text:
                                            address_lines.append(text)
                                    elif node.name == 'br':
                                        continue
                                    elif node.name == 'a' and 'Zur Karte' not in node.text:
                                        text = node.text.strip()
                                        if text:
                                            address_lines.append(text)
                                
                                # Clean up lines
                                address_lines = [line for line in address_lines if line]
                                if len(address_lines) >= 3:
                                    # Skip the school name
                                    school_data["Address"] = address_lines[1]
                                    # Get postal code and city
                                    city_line = address_lines[2]
                                    postal_match = re.match(r'(\d{5})\s+(.+)', city_line)
                                    if postal_match:
                                        school_data["Postal Code"] = postal_match.group(1)
                                        school_data["City"] = postal_match.group(2)
                    
                    # Extract phone
                    elif 'contact-phone' in p['class']:
                        phone_text = p.get_text(strip=True)
                        if 'Telefon' in phone_text:
                            phone_text = phone_text.split(':', 1)[1].strip()
                            school_data["Phone"] = phone_text
                    
                    # Extract email
                    elif 'contact-mail' in p['class']:
                        email_link = p.find('a')
                        if email_link:
                            school_data["Email"] = email_link.text.strip()
                    
                    # Extract website
                    elif 'contact-homepage' in p['class']:
                        web_link = p.find('a')
                        if web_link:
                            school_data["Website"] = web_link.get('href', '').strip()
            
            # Extract school type from Informationen section
            info_section = soup.find('h3', string='Informationen')
            if info_section:
                # Find the box-body div
                info_body = info_section.find_next('div', class_='box-body')
                if info_body:
                    # Find the Schulart section
                    schulart_h4 = info_body.find('h4', string='Schulart')
                    if schulart_h4:
                        schulart_p = schulart_h4.find_next('p')
                        if schulart_p:
                            # Clean up school type formatting
                            type_text = schulart_p.text.strip()
                            # Add space between Schule and Grundschule
                            type_text = type_text.replace('SchuleGrundschule', 'Schule Grundschule')
                            school_data["School Type"] = type_text
            
            # Extract principal information
            schulleitung_section = soup.find('h3', string='Schulleitung')
            if schulleitung_section:
                box_body = schulleitung_section.find_next('div', class_='box-body')
                if box_body:
                    principals = []
                    for person in box_body.find_all('div', class_='box-person'):
                        name = person.find('h4')
                        title = person.find('div', class_='box-text')
                        if name and title:
                            name_text = name.text.strip()
                            title_text = title.text.replace(name_text, '').strip()
                            principals.append(f"{name_text} ({title_text})")
                    if principals:
                        school_data["Principal"] = ", ".join(principals)
            
            return school_data
            
        except Exception as e:
            print(f"Error fetching details for school ID {school_id}: {str(e)}")
            return {"School ID": school_id, "Error": str(e)}
    
    def scrape_schools(self, limit: Optional[int] = None, delay: float = 1.0) -> pd.DataFrame:
        """
        Scrape school information
        If limit is None, scrape all schools found in the directory
        """
        all_data = []
        schools_needed = limit if limit is not None else float('inf')
        
        print(f"\nStarting Saxony school directory scraper...")
        print(f"Target: {'All schools' if limit is None else f'{limit} schools'}")
        
        try:
            # Get all school links
            schools = self.get_school_links(limit)
            
            for idx, (school_name, school_id) in enumerate(schools, 1):
                if len(all_data) >= schools_needed:
                    break
                
                print(f"\nProcessing school {idx}/{len(schools)}")
                print(f"School: {school_name}")
                print(f"ID: {school_id}")
                
                try:
                    # Add delay to be respectful to the server
                    if idx > 1:
                        time.sleep(delay)
                        
                    # Get school details - pass both school_id and school_name
                    school_info = self.get_school_details(school_id, school_name)
                    
                    # Print found/not found messages for key fields
                    print(f"Email: {school_info.get('Email') or 'No email found'}")
                    print(f"Phone: {school_info.get('Phone') or 'No phone found'}")
                    print(f"Fax: {school_info.get('Fax') or 'No fax found'}")
                    print(f"Principal: {school_info.get('Principal') or 'No principal found'}")
                    print(f"Website: {school_info.get('Website') or 'No website found'}")
                    
                    all_data.append(school_info)
                    
                except Exception as e:
                    print(f"Error processing school {school_name}: {str(e)}")
                    
        except KeyboardInterrupt:
            print("\nScraping interrupted by user. Saving collected data...")
        
        finally:
            if all_data:
                # Create DataFrame and save to CSV
                df = pd.DataFrame(all_data)
                filename = f"saxony_schools_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                # Let pandas handle the CSV escaping
                df.to_csv(filename, index=False, quoting=1)  # QUOTE_ALL
                print(f"\nResults saved to: {filename}")
                return df
            else:
                print("No data collected.")
                return pd.DataFrame()


if __name__ == "__main__":
    scraper = SaxonySchoolScraper()
    # Scrape all schools with a 1 second delay between requests
    scraper.scrape_schools(limit=None, delay=1.0) 