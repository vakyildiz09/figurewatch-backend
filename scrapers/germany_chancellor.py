#
# germany_chancellor.py
# Created by V. Akyildiz on 21 January 2026.
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

class MerzCalendarScraper:
    def __init__(self):
        self.url = "https://www.bundeskanzler.de/bk-de/friedrich-merz/terminkalender-merz"
        self.db = Database()
        self.country_id = self.db.add_country("Germany")
        self.translator = GoogleTranslator(source='de', target='en')
        
    def translate_german_to_english(self, text):
        """Translate German text to English"""
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
        """Scrape Chancellor Merz's schedule"""
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
            
            print("Fetching Merz's calendar...")
            driver.get(self.url)
            time.sleep(5)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Find all event containers
            event_divs = soup.find_all('div', class_='bpa-eventcalendar-event')
            
            if not event_divs:
                print("✗ No events found")
                return
            
            print(f"✓ Found {len(event_divs)} total events")
            
            # Parse all events and group by date
            events_by_date = {}
            
            for event_div in event_divs:
                # Find date
                date_div = event_div.find('div', class_='bpa-eventcalendar-event-date')
                if not date_div:
                    continue
                
                date_text = date_div.get_text(strip=True)
                # Extract date: "21. Januar 202621Jan" -> "21. Januar 2026"
                date_match = re.search(r'(\d{1,2})\.\s*(Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\s*(\d{4})', date_text)
                
                if not date_match:
                    continue
                
                day, month, year = date_match.groups()
                date_key = f"{day}. {month} {year}"
                
                # Find title and description using proper selectors
                title = ""
                description = ""
                
                # Title is in h4 with class 'bpa-eventcalendar-event-title'
                title_elem = event_div.find('h4', class_='bpa-eventcalendar-event-title')
                if title_elem:
                    title = title_elem.get_text(strip=True)
                
                # Description is in div with class 'bpa-richtext'
                desc_elem = event_div.find('div', class_='bpa-richtext')
                if desc_elem:
                    description = desc_elem.get_text(strip=True)
                
                if title:
                    if date_key not in events_by_date:
                        events_by_date[date_key] = []
                    events_by_date[date_key].append({
                        'title': title,
                        'description': description
                    })
            
            if not events_by_date:
                print("✗ No valid events found")
                return
            
            # Get TODAY's date
            now = datetime.now()
            today_day = now.day
            today_month_num = now.month
            
            # Map month number to German name
            month_num_to_de = {
                1: 'Januar', 2: 'Februar', 3: 'März', 4: 'April',
                5: 'Mai', 6: 'Juni', 7: 'Juli', 8: 'August',
                9: 'September', 10: 'Oktober', 11: 'November', 12: 'Dezember'
            }
            
            today_month_de = month_num_to_de[today_month_num]
            today_year = now.year
            today_date_key = f"{today_day}. {today_month_de} {today_year}"
            
            print(f"Looking for today's date: {today_date_key}")
            
            # Check if today's date exists
            if today_date_key not in events_by_date:
                print(f"✗ No events found for today ({today_date_key})")
                print(f"Available dates: {list(events_by_date.keys())}")
                return
            
            latest_date = today_date_key
            latest_events = events_by_date[latest_date]
            
            print(f"✓ Using most recent date: {latest_date}")
            print(f"  Found {len(latest_events)} event(s) on this date")
            
            # Combine all titles for this date (titles only, not descriptions)
            titles = [event['title'] for event in latest_events if event['title']]
            combined_title = "; ".join(titles)
            
            print(f"  Combined titles: {combined_title}")
            
            # Translate combined title (titles only)
            purpose_english = self.translate_german_to_english(combined_title)
            
            # Extract location from first event's description
            first_description = latest_events[0]['description'] if latest_events[0]['description'] else ""
            location = self._extract_location(first_description, combined_title)
            
            # Format purpose
            purpose = purpose_english
            if not purpose.endswith('.'):
                purpose += '.'
            if len(purpose) > 200:
                purpose = purpose[:197] + '...'
            
            # Format date (convert German month to English)
            month_en_map = {
                'Januar': 'January', 'Februar': 'February', 'März': 'March',
                'April': 'April', 'Mai': 'May', 'Juni': 'June',
                'Juli': 'July', 'August': 'August', 'September': 'September',
                'Oktober': 'October', 'November': 'November', 'Dezember': 'December'
            }
            
            date_match = re.match(r'(\d{1,2})\.\s*(\w+)\s*(\d{4})', latest_date)
            if date_match:
                day, month_de, year = date_match.groups()
                month_en = month_en_map.get(month_de, month_de)
                date_time = f"{month_en} {day}, {year}"
            else:
                date_time = latest_date
            
            # Save to database
            self.db.add_or_update_figure(
                name="Chancellor, Friedrich Merz",
                location=location,
                date_time=date_time,
                purpose=purpose,
                category_type="country",
                category_id=self.country_id,
                source_url=self.url
            )
            
            print(f"\n{'='*50}")
            print(f"✓ Updated Friedrich Merz:")
            print(f"  Location: {location}")
            print(f"  Time: {date_time}")
            print(f"  Purpose: {purpose}")
            print(f"{'='*50}")
            
        except Exception as e:
            print(f"✗ Error scraping Merz's calendar: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            if driver:
                driver.quit()
    
    def _extract_location(self, description, title):
        """Extract location from description or title"""
        text = (description + " " + title).lower()
        
        # Check for specific cities/locations
        locations = {
            'davos': 'Davos, Switzerland',
            'berlin': 'Berlin, Germany',
            'brüssel': 'Brussels, Belgium',
            'brussels': 'Brussels, Belgium',
            'paris': 'Paris, France',
            'washington': 'Washington, D.C., United States',
            'münchen': 'Munich, Germany',
            'munich': 'Munich, Germany',
            'hamburg': 'Hamburg, Germany',
            'köln': 'Cologne, Germany',
            'frankfurt': 'Frankfurt, Germany',
            'bonn': 'Bonn, Germany'
        }
        
        for keyword, location in locations.items():
            if keyword in text:
                return location
        
        return "Berlin, Germany"

def main():
    scraper = MerzCalendarScraper()
    scraper.scrape()

if __name__ == "__main__":
    main()
