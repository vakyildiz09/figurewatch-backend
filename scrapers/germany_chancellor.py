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
from bs4 import BeautifulSoup
from datetime import datetime
from deep_translator import GoogleTranslator
import re
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import Database

class MerzCalendarScraper:
    def __init__(self):
        self.url = "https://www.bundeskanzler.de/bk-de/friedrich-merz/terminkalender-merz"
        self.db = Database()
        self.country_id = self.db.add_country("Germany")
        
    def scrape(self):
        """Scrape Chancellor Merz's schedule"""
        driver = None
        try:
            print(f"Fetching Merz's calendar from {self.url}...")
            
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
                        name="Chancellor, Friedrich Merz",
                        location=latest['location'],
                        date_time=latest['time_display'],
                        purpose=latest['purpose'],
                        category_type="country",
                        category_id=self.country_id,
                        source_url=self.url,
                        display_order=1
                    )
                    
                    print(f"\n{'='*50}")
                    print(f"✓ Updated Friedrich Merz:")
                    print(f"  Location: {latest['location']}")
                    print(f"  Time: {latest['time_display']}")
                    print(f"  Purpose: {latest['purpose']}")
                    print(f"{'='*50}")
                else:
                    print(f"Found {len(events)} event(s) but none completed yet")
                    self._save_generic_schedule(datetime.now())
            else:
                print("No events found on calendar")
                self._save_generic_schedule(datetime.now())
            
        except Exception as e:
            print(f"✗ Error scraping Merz's schedule: {e}")
            import traceback
            traceback.print_exc()
            self._save_generic_schedule(datetime.now())
        finally:
            if driver:
                driver.quit()
    
    def _extract_events(self, soup, now):
        """Extract events from the calendar page"""
        events = []
        page_text = soup.get_text()
        
        # German day names
        days_de = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']
        
        # German months
        months_de = {
            'Januar': 1, 'Februar': 2, 'März': 3, 'April': 4,
            'Mai': 5, 'Juni': 6, 'Juli': 7, 'August': 8,
            'September': 9, 'Oktober': 10, 'November': 11, 'Dezember': 12
        }
        
        # Time of day mappings
        time_of_day_de = {
            'Vormittag': ('Morning', 9),
            'Mittag': ('Noon', 12),
            'Nachmittag': ('Afternoon', 15),
            'Abend': ('Evening', 18)
        }
        
        # Find date patterns (e.g., "25. März 2026")
        for month_de, month_num in months_de.items():
            pattern = rf'(\d{{1,2}})\.\s*{month_de}\s+(\d{{4}})'
            matches = re.finditer(pattern, page_text)
            
            for match in matches:
                day = int(match.group(1))
                year = int(match.group(2))
                
                try:
                    event_date = datetime(year, month_num, day)
                except:
                    continue
                
                # Extract text around this date to find events
                start_pos = match.start()
                # Get text from this date until the next date or end (limit to 1000 chars)
                text_segment = page_text[start_pos:start_pos + 1000]
                
                # Look for day names followed by event descriptions
                for day_name in days_de:
                    day_pattern = rf'{day_name}[:\s]+([^\n]+)'
                    day_matches = re.finditer(day_pattern, text_segment)
                    
                    for day_match in day_matches:
                        event_text = day_match.group(1).strip()
                        
                        # Check for time of day
                        time_of_day_en = None
                        event_hour = 12  # Default to noon if no time specified
                        
                        for tod_de, (tod_en, hour) in time_of_day_de.items():
                            if tod_de in event_text:
                                time_of_day_en = tod_en
                                event_hour = hour
                                # Remove time of day from event text
                                event_text = event_text.replace(tod_de, '').strip(':, ')
                                break
                        
                        # Remove day name from event text
                        event_text = re.sub(rf'^{day_name}[:\s]*', '', event_text, flags=re.IGNORECASE).strip()
                        
                        if len(event_text) > 10:
                            # Translate to English
                            try:
                                purpose_en = GoogleTranslator(source='de', target='en').translate(event_text)
                            except:
                                purpose_en = event_text
                            
                            # Determine if completed
                            event_time = event_date.replace(hour=event_hour, minute=0, second=0, microsecond=0)
                            
                            if event_date.date() == now.date():
                                completed = event_time < now
                            else:
                                completed = event_date.date() < now.date()
                            
                            # Extract location
                            location = self._extract_location(event_text)
                            
                            # Build time display
                            if time_of_day_en:
                                time_display = f"{event_date.strftime('%B %d, %Y')} - {time_of_day_en}"
                            else:
                                time_display = event_date.strftime('%B %d, %Y')
                            
                            events.append({
                                'time': event_time,
                                'time_display': time_display,
                                'purpose': purpose_en,
                                'location': location,
                                'completed': completed
                            })
        
        return sorted(events, key=lambda x: x['time'])
    
    def _extract_location(self, text):
        """Extract location from event text"""
        text_lower = text.lower()
        
        # Check for specific buildings first
        if 'bundestag' in text_lower:
            return 'Bundestag, Berlin'
        elif 'bundeskanzleramt' in text_lower:
            return 'Federal Chancellery, Berlin'
        elif 'berlin' in text_lower:
            return 'Berlin, Germany'
        elif 'brüssel' in text_lower or 'brussels' in text_lower:
            return 'Brussels, Belgium'
        elif 'paris' in text_lower:
            return 'Paris, France'
        elif 'washington' in text_lower:
            return 'Washington, D.C., United States'
        elif 'london' in text_lower:
            return 'London, United Kingdom'
        elif 'rom' in text_lower:
            return 'Rome, Italy'
        
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
