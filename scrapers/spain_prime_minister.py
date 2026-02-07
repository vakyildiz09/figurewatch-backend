#
# spain_prime_minister.py
# Created by V. Akyildiz on 3 February 2026.
# Copyright © 2026 FigureWatch. All rights reserved.
#

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
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

class SanchezCalendarScraper:
    def __init__(self):
        self.url = "https://www.lamoncloa.gob.es/gobierno/agenda/paginas/agenda.aspx"
        self.db = Database()
        self.country_id = self.db.add_country("Spain")
        self.translator = GoogleTranslator(source='es', target='en')
    
    def translate_spanish_to_english(self, text):
        """Translate Spanish text to English"""
        try:
            if not text or len(text.strip()) < 3:
                return text
            translated = self.translator.translate(text)
            return translated
        except Exception as e:
            print(f"  Translation error: {e}")
            return text
    
    def scrape(self):
        """Scrape PM Sánchez's schedule"""
        driver = None
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
            
            print("Starting Chrome browser...")
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=chrome_options
            )
            
            print("Fetching PM Sánchez's agenda...")
            driver.get(self.url)
            time.sleep(6)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Get today's date from the header
            header = soup.find('h1', class_='title-column')
            if not header:
                print("✗ Could not find agenda header")
                return
            
            header_text = header.get_text(strip=True)  # "Agenda del Gobierno - 3.2.2026"
            date_match = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', header_text)
            
            if not date_match:
                print("✗ Could not parse date from header")
                return
            
            agenda_day = int(date_match.group(1))
            agenda_month = int(date_match.group(2))
            agenda_year = int(date_match.group(3))
            
            print(f"✓ Agenda date: {agenda_day}/{agenda_month}/{agenda_year}")
            
            # Find the event list
            event_list = soup.find('ul', class_='eventList')
            
            if not event_list:
                print("✗ Could not find event list")
                return
            
            # Find all person items (top level li)
            person_items = event_list.find_all('li', recursive=False)
            
            # Find Sánchez's item
            sanchez_item = None
            for item in person_items:
                h2 = item.find('h2')
                if h2 and 'sánchez' in h2.get_text().lower():
                    sanchez_item = item
                    break
            
            if not sanchez_item:
                print("✗ Could not find Sánchez's section")
                return
            
            print("✓ Found Sánchez's agenda section")
            
            # Find the nested event list for Sánchez
            nested_list = sanchez_item.find('ul', class_='eventList')
            
            if not nested_list:
                print("✗ No events found for Sánchez")
                return
            
            # Extract events
            event_items = nested_list.find_all('li', recursive=False)
            print(f"✓ Found {len(event_items)} event(s)")
            
            events = []
            for item in event_items:
                # Time
                time_span = item.find('span', class_='eventDate')
                time_str = time_span.get_text(strip=True) if time_span else None
                
                # Title
                title_p = item.find('p', class_='eventPersonTitle')
                title_text = title_p.get_text(strip=True) if title_p else None
                
                # Location
                loc_p = item.find('p', class_='eventLocation')
                location_text = loc_p.get_text(strip=True) if loc_p else None
                
                if not title_text:
                    continue
                
                # Parse time (Spanish format: "06:30 h." or "10:00 h.")
                event_minutes = None
                if time_str:
                    time_match = re.match(r'(\d{1,2}):(\d{2})', time_str)
                    if time_match:
                        hours = int(time_match.group(1))
                        mins = int(time_match.group(2))
                        event_minutes = hours * 60 + mins
                        time_str = f"{hours:02d}:{mins:02d}"
                
                events.append({
                    'text': title_text,
                    'time_str': time_str,
                    'minutes': event_minutes,
                    'location': location_text
                })
            
            if not events:
                print("✗ No events could be parsed")
                return
            
            # Determine if agenda is for today
            now = datetime.now()
            is_today = (agenda_day == now.day and 
                       agenda_month == now.month and 
                       agenda_year == now.year)
            
            # Filter to current event if today
            if is_today:
                now_minutes = now.hour * 60 + now.minute
                timed_events = [e for e in events if e['minutes'] is not None]
                untimed_events = [e for e in events if e['minutes'] is None]
                
                current_event = None
                
                if timed_events:
                    timed_events.sort(key=lambda e: e['minutes'])
                    
                    for event in timed_events:
                        if event['minutes'] <= now_minutes:
                            current_event = event
                        else:
                            break
                
                if current_event:
                    selected_event = current_event
                    event_time = current_event['time_str']
                    print(f"✓ Current event (now {now.strftime('%H:%M')}): {event_time} - {current_event['text'][:60]}...")
                elif untimed_events:
                    selected_event = untimed_events[0]
                    event_time = None
                    print(f"✓ Showing first untimed event")
                else:
                    # Next upcoming event
                    selected_event = timed_events[0] if timed_events else None
                    event_time = selected_event['time_str'] if selected_event else None
                    if selected_event:
                        print(f"✓ Next event: {event_time} - {selected_event['text'][:60]}...")
                    else:
                        print("✗ No events available")
                        return
            else:
                # Past or future day — show all events combined
                all_texts = []
                for e in events:
                    if e['time_str']:
                        all_texts.append(f"{e['time_str']} - {e['text']}")
                    else:
                        all_texts.append(e['text'])
                
                # For non-today, we'll just take the first event
                selected_event = events[0]
                event_time = selected_event['time_str']
                print(f"✓ Using first event from agenda")
            
            # Translate
            title_en = self.translate_spanish_to_english(selected_event['text'])
            print(f"  Translated: {title_en[:70]}...")
            
            # Determine location
            location = "Madrid, Spain"  # Default
            
            # Check event's location field
            if selected_event['location']:
                loc_text = selected_event['location'].lower()
                # Often contains "hora local" (local time) — ignore that part
                if 'dubái' in loc_text or 'dubai' in loc_text:
                    location = "Dubai, UAE"
                elif 'bruselas' in loc_text or 'brussels' in loc_text:
                    location = "Brussels, Belgium"
                elif 'barcelona' in loc_text:
                    location = "Barcelona, Spain"
                # Check in the title too
            
            title_lower = selected_event['text'].lower()
            if 'dubái' in title_lower or 'emiratos' in title_lower:
                location = "Dubai, UAE"
            elif 'bruselas' in title_lower:
                location = "Brussels, Belgium"
            elif 'barcelona' in title_lower:
                location = "Barcelona, Spain"
            
            # Format date
            spanish_months = [
                'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ]
            month_en = spanish_months[agenda_month - 1]
            date_time = f"{month_en} {agenda_day}, {agenda_year}"
            if event_time:
                date_time = f"{date_time}, {event_time}"
            
            # Format purpose
            purpose = title_en
            if len(purpose) > 200:
                purpose = purpose[:197] + "..."
            
            # Save to database
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
            print(f"✓ Updated Pedro Sánchez:")
            print(f"  Location: {location}")
            print(f"  Time: {date_time}")
            print(f"  Purpose: {purpose}")
            print(f"{'='*50}")
            
        except Exception as e:
            print(f"✗ Error scraping Sánchez's calendar: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            if driver:
                driver.quit()

def main():
    scraper = SanchezCalendarScraper()
    scraper.scrape()

if __name__ == "__main__":
    main()
