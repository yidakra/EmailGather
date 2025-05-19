import requests
from bs4 import BeautifulSoup
import pandas as pd
from typing import Dict, List, Tuple, Optional
import time
import re
import os
from datetime import datetime
import urllib.parse


class BerlinSchoolScraper:
    def __init__(self):
        self.base_url = "https://www.bildung.berlin.de/Schulverzeichnis/SchulListe.aspx"
        self.school_url = "https://www.bildung.berlin.de/Schulverzeichnis/Schulportrait.aspx"
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        }
        
    def get_school_links(self, page_limit: Optional[int] = None) -> List[Tuple[str, str]]:
        """Get school names and their IDs from the directory page"""
        schools = []
        
        try:
            print(f"\nFetching school links from directory...")
            response = self.session.get(self.base_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all school links in the table
            links = soup.find_all('a', href=lambda href: href and 'Schulportrait.aspx' in href)
            print(f"Found {len(links)} school entries")
            
            for link in links:
                school_name = link.text.strip()
                href = link['href']
                school_id = re.search(r'IDSchulzweig=\s*(\d+)', href)
                
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
    
    def get_school_details(self, school_id: str) -> Dict[str, str]:
        """Extract information from a school's detail page"""
        params = {"IDSchulzweig": school_id}
        
        try:
            response = self.session.get(self.school_url, params=params, headers=self.headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            school_data = {
                "School ID": school_id,
                "School Name": "",
                "School Type": "",
                "Address": "",
                "Postal Code": "",
                "City": "Berlin",
                "Phone": "",
                "Fax": "",
                "Email": "",
                "Principal": "",
                "Additional Info": ""
            }
            
            # Extract school name
            school_name_elem = soup.find('span', id=lambda x: x and 'lblSchulname' in x)
            if school_name_elem:
                school_data["School Name"] = school_name_elem.text.strip()
            
            # Extract school type
            school_type_elem = soup.find('span', id=lambda x: x and 'lblSchulart' in x)
            if school_type_elem:
                school_data["School Type"] = school_type_elem.text.strip()
            
            # Extract address
            address_elem = soup.find('span', id=lambda x: x and 'lblStrasse' in x)
            if address_elem:
                school_data["Address"] = address_elem.text.strip()
            
            # Extract postal code and city
            postal_city_elem = soup.find('span', id=lambda x: x and 'lblOrt' in x)
            if postal_city_elem:
                postal_city_text = postal_city_elem.text.strip()
                postal_match = re.search(r'(\d{5})\s+Berlin', postal_city_text)
                if postal_match:
                    school_data["Postal Code"] = postal_match.group(1)
                    
                    # Extract district if available (in parentheses after Berlin)
                    district_match = re.search(r'Berlin\s+\(([^)]+)\)', postal_city_text)
                    if district_match:
                        school_data["District"] = district_match.group(1)
            
            # Extract phone number
            phone_elem = soup.find('span', id=lambda x: x and 'lblTelefon' in x and 'Text' not in x)
            if phone_elem:
                school_data["Phone"] = phone_elem.text.strip()
            
            # Extract fax number
            fax_elem = soup.find('span', id=lambda x: x and 'lblFax' in x and 'Text' not in x)
            if fax_elem:
                school_data["Fax"] = fax_elem.text.strip()
            
            # Extract email - This is the critical part for the left side school email
            email_elem = soup.find('a', id=lambda x: x and 'HLinkEMail' in x)
            if email_elem:
                href = email_elem.get('href', '')
                if 'mailto:' in href:
                    email = href.replace('mailto:', '').strip()
                    # Decode percent-encoded characters and clean up
                    email = urllib.parse.unquote(email).strip()
                    email = re.sub(r'[\t\n\r]+', '', email)
                    school_data["Email"] = email
                else:
                    email = email_elem.text.strip()
                    email = urllib.parse.unquote(email).strip()
                    email = re.sub(r'[\t\n\r]+', '', email)
                    school_data["Email"] = email
            
            # Extract website
            web_elem = soup.find('a', id=lambda x: x and 'HLinkWeb' in x)
            if web_elem and web_elem.text.strip():
                school_data["Website"] = web_elem.text.strip()
            
            # Extract principal
            principal_elem = soup.find('span', id=lambda x: x and 'lblLeitung' in x and 'Text' not in x)
            if principal_elem:
                principal_text = principal_elem.text.strip()
                # Convert "Surname, FirstName" to "FirstName Surname"
                if ',' in principal_text:
                    surname, first_name = principal_text.split(',', 1)
                    # Handle cases with titles like "Dr."
                    if 'Dr.' in surname:
                        school_data["Principal"] = f"Dr. {first_name.strip()} {surname.replace('Dr.', '').strip()}"
                    else:
                        school_data["Principal"] = f"{first_name.strip()} {surname.strip()}"
                else:
                    school_data["Principal"] = principal_text
            
            # Extract additional information
            additional_info_elem = soup.find('span', id=lambda x: x and 'lblZusatz' in x)
            if additional_info_elem:
                school_data["Additional Info"] = additional_info_elem.text.strip()
            
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
        
        print(f"\nStarting Berlin school directory scraper...")
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
                        
                    # Get school details
                    school_info = self.get_school_details(school_id)
                    
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
                filename = f"berlin_schools_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                df.to_csv(filename, index=False)
                print(f"\nResults saved to: {filename}")
                return df
            else:
                print("No data collected.")
                return pd.DataFrame()


if __name__ == "__main__":
    scraper = BerlinSchoolScraper()
    # Scrape all schools with a 1 second delay between requests
    scraper.scrape_schools(limit=None, delay=1.0) 