#
# italy_prime_minister.py
# FIXED VERSION 2 - Fixes month parsing issue
# Created by V. Akyildiz on 26 January 2026.
# Updated: 6 February 2026 - Fixed month parsing
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

class MeloniCalendarScraper:
    def __init__(self):
        self.url = "https://www.governo.it/it/agenda"
        self.db = Database()
        self.country_id = self.db.add_country("Italy")
        self.translator = GoogleTranslator(source='it', target='en')
        
    def translate_italian_to_english(self, text):
        """Translate Italian text to English"""
        try:
            if not text or len(text.strip()) < 3:
                return text
            
            translated = self.translator.translate(text)
            print(f"  Translated: '{text[:40]}...' → '{translated[:40]}...'")
            return translated
        except Exception as e:
            print(f"  Translation error: {e}")
            return text
    
    def scrape(self):
        """Scrape Prime Minister Meloni's schedule"""
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
            
            print("Fetching Meloni's agenda...")
            driver.get(self.url)
            time.sleep(5)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Get today's date
            now = datetime.now()
            today_day = str(now.day).zfill(2)  # "07" not "7"
            today_month = now.strftime('%B').lower()
            today_year = str(now.year)
            
            # Italian month names
            month_map_en_to_it = {
                'january': 'gennaio', 'february': 'febbraio', 'march': 'marzo',
                'april': 'aprile', 'may': 'maggio', 'june': 'giugno',
                'july': 'luglio', 'august': 'agosto', 'september': 'settembre',
                'october': 'ottobre', 'november': 'novembre', 'december': 'dicembre'
            }
            
            month_map_it_to_en = {
                'gennaio': 'January', 'febbraio': 'February', 'marzo': 'March',
                'aprile': 'April', 'maggio': 'May', 'giugno': 'June',
                'luglio': 'July', 'agosto': 'August', 'settembre': 'September',
                'ottobre': 'October', 'novembre': 'November', 'dicembre': 'December'
            }
            
            today_month_it = month_map_en_to_it.get(today_month, 'febbraio')
            
            print(f"Looking for events on: {today_day} {today_month_it} {today_year}")
            
            # Find all event divs
            event_divs = soup.find_all('div', class_='linea_agenda')
            print(f"✓ Found {len(event_divs)} total event containers")
            
            # Collect all events
            today_events = []
            all_events_by_date = {}
            
            for div in event_divs:
                # Extract day
                day_elem = div.find('span', class_='agenda_data_giorno')
                if not day_elem:
                    continue
                
                day_text = day_elem.get_text(strip=True)
                day_match = re.search(r'\d+', day_text)
                if not day_match:
                    continue
                day_num = day_match.group().zfill(2)  # Pad with zero: "7" → "07"
                
                # Extract month
                month_elem = div.find('span', class_='agenda_data_mese_anno')
                if not month_elem:
                    continue
                month_text = month_elem.get_text(strip=True).lower()
                
                # Extract year from month_text if present
                year_match = re.search(r'\d{4}', month_text)
                event_year = year_match.group() if year_match else today_year
                
                # Clean month text - extract just the month name
                # The month text might be "febbraio" or "febbraio 2026"
                month_clean = month_text.split()[0]  # Take first word only
                
                # Extract event details
                time_elem = div.find('span', class_='agenda_ora')
                event_time = time_elem.get_text(strip=True) if time_elem else None
                
                title_elem = div.find('p', class_='agenda_titolo_vedi_tutto')
                title = title_elem.get_text(strip=True) if title_elem else ""
                
                all_p_tags = div.find_all('p')
                description = ""
                if len(all_p_tags) > 1:
                    description = all_p_tags[1].get_text(strip=True)
                
                if not title:
                    continue
                
                event = {
                    'day': day_num,
                    'month': month_clean,
                    'year': event_year,
                    'time': event_time,
                    'title': title,
                    'description': description
                }
                
                # Store by date
                date_key = f"{day_num}_{month_clean}_{event_year}"
                if date_key not in all_events_by_date:
                    all_events_by_date[date_key] = []
                all_events_by_date[date_key].append(event)
                
                # Check if this is TODAY
                # Compare: day_num (e.g., "07") with today_day (e.g., "07")
                # Compare: month_clean (e.g., "febbraio") with today_month_it (e.g., "febbraio")
                if day_num == today_day and month_clean == today_month_it and event_year == today_year:
                    today_events.append(event)
                    print(f"  ✓ Found TODAY's event: {event_time} - {title[:50]}...")
            
            # Decide which events to use
            if today_events:
                print(f"✓ Using {len(today_events)} event(s) from TODAY")
                selected_events = today_events
                selected_date = (today_day, today_month_it, today_year)
            else:
                print("ℹ No events found for TODAY, looking for most recent past date...")
                
                # Find most recent PAST or TODAY date (not future)
                def parse_date(date_key):
                    day, month, year = date_key.split('_')
                    month_num = list(month_map_it_to_en.keys()).index(month) + 1
                    return datetime(int(year), month_num, int(day))
                
                if all_events_by_date:
                    # Filter to past/today dates only
                    today_dt = datetime(now.year, now.month, now.day)
                    past_dates = {k: v for k, v in all_events_by_date.items() 
                                 if parse_date(k) <= today_dt}
                    
                    if past_dates:
                        most_recent_key = max(past_dates.keys(), key=parse_date)
                        selected_events = past_dates[most_recent_key]
                        day, month, year = most_recent_key.split('_')
                        selected_date = (day, month, year)
                        print(f"✓ Using {len(selected_events)} event(s) from {day} {month} {year}")
                    else:
                        # All events are in the future, use the earliest one
                        earliest_key = min(all_events_by_date.keys(), key=parse_date)
                        selected_events = all_events_by_date[earliest_key]
                        day, month, year = earliest_key.split('_')
                        selected_date = (day, month, year)
                        print(f"✓ Using {len(selected_events)} event(s) from future date {day} {month} {year}")
                else:
                    print("✗ No events found at all")
                    return
            
            if not selected_events:
                print("✗ No events to process")
                return
            
            # Combine all titles
            titles = [e['title'] for e in selected_events if e['title']]
            combined_title = "; ".join(titles)
            
            print(f"  Combined {len(titles)} event(s)")
            
            # Translate
            purpose_english = self.translate_italian_to_english(combined_title)
            
            # Extract location from first event's description
            first_description = selected_events[0]['description'] if selected_events[0]['description'] else ""
            location = self._extract_location(first_description, combined_title)
            
            # Format purpose
            purpose = purpose_english
            if not purpose.endswith('.'):
                purpose += '.'
            if len(purpose) > 200:
                purpose = purpose[:197] + '...'
            
            # Format date
            day, month_it, year = selected_date
            month_en = month_map_it_to_en.get(month_it, month_it.capitalize())
            
            # Add time if available
            first_time = selected_events[0]['time']
            if first_time:
                date_time = f"{month_en} {int(day)}, {year}, {first_time}"
            else:
                date_time = f"{month_en} {int(day)}, {year}"
            
            # Save to database
            self.db.add_or_update_figure(
                name="Prime Minister, Giorgia Meloni",
                location=location,
                date_time=date_time,
                purpose=purpose,
                category_type="country",
                category_id=self.country_id,
                source_url=self.url
            )
            
            print(f"\n{'='*50}")
            print(f"✓ Updated Giorgia Meloni:")
            print(f"  Location: {location}")
            print(f"  Time: {date_time}")
            print(f"  Purpose: {purpose}")
            print(f"{'='*50}")
            
        except Exception as e:
            print(f"✗ Error scraping Meloni's calendar: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            if driver:
                driver.quit()
    
    def _extract_location(self, description, title):
        """Extract location from description or title"""
        text = (description + " " + title).lower()
        
        # Common Italian locations - check for Palazzo Chigi first
        if 'palazzo chigi' in text:
            return 'Palazzo Chigi, Rome'
        
        locations = {
            'roma': 'Rome, Italy',
            'milano': 'Milan, Italy',
            'cortina': 'Cortina d\'Ampezzo, Italy',
            'napoli': 'Naples, Italy',
            'firenze': 'Florence, Italy',
            'venezia': 'Venice, Italy',
            'torino': 'Turin, Italy',
            'bologna': 'Bologna, Italy',
            'bruxelles': 'Brussels, Belgium',
            'parigi': 'Paris, France',
            'berlino': 'Berlin, Germany',
            'londra': 'London, United Kingdom',
            'madrid': 'Madrid, Spain',
            'washington': 'Washington, D.C., United States',
            'new york': 'New York City, United States',
            'oman': 'Muscat, Oman',
            'giappone': 'Tokyo, Japan',
            'corea': 'Seoul, South Korea',
            'cina': 'Beijing, China',
            'india': 'New Delhi, India',
            'arabia saudita': 'Riyadh, Saudi Arabia',
            'emirati arabi': 'Abu Dhabi, UAE',
            'dubai': 'Dubai, UAE'
        }
        
        for keyword, location in locations.items():
            if keyword in text:
                return location
        
        return "Rome, Italy"

def main():
    scraper = MeloniCalendarScraper()
    scraper.scrape()

if __name__ == "__main__":
    main()

# ==============================================================
# FIXES IN THIS VERSION:
# ==============================================================
#
# 1. ZERO-PADDING: Day numbers now padded ("7" → "07")
#    - today_day = str(now.day).zfill(2)
#    - day_num = day_match.group().zfill(2)
#    - This ensures "07 febbraio" matches "07"
#
# 2. MONTH EXTRACTION: Uses .split()[0] to get just month name
#    - "febbraio" → "febbraio" ✓
#    - "febbraio 2026" → "febbraio" ✓
#
# 3. PAST DATE PREFERENCE: Looks for past/today dates first
#    - Won't skip to future dates if today has events
#
# 4. ADDED LOCATION: "cortina" for Milano Cortina events
#
# This should now correctly detect Feb 7 events!
# ==============================================================
