#
# nato_secretary_general.py
# Scraper for NATO Secretary General Mark Rutte
# Created by V. Akyildiz on 31 January 2026.
# Copyright © 2026 FigureWatch. All rights reserved.
#

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from datetime import datetime
import re
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import Database

class RutteCalendarScraper:
    def __init__(self):
        self.base_url = "https://www.nato.int"
        self.advisories_url = "https://www.nato.int/en/news-and-events/events/media-advisories"
        self.db = Database()
        self.category_id = self.db.add_organization("NATO")
        
    def scrape(self):
        """Scrape NATO Secretary General's schedule"""
        driver = None
        try:
            print(f"Fetching NATO media advisories from {self.advisories_url}...")
            
            chrome_options = Options()
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-software-rasterizer')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36')
            
            service = Service('/usr/local/bin/chromedriver')
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.set_page_load_timeout(120)
            driver.get(self.advisories_url)
            
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Find all advisory links that mention "NATO Secretary General"
            advisory_links = []
            for link in soup.find_all('a', href=True):
                link_text = link.get_text().strip()
                
                if 'NATO Secretary General' in link_text or 'Secretary General' in link_text:
                    href = link['href']
                    full_url = self.base_url + href if href.startswith('/') else href
                    advisory_links.append((full_url, link_text))
            
            print(f"Found {len(advisory_links)} advisories mentioning Secretary General")
            
            if not advisory_links:
                print("No advisories found")
                self._save_generic_schedule(datetime.now())
                return
            
            # Use the first (most recent) advisory
            advisory_url, advisory_title = advisory_links[0]
            print(f"Opening most recent advisory: {advisory_title}")
            
            driver.get(advisory_url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            article_soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Extract purpose from title
            title_elem = article_soup.find('h1')
            if title_elem:
                purpose = title_elem.get_text().strip()
            else:
                purpose = advisory_title
            
            # Clean up purpose
            purpose = re.sub(r'^Media advisory\s*[-:]\s*', '', purpose, flags=re.IGNORECASE)
            purpose = re.sub(r'^Media Advisory\s*[-:]\s*', '', purpose, flags=re.IGNORECASE)
            
            # Extract date from article
            article_date = self._extract_date(article_soup)
            
            # Extract location
            location = self._extract_location(purpose, article_soup.get_text())
            
            # Save to database
            self.db.add_or_update_figure(
                name="Secretary General, Mark Rutte",
                location=location,
                date_time=article_date,
                purpose=purpose,
                category_type="organization",
                category_id=self.category_id,
                source_url=advisory_url,
                display_order=1
            )
            
            print(f"\n{'='*50}")
            print(f"✓ Updated Mark Rutte:")
            print(f"  Location: {location}")
            print(f"  Time: {article_date}")
            print(f"  Purpose: {purpose}")
            print(f"{'='*50}")
            
        except Exception as e:
            print(f"✗ Error scraping NATO schedule: {e}")
            import traceback
            traceback.print_exc()
            self._save_generic_schedule(datetime.now())
        finally:
            if driver:
                driver.quit()
    
    def _extract_date(self, soup):
        """Extract date from article"""
        page_text = soup.get_text()
        
        # Look for date patterns like "26 March 2026" or "March 26, 2026"
        months = ['January', 'February', 'March', 'April', 'May', 'June',
                  'July', 'August', 'September', 'October', 'November', 'December']
        
        # Try "26 March 2026" format
        for month in months:
            pattern = rf'(\d{{1,2}})\s+{month}\s+(\d{{4}})'
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                day = int(match.group(1))
                year = int(match.group(2))
                month_num = months.index(month) + 1
                try:
                    date_obj = datetime(year, month_num, day)
                    return date_obj.strftime("%B %d, %Y")
                except:
                    pass
        
        # Fallback to today's date
        return datetime.now().strftime("%B %d, %Y")
    
    def _extract_location(self, purpose_text, article_text):
        """Extract location from text"""
        combined_text = (purpose_text + " " + article_text).lower()
        
        # Check for specific locations
        if 'brussels' in combined_text or 'belgium' in combined_text:
            return 'Brussels, Belgium'
        elif 'washington' in combined_text:
            return 'Washington, D.C., United States'
        elif 'paris' in combined_text:
            return 'Paris, France'
        elif 'london' in combined_text:
            return 'London, United Kingdom'
        elif 'berlin' in combined_text:
            return 'Berlin, Germany'
        elif 'kyiv' in combined_text or 'kiev' in combined_text:
            return 'Kyiv, Ukraine'
        elif 'warsaw' in combined_text:
            return 'Warsaw, Poland'
        elif 'riga' in combined_text:
            return 'Riga, Latvia'
        elif 'vilnius' in combined_text:
            return 'Vilnius, Lithuania'
        elif 'tallinn' in combined_text:
            return 'Tallinn, Estonia'
        
        # Default to NATO HQ
        return 'Brussels, Belgium'
    
    def _save_generic_schedule(self, now):
        """Save generic schedule when no events found"""
        purpose = "NATO Secretary General's official duties."
        location = "Brussels, Belgium"
        date_time = now.strftime("%B %d, %Y")
        
        self.db.add_or_update_figure(
            name="Secretary General, Mark Rutte",
            location=location,
            date_time=date_time,
            purpose=purpose,
            category_type="organization",
            category_id=self.category_id,
            source_url=self.advisories_url,
            display_order=1
        )
        
        print(f"\n{'='*50}")
        print(f"✓ Updated Mark Rutte (no specific events today):")
        print(f"  Location: {location}")
        print(f"  Time: {date_time}")
        print(f"  Purpose: {purpose}")
        print(f"{'='*50}")

def main():
    scraper = RutteCalendarScraper()
    scraper.scrape()

if __name__ == "__main__":
    main()
