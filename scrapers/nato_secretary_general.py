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
from datetime import datetime
import re
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import Database

class RutteCalendarScraper:
    def __init__(self):
        self.url = "https://www.nato.int/cps/en/natohq/news.htm"
        self.db = Database()
        self.category_id = self.db.add_organization("NATO")
        
    def scrape(self):
        """Scrape NATO Secretary General's schedule"""
        driver = None
        try:
            print(f"Fetching NATO Secretary General's schedule from {self.url}...")
            
            # Configure Chrome options for Docker
            chrome_options = Options()
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-software-rasterizer')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
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
            
            # Look for media advisories containing today's date
            advisories = driver.find_elements(By.CSS_SELECTOR, "a[href*='media-advisory']")
            
            latest_event = None
            for advisory in advisories:
                text = advisory.text
                if self._contains_today(text, now):
                    # Found today's advisory
                    purpose = text.strip()
                    # Clean up the purpose
                    purpose = re.sub(r'^Media advisory\s*[-:]\s*', '', purpose, flags=re.IGNORECASE)
                    purpose = re.sub(r'\s*-\s*\d+\s+[A-Za-z]+\s+\d{4}', '', purpose)
                    
                    if purpose:
                        latest_event = {
                            'purpose': purpose.strip(),
                            'url': advisory.get_attribute('href')
                        }
                        break
            
            if latest_event:
                # Extract location if mentioned
                location = self._extract_location(latest_event['purpose'])
                
                # Save to database
                self.db.add_or_update_figure(
                    name="Secretary General, Mark Rutte",
                    location=location,
                    date_time=today_str,
                    purpose=latest_event['purpose'],
                    category_type="organization",
                    category_id=self.category_id,
                    source_url=self.url,
                    display_order=1
                )
                
                print(f"\n{'='*50}")
                print(f"✓ Updated Mark Rutte:")
                print(f"  Location: {location}")
                print(f"  Time: {today_str}")
                print(f"  Purpose: {latest_event['purpose']}")
                print(f"{'='*50}")
            else:
                # No events for today, use generic
                self._save_generic_schedule(now)
            
        except Exception as e:
            print(f"✗ Error scraping NATO schedule: {e}")
            import traceback
            traceback.print_exc()
            self._save_generic_schedule(datetime.now())
        finally:
            if driver:
                driver.quit()
    
    def _contains_today(self, text, now):
        """Check if text contains today's date"""
        # Try various date formats
        formats = [
            now.strftime("%d %B %Y"),  # 26 March 2026
            now.strftime("%B %d, %Y"),  # March 26, 2026
            now.strftime("%d/%m/%Y"),   # 26/03/2026
        ]
        
        for date_format in formats:
            if date_format in text:
                return True
        
        return False
    
    def _extract_location(self, text):
        """Extract location from text"""
        text_lower = text.lower()
        
        # Common NATO locations
        if 'brussels' in text_lower or 'belgium' in text_lower:
            return 'Brussels, Belgium'
        elif 'washington' in text_lower:
            return 'Washington, D.C., United States'
        elif 'paris' in text_lower:
            return 'Paris, France'
        elif 'london' in text_lower:
            return 'London, United Kingdom'
        elif 'berlin' in text_lower:
            return 'Berlin, Germany'
        elif 'kyiv' in text_lower or 'kiev' in text_lower:
            return 'Kyiv, Ukraine'
        elif 'warsaw' in text_lower:
            return 'Warsaw, Poland'
        
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
            source_url=self.url,
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
