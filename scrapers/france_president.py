#
# france_president.py
# Scraper for French President Emmanuel Macron
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

class MacronCalendarScraper:
    def __init__(self):
        self.url = "https://www.elysee.fr/agenda"
        self.db = Database()
        self.country_id = self.db.add_country("France")
        
    def scrape(self):
        """Scrape President Macron's schedule"""
        driver = None
        try:
            print(f"Fetching Macron's agenda from {self.url}...")
            
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
            
            # Extract all events from the page
            events = self._extract_events(soup, datetime.now())
            
            if events:
                # Find the most recent completed event
                completed_events = [e for e in events if e['completed']]
                
                if completed_events:
                    # Use the most recent completed event
                    latest = completed_events[-1]
                    
                    self.db.add_or_update_figure(
                        name="President, Emmanuel Macron",
                        location=latest['location'],
                        date_time=latest['time_display'],
                        purpose=latest['purpose'],
                        category_type="country",
                        category_id=self.country_id,
                        source_url=self.url,
                        display_order=1
                    )
                    
                    print(f"\n{'='*50}")
                    print(f"✓ Updated Emmanuel Macron:")
                    print(f"  Location: {latest['location']}")
                    print(f"  Time: {latest['time_display']}")
                    print(f"  Purpose: {latest['purpose']}")
                    print(f"{'='*50}")
                else:
                    print(f"Found {len(events)} event(s) but none completed yet")
                    self._save_generic_schedule(datetime.now())
            else:
                print("No events found on agenda")
                self._save_generic_schedule(datetime.now())
            
        except Exception as e:
            print(f"✗ Error scraping Macron's schedule: {e}")
            import traceback
            traceback.print_exc()
            self._save_generic_schedule(datetime.now())
        finally:
            if driver:
                driver.quit()
    
    def _extract_events(self, soup, now):
        """Extract events from the agenda page"""
        events = []
        page_text = soup.get_text()
        
        # French months
        months_fr = {
            'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4,
            'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8,
            'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12
        }
        
        # Find date patterns (e.g., "27 mars 2026")
        for month_fr, month_num in months_fr.items():
            pattern = rf'(\d{{1,2}})\s+{month_fr}\s+(\d{{4}})'
            matches = re.finditer(pattern, page_text, re.IGNORECASE)
            
            for match in matches:
                day = int(match.group(1))
                year = int(match.group(2))
                
                try:
                    event_date = datetime(year, month_num, day)
                except:
                    continue
                
                # Extract text around this date to find events
                start_pos = match.start()
                # Get text from this date until the next date (limit to 1000 chars)
                text_segment = page_text[start_pos:start_pos + 1000]
                
                # Look for time patterns like "16h00" or "16:00"
                time_pattern = r'(\d{1,2})h(\d{2})|(\d{1,2}):(\d{2})'
                time_matches = re.finditer(time_pattern, text_segment)
                
                for time_match in time_matches:
                    if time_match.group(1):  # "16h00" format
                        hour = int(time_match.group(1))
                        minute = int(time_match.group(2))
                    else:  # "16:00" format
                        hour = int(time_match.group(3))
                        minute = int(time_match.group(4))
                    
                    # Extract event text after the time
                    event_start = time_match.end()
                    event_text = text_segment[event_start:event_start + 200].split('\n')[0].strip()
                    
                    if len(event_text) > 10:
                        # Translate to English
                        try:
                            purpose_en = GoogleTranslator(source='fr', target='en').translate(event_text)
                        except:
                            purpose_en = event_text
                        
                        # Extract location
                        location = self._extract_location(event_text, purpose_en)
                        
                        # Determine if completed
                        event_time = event_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                        
                        if event_date.date() == now.date():
                            completed = event_time < now
                        else:
                            completed = event_date.date() < now.date()
                        
                        time_display = f"{event_date.strftime('%B %d, %Y')} - {hour:02d}:{minute:02d}"
                        
                        events.append({
                            'time': event_time,
                            'time_display': time_display,
                            'purpose': purpose_en,
                            'location': location,
                            'completed': completed
                        })
        
        return sorted(events, key=lambda x: x['time'])
    
    def _extract_location(self, text_fr, text_en):
        """Extract location from event text"""
        text_fr_lower = text_fr.lower()
        text_en_lower = text_en.lower()
        
        # Special cases
        if 'conseil européen' in text_fr_lower or 'european council' in text_en_lower:
            return 'Brussels, Belgium'
        elif 'entretien téléphonique' in text_fr_lower or 'telephone' in text_en_lower:
            return 'Paris, France'
        elif 'conseil des ministres' in text_fr_lower or 'council of ministers' in text_en_lower:
            return 'Paris, France'
        
        # Look for "Déplacement à [location]" pattern
        deplacement_match = re.search(r'déplacement à ([^,\n\.]+)', text_fr_lower)
        if deplacement_match:
            city = deplacement_match.group(1).strip()
            # Capitalize first letter of each word
            city = city.title()
            return f"{city}, France"
        
        # Check for other cities/countries
        if 'bruxelles' in text_fr_lower or 'brussels' in text_en_lower:
            return 'Brussels, Belgium'
        elif 'berlin' in text_fr_lower:
            return 'Berlin, Germany'
        elif 'washington' in text_fr_lower:
            return 'Washington, D.C., United States'
        elif 'rome' in text_fr_lower:
            return 'Rome, Italy'
        elif 'londres' in text_fr_lower or 'london' in text_en_lower:
            return 'London, United Kingdom'
        
        # Default to Paris
        return 'Paris, France'
    
    def _save_generic_schedule(self, now):
        """Save generic schedule"""
        purpose = "President's official duties and meetings."
        location = "Paris, France"
        date_time = now.strftime("%B %d, %Y")
        
        self.db.add_or_update_figure(
            name="President, Emmanuel Macron",
            location=location,
            date_time=date_time,
            purpose=purpose,
            category_type="country",
            category_id=self.country_id,
            source_url=self.url,
            display_order=1
        )
        
        print(f"\n{'='*50}")
        print(f"✓ Updated Emmanuel Macron (no specific events today):")
        print(f"  Location: {location}")
        print(f"  Time: {date_time}")
        print(f"  Purpose: {purpose}")
        print(f"{'='*50}")

def main():
    scraper = MacronCalendarScraper()
    scraper.scrape()

if __name__ == "__main__":
    main()
