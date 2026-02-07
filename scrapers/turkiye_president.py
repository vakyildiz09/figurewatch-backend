#
# turkiye_president.py
# Created by V. Akyildiz on 31 January 2026.
# Copyright © 2026 FigureWatch. All rights reserved.
#

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
from datetime import datetime
import re
import time
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import Database

class ErdoganCalendarScraper:
    def __init__(self):
        self.url = "https://www.tccb.gov.tr/program/"
        self.db = Database()
        self.country_id = self.db.add_country("Türkiye")
        self.translator = GoogleTranslator(source='tr', target='en')
        
    def translate_turkish_to_english(self, text):
        """Translate Turkish text to English"""
        try:
            if not text or len(text.strip()) < 3:
                return text
            
            translated = self.translator.translate(text)
            return translated
        except Exception as e:
            print(f"  Translation error: {e}")
            return text
    
    def scrape(self):
        """Scrape President Erdoğan's schedule"""
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
            
            print("Fetching Erdoğan's agenda...")
            driver.get(self.url)
            time.sleep(5)
            
            # The page automatically loads today's date
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Get today's date
            now = datetime.now()
            today_str = now.strftime("%B %d, %Y")
            
            print(f"Checking program for: {today_str}")
            
            # Find the program container
            program_div = soup.find('div', id='list-daily-program')
            
            if not program_div:
                print("✗ Could not find program container")
                return
            
            program_text = program_div.get_text(strip=True)
            
            # Check if empty (no program)
            if len(program_text) < 10:
                print("✓ No program for today")
                
                # Save with "No program"
                self.db.add_or_update_figure(
                    name="President, Recep Tayyip Erdoğan",
                    location="Ankara, Türkiye",
                    date_time=today_str,
                    purpose="No program",
                    category_type="country",
                    category_id=self.country_id,
                    source_url=self.url,
                    display_order=1
                )
                
                print(f"\n{'='*50}")
                print(f"✓ Updated Recep Tayyip Erdoğan:")
                print(f"  Location: Ankara, Türkiye")
                print(f"  Time: {today_str}")
                print(f"  Purpose: No program")
                print(f"{'='*50}")
                return
            
            # Extract all events
            print(f"✓ Found program content ({len(program_text)} chars)")
            
            # Find all <dl> elements (each is an event)
            events = program_div.find_all('dl')
            
            if not events:
                print("✗ No events found in program div")
                return
            
            print(f"✓ Found {len(events)} event(s)")
            
            event_list = []
            locations_found = []
            
            for event in events:
                # Extract time
                time_elem = event.find('dt', class_='time')
                event_time = time_elem.get_text(strip=True) if time_elem else None
                
                # Extract title and location
                dd_elem = event.find('dd')
                if dd_elem:
                    full_text = dd_elem.get_text(strip=True)
                    
                    # Location is usually in parentheses at the end
                    location_match = re.search(r'\(([^)]+)\)\s*$', full_text)
                    if location_match:
                        location_tr = location_match.group(1)
                        title_tr = full_text[:location_match.start()].strip()
                        locations_found.append(location_tr)
                    else:
                        title_tr = full_text
                        location_tr = None
                    
                    # Translate title
                    title_en = self.translate_turkish_to_english(title_tr)
                    
                    event_list.append({
                        'time': event_time,
                        'title': title_en,
                        'location': location_tr
                    })
                    
                    print(f"  {event_time}: {title_en[:60]}...")
            
            # Combine all event titles
            titles = [e['title'] for e in event_list if e['title']]
            combined_titles = "; ".join(titles)
            
            # Determine location
            if locations_found:
                # Use first location, translate it
                primary_location_tr = locations_found[0]
                primary_location_en = self.translate_turkish_to_english(primary_location_tr)
                
                # Clean up common location names
                if 'cumhurbaşkanlığı külliyesi' in primary_location_tr.lower():
                    location = "Presidential Complex, Ankara"
                elif 'ankara' in primary_location_en.lower():
                    location = "Ankara, Türkiye"
                elif 'istanbul' in primary_location_en.lower():
                    location = "Istanbul, Türkiye"
                else:
                    location = f"{primary_location_en}, Türkiye"
            else:
                location = "Ankara, Türkiye"
            
            # Format purpose
            purpose = combined_titles
            if len(purpose) > 200:
                purpose = purpose[:197] + "..."
            
            # Save to database
            self.db.add_or_update_figure(
                name="President, Recep Tayyip Erdoğan",
                location=location,
                date_time=today_str,
                purpose=purpose,
                category_type="country",
                category_id=self.country_id,
                source_url=self.url,
                display_order=1
            )
            
            print(f"\n{'='*50}")
            print(f"✓ Updated Recep Tayyip Erdoğan:")
            print(f"  Location: {location}")
            print(f"  Time: {today_str}")
            print(f"  Purpose: {purpose}")
            print(f"{'='*50}")
            
        except Exception as e:
            print(f"✗ Error scraping Erdoğan's calendar: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            if driver:
                driver.quit()

def main():
    scraper = ErdoganCalendarScraper()
    scraper.scrape()

if __name__ == "__main__":
    main()
