#
# spain_prime_minister.py
# Scraper for Spanish Prime Minister Pedro Sánchez
# Created by V. Akyildiz on 31 January 2026.
# Copyright © 2026 FigureWatch. All rights reserved.
#

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import re
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import Database

class SanchezCalendarScraper:
    def __init__(self):
        self.url = "https://www.lamoncloa.gob.es/presidente/agenda/Paginas/index.aspx"
        self.db = Database()
        self.country_id = self.db.add_country("Spain")
        
    def scrape(self):
        """Scrape Prime Minister Sánchez's schedule"""
        driver = None
        try:
            print(f"Fetching Sánchez's schedule from {self.url}...")
            
            chrome_options = Options()
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-software-rasterizer')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36')
            chrome_options.binary_location = '/usr/bin/google-chrome'
            
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(self.url)
            
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            now = datetime.now()
            today_str = now.strftime("%B %d, %Y")
            
            agenda_items = driver.find_elements(By.CSS_SELECTOR, ".agenda-item, .event, article")
            
            latest_event = None
            for item in agenda_items:
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
                    name="Prime Minister, Pedro Sánchez",
                    location=latest_event['location'],
                    date_time=today_str,
                    purpose=latest_event['purpose'],
                    category_type="country",
                    category_id=self.country_id,
                    source_url=self.url,
                    display_order=1
                )
                
                print(f"\n{'='*50}")
                print(f"✓ Updated Pedro Sánchez:")
                print(f"  Location: {latest_event['location']}")
                print(f"  Time: {today_str}")
                print(f"  Purpose: {latest_event['purpose']}")
                print(f"{'='*50}")
            else:
                self._save_generic_schedule(now)
            
        except Exception as e:
            print(f"✗ Error scraping Sánchez's schedule: {e}")
            import traceback
            traceback.print_exc()
            self._save_generic_schedule(datetime.now())
        finally:
            if driver:
                driver.quit()
    
    def _contains_today(self, text, now):
        formats = [
            now.strftime("%d/%m/%Y"),
            now.strftime("%d de %B de %Y").lower(),
        ]
        
        text_lower = text.lower()
        for date_format in formats:
            if date_format in text_lower:
                return True
        return False
    
    def _extract_location(self, text):
        text_lower = text.lower()
        
        if 'madrid' in text_lower or 'moncloa' in text_lower:
            return 'Madrid, Spain'
        elif 'barcelona' in text_lower:
            return 'Barcelona, Spain'
        elif 'bruselas' in text_lower or 'brussels' in text_lower:
            return 'Brussels, Belgium'
        
        return 'Madrid, Spain'
    
    def _save_generic_schedule(self, now):
        purpose = "Prime Minister's official duties and meetings."
        location = "Madrid, Spain"
        date_time = now.strftime("%B %d, %Y")
        
        self.db.add_or_update_figure(
            name="Prime Minister, Pedro Sánchez",
            location=location,
            date_time=date_time,
            purpose=purpose,
            category_type="country",
            category_id=self.country_id,
            source_url=self.url,
            display_order=1
        )
        
        print(f"\n{'='*50}")
        print(f"✓ Updated Pedro Sánchez (no specific events today):")
        print(f"  Location: {location}")
        print(f"  Time: {date_time}")
        print(f"  Purpose: {purpose}")
        print(f"{'='*50}")

def main():
    scraper = SanchezCalendarScraper()
    scraper.scrape()

if __name__ == "__main__":
    main()
