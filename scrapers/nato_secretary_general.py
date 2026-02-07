#
# nato_secretary_general.py
# Created by V. Akyildiz on 21 January 2026.
# Copyright © 2026 FigureWatch. All rights reserved.
#

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re
import time
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import Database

class RutteCalendarScraper:
    def __init__(self):
        self.base_url = "https://www.nato.int"
        self.advisories_url = "https://www.nato.int/en/news-and-events/events/media-advisories"
        self.db = Database()
        self.org_id = self.db.add_organization("NATO")
        
    def scrape(self):
        """Scrape NATO Secretary General Mark Rutte's schedule"""
        driver = None
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
            
            print("Starting Chrome browser...")
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=chrome_options
            )
            
            # Step 1: Load the media advisories page
            print("Fetching NATO media advisories list...")
            driver.get(self.advisories_url)
            time.sleep(3)
            
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Step 2: Find the most recent advisory with "Secretary General"
            advisory_link = None
            advisory_title = None
            
            all_links = soup.find_all('a', href=True)
            
            for link in all_links:
                title = link.get_text(strip=True)
                href = link.get('href', '')
                
                if 'Secretary General' in title and ('/2026/' in href or '/2025/' in href):
                    advisory_link = href if href.startswith('http') else self.base_url + href
                    advisory_title = title
                    print(f"✓ Found advisory: {title[:80]}...")
                    break
            
            if not advisory_link:
                print("✗ No recent Secretary General advisory found")
                return
            
            # Step 3: Load the advisory detail page
            print(f"Fetching advisory details...")
            driver.get(advisory_link)
            time.sleep(2)
            
            advisory_page = driver.page_source
            advisory_soup = BeautifulSoup(advisory_page, 'html.parser')
            
            # Step 4: Extract information
            full_text = advisory_soup.get_text()
            
            location = self._extract_location(full_text)
            date_range = self._extract_date_range(full_text)
            purpose = self._extract_purpose(advisory_title)
            
            if not location or not date_range:
                print("✗ Could not extract required information")
                return
            
            # Save to database
            self.db.add_or_update_figure(
                name="Secretary General, Mark Rutte",
                location=location,
                date_time=date_range,
                purpose=purpose,
                category_type="organization",
                category_id=self.org_id,
                source_url=advisory_link
            )
            
            print(f"\n{'='*50}")
            print(f"✓ Updated Mark Rutte:")
            print(f"  Location: {location}")
            print(f"  Time: {date_range}")
            print(f"  Purpose: {purpose}")
            print(f"{'='*50}")
            
        except Exception as e:
            print(f"✗ Error scraping NATO: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            if driver:
                driver.quit()
    
    def _extract_location(self, text):
        """Extract location from page text"""
        # Find all City, Country patterns
        city_country_matches = re.findall(r'([A-Z][a-zA-Z]+),\s*([A-Z][a-zA-Z]+)', text)
        
        # Filter out non-location patterns (like "General, Mr" or "Women, Peace")
        location_keywords = ['Switzerland', 'Belgium', 'France', 'Germany', 'United States', 
                           'Poland', 'Finland', 'Netherlands', 'Latvia', 'Estonia', 
                           'Lithuania', 'Norway', 'Denmark', 'Canada', 'United Kingdom',
                           'Italy', 'Spain', 'Portugal', 'Greece', 'Turkey', 'Romania',
                           'Bulgaria', 'Croatia', 'Slovenia', 'Slovakia', 'Czech Republic',
                           'Hungary', 'Albania', 'Montenegro', 'North Macedonia']
        
        for city, country in city_country_matches:
            if country in location_keywords:
                location = f"{city}, {country}"
                print(f"✓ Extracted location: {location}")
                return location
        
        print("⚠ Could not extract location")
        return "Location TBD"
    
    def _extract_date_range(self, text):
        """Extract date range from page text"""
        # Find all single dates first
        single_dates = re.findall(r'(\d{1,2})\s+([A-Z][a-z]+)\s+(\d{4})', text)
        
        if len(single_dates) >= 2:
            # If we have multiple dates, create a range from first to last
            start_day, start_month, start_year = single_dates[0]
            end_day, end_month, end_year = single_dates[1]
            
            # Check if same month and year
            if start_month == end_month and start_year == end_year:
                date_range = f"{start_day}-{end_day} {start_month} {start_year}"
                print(f"✓ Extracted date range: {date_range}")
                return date_range
            else:
                # Different months, show full range
                date_range = f"{start_day} {start_month} - {end_day} {end_month} {start_year}"
                print(f"✓ Extracted date range: {date_range}")
                return date_range
        
        elif len(single_dates) == 1:
            # Single date event
            day, month, year = single_dates[0]
            date_range = f"{day} {month} {year}"
            print(f"✓ Extracted date: {date_range}")
            return date_range
        
        print("⚠ Could not extract date")
        return "Date TBD"
    
    def _extract_purpose(self, title):
        """Extract purpose from advisory title"""
        # Remove "NATO Secretary General to " prefix
        purpose = re.sub(r'^NATO\s+Secretary\s+General\s+(to\s+)?', '', title, flags=re.IGNORECASE)
        
        # Remove any dates and everything after
        purpose = re.split(r'\d{1,2}\s+[A-Z][a-z]+\s+\d{4}', purpose)[0]
        
        # Clean up
        purpose = purpose.strip()
        
        # Capitalize first letter
        if purpose and purpose[0].islower():
            purpose = purpose[0].upper() + purpose[1:]
        
        # Add period if missing
        if purpose and not purpose.endswith('.'):
            purpose += '.'
        
        # Limit length
        if len(purpose) > 200:
            purpose = purpose[:197] + '...'
        
        if purpose and len(purpose) > 10:
            print(f"✓ Extracted purpose: {purpose}")
            return purpose
        
        print("⚠ Could not extract purpose")
        return "Official visit."

def main():
    scraper = RutteCalendarScraper()
    scraper.scrape()

if __name__ == "__main__":
    main()
