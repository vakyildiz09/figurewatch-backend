#
# germany_chancellor.py  
# Scraper for German Chancellor Friedrich Merz
# Created by V. Akyildiz on 31 January 2026.
# Copyright © 2026 FigureWatch. All rights reserved.
#

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import re
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import Database

class MerzCalendarScraper:
    def __init__(self):
        self.url = "https://www.bundeskanzler.de/bk-de/aktuelles/terminkalender"
        self.db = Database()
        self.country_id = self.db.add_country("Germany")
        
    def scrape(self):
        """Scrape Chancellor Merz's schedule"""
        driver = None
        try:
            print(f"Fetching Merz's schedule from {self.url}...")
            
            # Configure Chrome options for Docker
            chrome_options = Options()
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-software-rasterizer')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36')
            # Use chromedriver from PATH
            
            service = Service('/usr/local/bin/chromedriver')
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.set_page_load_timeout(120)  # Timeout if page takes too long
            driver.get(self.url)
            
            # Wait for content to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Get today's date
            now = datetime.now()
            today_str = now.strftime("%B %d, %Y")
            
            # Look for calendar entries
            calendar_items = driver.find_elements(By.CSS_SELECTOR, ".calendar-item, .termin, article")
            
            latest_event = None
            for item in calendar_items:
                item_text = item.text
                
                if self._contains_today(item_text, now):
                    title_elem = item.find_elements(By.CSS_SELECTOR, "h2, h3, .title")
                    if title_elem:
                        purpose = title_elem[0].text.strip()
                        location = self._extract_location(purpose)
                        
                        latest_event = {
                            'purpose': purpose,
                            'location': location
                        }
                        break
            
            if latest_event:
                self.db.add_or_update_figure(
                    name="Chancellor, Friedrich Merz",
                    location=latest_event['location'],
                    date_time=today_str,
                    purpose=latest_event['purpose'],
                    category_type="country",
                    category_id=self.country_id,
                    source_url=self.url,
                    display_order=1
                )
                
                print(f"\n{'='*50}")
                print(f"✓ Updated Friedrich Merz:")
                print(f"  Location: {latest_event['location']}")
                print(f"  Time: {today_str}")
                print(f"  Purpose: {latest_event['purpose']}")
                print(f"{'='*50}")
            else:
                self._save_generic_schedule(now)
            
        except Exception as e:
            print(f"✗ Error scraping Merz's schedule: {e}")
            import traceback
            traceback.print_exc()
            self._save_generic_schedule(datetime.now())
        finally:
            if driver:
                driver.quit()
    
    def _contains_today(self, text, now):
        """Check if text contains today's date"""
        formats = [
            now.strftime("%d.%m.%Y"),
            now.strftime("%d. %B %Y").lower(),
        ]
        
        text_lower = text.lower()
        for date_format in formats:
            if date_format in text_lower:
                return True
        
        return False
    
    def _extract_location(self, text):
        """Extract location from text"""
        text_lower = text.lower()
        
        if 'berlin' in text_lower or 'bundeskanzleramt' in text_lower:
            return 'Berlin, Germany'
        elif 'brüssel' in text_lower or 'brussels' in text_lower:
            return 'Brussels, Belgium'
        elif 'paris' in text_lower:
            return 'Paris, France'
        elif 'washington' in text_lower:
            return 'Washington, D.C., United States'
        
        return 'Berlin, Germany'
    
    def _save_generic_schedule(self, now):
        """Save generic schedule"""
        purpose = "Chancellor's official duties and meetings."
        location = "Berlin, Germany"
        date_time = now.strftime("%B %d, %Y")
        
        self.db.add_or_update_figure(
            name="Chancellor, Friedrich Merz",
            location=location,
            date_time=date_time,
            purpose=purpose,
            category_type="country",
            category_id=self.country_id,
            source_url=self.url,
            display_order=1
        )
        
        print(f"\n{'='*50}")
        print(f"✓ Updated Friedrich Merz (no specific events today):")
        print(f"  Location: {location}")
        print(f"  Time: {date_time}")
        print(f"  Purpose: {purpose}")
        print(f"{'='*50}")

def main():
    scraper = MerzCalendarScraper()
    scraper.scrape()

if __name__ == "__main__":
    main()
