#
# france_foreign_minister.py
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

class BarrotCalendarScraper:
    def __init__(self):
        self.url = "https://www.diplomatie.gouv.fr/fr/salle-de-presse/agenda-des-ministres/"
        self.db = Database()
        self.country_id = self.db.add_country("France")
        self.translator = GoogleTranslator(source='fr', target='en')
        
    def translate_french_to_english(self, text):
        """Translate French text to English"""
        try:
            if not text or len(text.strip()) < 3:
                return text
            
            translated = self.translator.translate(text)
            return translated
        except Exception as e:
            print(f"  Translation error: {e}")
            return text
    
    def scrape(self):
        """Scrape Foreign Minister Barrot's schedule"""
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
            
            print("Fetching Foreign Minister Barrot's agenda...")
            driver.get(self.url)
            time.sleep(5)
            
            # Close cookie banner
            try:
                close_btn = driver.find_element(By.CSS_SELECTOR, "button.tarteaucitronAllow")
                close_btn.click()
                time.sleep(1)
            except:
                pass
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Find Barrot's section
            h2_tags = soup.find_all('h2')
            barrot_section = None
            
            for h2 in h2_tags:
                if 'barrot' in h2.get_text().lower():
                    barrot_section = h2
                    break
            
            if not barrot_section:
                print("✗ Could not find Barrot's agenda section")
                return
            
            print("✓ Found Barrot's agenda section")
            
            # Get today's date info
            now = datetime.now()
            today_day = now.day
            today_month = now.month
            
            # French month mapping
            french_months = {
                'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4,
                'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8,
                'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12
            }
            
            month_to_english = {
                'janvier': 'January', 'février': 'February', 'mars': 'March',
                'avril': 'April', 'mai': 'May', 'juin': 'June',
                'juillet': 'July', 'août': 'August', 'septembre': 'September',
                'octobre': 'October', 'novembre': 'November', 'décembre': 'December'
            }
            
            # Extract all date headers and their events
            current = barrot_section.find_next_sibling()
            agenda_days = []
            
            while current:
                if current.name == 'h2':
                    break  # Next minister's section
                
                if current.name == 'h3':
                    # This is a date header
                    date_text = current.get_text(strip=True)
                    
                    # Parse: "Lundi 2 février" or "Mardi 3 février"
                    month_pattern = '|'.join(french_months.keys())
                    match = re.search(rf'(\d{{1,2}})\s+({month_pattern})', date_text, re.IGNORECASE)
                    
                    if match:
                        day_num = int(match.group(1))
                        month_name = match.group(2).lower()
                        month_num = french_months[month_name]
                        
                        agenda_days.append({
                            'day': day_num,
                            'month': month_num,
                            'month_name_fr': month_name,
                            'events': []
                        })
                
                elif current.name == 'ul' and agenda_days:
                    # This is an event for the most recent date
                    event_text = current.get_text(strip=True)
                    if event_text:
                        # Parse French time format: "10h30 - Event" or "15h - Event"
                        time_match = re.match(r'(\d{1,2})h(\d{2})?\s*-\s*(.*)', event_text, re.DOTALL)
                        
                        if time_match:
                            hours = int(time_match.group(1))
                            minutes = int(time_match.group(2)) if time_match.group(2) else 0
                            event_desc = time_match.group(3).strip()
                            time_str = f"{hours:02d}:{minutes:02d}"
                            total_minutes = hours * 60 + minutes
                            
                            agenda_days[-1]['events'].append({
                                'text': event_desc,
                                'time_str': time_str,
                                'minutes': total_minutes
                            })
                        else:
                            # No time, untimed event
                            agenda_days[-1]['events'].append({
                                'text': event_text,
                                'time_str': None,
                                'minutes': None
                            })
                
                current = current.find_next_sibling()
            
            if not agenda_days:
                print("✗ No agenda days found")
                return
            
            print(f"✓ Found {len(agenda_days)} days with events")
            
            # Find today or the most recent PAST date (not upcoming)
            target_day = None
            
            # First, try to find today
            for day in agenda_days:
                if day['day'] == today_day and day['month'] == today_month:
                    target_day = day
                    print(f"✓ Found events for today ({today_day} {day['month_name_fr']})")
                    break
            
            # If not today, find the most recent PAST date
            if not target_day:
                # Filter to only past dates (or today)
                past_days = []
                for day in agenda_days:
                    # Create comparable date values
                    if day['month'] < today_month or (day['month'] == today_month and day['day'] <= today_day):
                        past_days.append(day)
                
                if past_days:
                    # Take the last one (most recent past)
                    target_day = past_days[-1]
                    print(f"✓ Using most recent past day: {target_day['day']} {target_day['month_name_fr']}")
                else:
                    print("✗ No past or current events found, all are future")
                    return
            
            if not target_day['events']:
                print("✗ No events for selected day")
                return
            
            print(f"✓ Found {len(target_day['events'])} event(s) for the day")
            
            # Determine current event based on time (only for today)
            now_minutes = now.hour * 60 + now.minute
            is_today = (target_day['day'] == today_day and target_day['month'] == today_month)
            
            if is_today:
                timed_events = [e for e in target_day['events'] if e['minutes'] is not None]
                untimed_events = [e for e in target_day['events'] if e['minutes'] is None]
                
                current_event = None
                
                if timed_events:
                    timed_events.sort(key=lambda e: e['minutes'])
                    
                    for event in timed_events:
                        if event['minutes'] <= now_minutes:
                            current_event = event
                        else:
                            break
                
                if current_event:
                    selected_events = [current_event]
                    event_time = current_event['time_str']
                    print(f"✓ Current event (now {now.strftime('%H:%M')}): {event_time} - {current_event['text'][:60]}...")
                elif untimed_events:
                    selected_events = untimed_events
                    event_time = None
                    print(f"✓ Showing untimed event(s)")
                else:
                    # All timed events are in the future, show next one
                    selected_events = [timed_events[0]] if timed_events else []
                    event_time = selected_events[0]['time_str'] if selected_events else None
                    if selected_events:
                        print(f"✓ Next event: {event_time} - {selected_events[0]['text'][:60]}...")
                    else:
                        print("✗ No current or upcoming events")
                        return
            else:
                # Past day — show all events
                selected_events = target_day['events']
                event_time = None
                print(f"✓ Showing all events for past day")
            
            # Translate selected events (text only, no time prefix)
            translated_events = []
            for event in selected_events:
                event_translated = self.translate_french_to_english(event['text'])
                translated_events.append(event_translated)
                print(f"  - {event_translated[:70]}...")
            
            # Determine location from ALL events of the day (not just selected)
            location = "Paris, France"  # Default
            
            all_texts_fr = [e['text'] for e in target_day['events']]
            all_texts_en = [self.translate_french_to_english(t) for t in all_texts_fr]
            
            for i, event_en in enumerate(all_texts_en):
                event_lower = event_en.lower()
                event_fr_lower = all_texts_fr[i].lower()
                if 'toulouse' in event_lower or 'toulouse' in event_fr_lower:
                    location = "Toulouse, France"
                    break
                elif 'lyon' in event_lower or 'lyon' in event_fr_lower:
                    location = "Lyon, France"
                    break
                elif 'marseille' in event_lower or 'marseille' in event_fr_lower:
                    location = "Marseille, France"
                    break
                elif 'strasbourg' in event_lower or 'strasbourg' in event_fr_lower:
                    location = "Strasbourg, France"
                    break
                elif 'national assembly' in event_lower or 'assemblée nationale' in event_fr_lower:
                    location = "National Assembly, Paris"
                    break
                elif 'senate' in event_lower or 'sénat' in event_fr_lower:
                    location = "Senate, Paris"
                    break
            
            # Format date — append time if available
            month_en = month_to_english[target_day['month_name_fr']]
            date_time = f"{month_en} {target_day['day']}, {now.year}"
            if event_time:
                date_time = f"{date_time}, {event_time}"
            
            # Format purpose
            purpose = "; ".join(translated_events)
            if len(purpose) > 200:
                purpose = purpose[:197] + "..."
            
            # Save to database
            self.db.add_or_update_figure(
                name="Minister for Europe and Foreign Affairs, Jean-Noël Barrot",
                location=location,
                date_time=date_time,
                purpose=purpose,
                category_type="country",
                category_id=self.country_id,
                source_url=self.url,
                display_order=2
            )
            
            print(f"\n{'='*50}")
            print(f"✓ Updated Jean-Noël Barrot:")
            print(f"  Location: {location}")
            print(f"  Time: {date_time}")
            print(f"  Purpose: {purpose}")
            print(f"{'='*50}")
            
        except Exception as e:
            print(f"✗ Error scraping Barrot's calendar: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            if driver:
                driver.quit()

def main():
    scraper = BarrotCalendarScraper()
    scraper.scrape()

if __name__ == "__main__":
    main()
