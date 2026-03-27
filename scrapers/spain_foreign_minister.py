#
# spain_foreign_minister.py
# Scraper for Spanish Foreign Minister José Manuel Albares
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
from deep_translator import GoogleTranslator
import re
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import Database

class AlbaresCalendarScraper:
    def __init__(self):
        self.url = "https://www.exteriores.gob.es/es/Ministerio/Ministro/Paginas/AgendaMinistro.aspx"
        self.db = Database()
        self.country_id = self.db.add_country("Spain")
        
    def scrape(self):
        """Scrape Foreign Minister Albares's schedule"""
        driver = None
        try:
            print(f"Fetching Albares's agenda from {self.url}...")
            
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
            driver.get(self.url)
            
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Extract date from page
            page_date = self._extract_date(soup)
            
            # Extract all events from the agenda
            events = self._extract_events(soup, page_date)
            
            if events:
                # Find the most recent completed event
                completed_events = [e for e in events if e['completed']]
                
                if completed_events:
                    # Use the most recent completed event
                    latest = completed_events[-1]
                    
                    # Translate purpose to English
                    try:
                        purpose_english = GoogleTranslator(source='es', target='en').translate(latest['purpose'])
                    except:
                        purpose_english = latest['purpose']  # Fallback to Spanish if translation fails
                    
                    self.db.add_or_update_figure(
                        name="Minister of Foreign Affairs, European Union and Cooperation, José Manuel Albares",
                        location=latest['location'],
                        date_time=latest['time_display'],
                        purpose=purpose_english,
                        category_type="country",
                        category_id=self.country_id,
                        source_url=self.url,
                        display_order=2
                    )
                    
                    print(f"\n{'='*50}")
                    print(f"✓ Updated José Manuel Albares:")
                    print(f"  Location: {latest['location']}")
                    print(f"  Time: {latest['time_display']}")
                    print(f"  Purpose: {purpose_english}")
                    print(f"{'='*50}")
                else:
                    print(f"Found {len(events)} event(s) but none completed yet")
                    self._save_generic_schedule(datetime.now())
            else:
                print("No events found on agenda page")
                self._save_generic_schedule(datetime.now())
            
        except Exception as e:
            print(f"✗ Error scraping Albares's schedule: {e}")
            import traceback
            traceback.print_exc()
            self._save_generic_schedule(datetime.now())
        finally:
            if driver:
                driver.quit()
    
    def _extract_date(self, soup):
        """Extract the date shown on the page"""
        # Look for date patterns in Spanish (e.g., "20 de marzo de 2026")
        page_text = soup.get_text()
        
        # Try to find Spanish date pattern
        months_es = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
            'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
            'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }
        
        for month_name, month_num in months_es.items():
            pattern = rf'(\d{{1,2}})\s+de\s+{month_name}\s+de\s+(\d{{4}})'
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                day = int(match.group(1))
                year = int(match.group(2))
                return datetime(year, month_num, day)
        
        # Fallback to today
        return datetime.now()
    
    def _extract_events(self, soup, page_date):
        """Extract events from the agenda page"""
        events = []
        now = datetime.now()
        
        # Look for time patterns like "10:00h" or "12:30h"
        time_pattern = r'(\d{1,2}):(\d{2})\s*h'
        
        # Search in all elements
        for element in soup.find_all(['p', 'li', 'div', 'span']):
            text = element.get_text()
            
            time_match = re.search(time_pattern, text)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2))
                
                # Extract purpose (text after the time)
                purpose = text[time_match.end():].strip()
                purpose = re.sub(r'^[-–—:.\s]+', '', purpose)
                
                if purpose and len(purpose) > 10:
                    # Create event time using page date
                    event_time = page_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    
                    # Check if completed (only if it's today)
                    if page_date.date() == now.date():
                        completed = event_time < now
                    else:
                        # If it's a past date, all events are completed
                        completed = page_date.date() < now.date()
                    
                    # Extract location
                    location = self._extract_location(text)
                    
                    time_display = f"{page_date.strftime('%B %d, %Y')} - {time_match.group(0).upper()}"
                    
                    events.append({
                        'time': event_time,
                        'time_display': time_display,
                        'purpose': purpose,
                        'location': location,
                        'completed': completed
                    })
        
        return sorted(events, key=lambda x: x['time'])
    
    def _extract_location(self, text):
        """Extract location from event text"""
        text_lower = text.lower()
        
        if 'madrid' in text_lower:
            return 'Madrid, Spain'
        elif 'barcelona' in text_lower:
            return 'Barcelona, Spain'
        elif 'bruselas' in text_lower or 'brussels' in text_lower:
            return 'Brussels, Belgium'
        elif 'paris' in text_lower or 'parís' in text_lower:
            return 'Paris, France'
        elif 'washington' in text_lower:
            return 'Washington, D.C., United States'
        
        return 'Madrid, Spain'
    
    def _save_generic_schedule(self, now):
        """Save generic schedule when no events found"""
        purpose = "Foreign Minister's official duties and meetings."
        location = "Madrid, Spain"
        date_time = now.strftime("%B %d, %Y")
        
        self.db.add_or_update_figure(
            name="Minister of Foreign Affairs, European Union and Cooperation, José Manuel Albares",
            location=location,
            date_time=date_time,
            purpose=purpose,
            category_type="country",
            category_id=self.country_id,
            source_url=self.url,
            display_order=2
        )
        
        print(f"\n{'='*50}")
        print(f"✓ Updated José Manuel Albares (no specific events today):")
        print(f"  Location: {location}")
        print(f"  Time: {date_time}")
        print(f"  Purpose: {purpose}")
        print(f"{'='*50}")

def main():
    scraper = AlbaresCalendarScraper()
    scraper.scrape()

if __name__ == "__main__":
    main()
