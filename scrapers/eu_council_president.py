#
# eu_council_president.py
# Scraper for EU Council President António Costa
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
import re
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import Database

class CostaCalendarScraper:
    def __init__(self):
        self.url = "https://www.consilium.europa.eu/en/european-council/president/calendar/"
        self.db = Database()
        self.org_id = self.db.add_organization("European Union")
        
    def scrape(self):
        """Scrape EU Council President Costa's schedule"""
        driver = None
        try:
            print(f"Fetching Costa's calendar from {self.url}...")
            
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
            
            # Find the most recent date on the calendar
            most_recent_date = self._find_most_recent_date(soup)
            
            if not most_recent_date:
                print("No dates found on calendar")
                self._save_generic_schedule(datetime.now())
                return
            
            print(f"Most recent date on calendar: {most_recent_date.strftime('%B %d, %Y')}")
            
            # Extract all events from that date
            events = self._extract_events(soup, most_recent_date)
            
            if events:
                # Find the most recent completed event
                completed_events = [e for e in events if e['completed']]
                
                if completed_events:
                    # Use the most recent completed event
                    latest = completed_events[-1]
                    
                    self.db.add_or_update_figure(
                        name="President of the European Council, António Costa",
                        location=latest['location'],
                        date_time=latest['time_display'],
                        purpose=latest['purpose'],
                        category_type="organization",
                        category_id=self.org_id,
                        source_url=self.url,
                        display_order=2
                    )
                    
                    print(f"\n{'='*50}")
                    print(f"✓ Updated António Costa:")
                    print(f"  Location: {latest['location']}")
                    print(f"  Time: {latest['time_display']}")
                    print(f"  Purpose: {latest['purpose']}")
                    print(f"{'='*50}")
                else:
                    print(f"Found {len(events)} event(s) but none completed yet")
                    self._save_generic_schedule(datetime.now())
            else:
                print("No events found for most recent date")
                self._save_generic_schedule(datetime.now())
            
        except Exception as e:
            print(f"✗ Error scraping Costa's schedule: {e}")
            import traceback
            traceback.print_exc()
            self._save_generic_schedule(datetime.now())
        finally:
            if driver:
                driver.quit()
    
    def _find_most_recent_date(self, soup):
        """Find the most recent date on the calendar page"""
        # Look for date patterns (e.g., "26 March 2026", "24 March 2026")
        page_text = soup.get_text()
        
        months = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12
        }
        
        dates_found = []
        for month_name, month_num in months.items():
            pattern = rf'(\d{{1,2}})\s+{month_name}\s+(\d{{4}})'
            matches = re.finditer(pattern, page_text, re.IGNORECASE)
            for match in matches:
                day = int(match.group(1))
                year = int(match.group(2))
                try:
                    date_obj = datetime(year, month_num, day)
                    dates_found.append(date_obj)
                except:
                    continue
        
        if dates_found:
            # Return the most recent date
            return max(dates_found)
        
        return None
    
    def _extract_events(self, soup, target_date):
        """Extract events for a specific date"""
        events = []
        now = datetime.now()
        
        # Look for time patterns like "09:00" or "14:30"
        time_pattern = r'(\d{1,2}):(\d{2})'
        
        # Format target date string to match in text
        date_str = target_date.strftime("%d %B %Y")
        
        # Find all elements and check if they contain the target date
        for element in soup.find_all(['div', 'article', 'section', 'li']):
            text = element.get_text()
            
            # Check if this element is for our target date
            if date_str.lower() in text.lower():
                # Look for times in this element
                time_match = re.search(time_pattern, text)
                if time_match:
                    hour = int(time_match.group(1))
                    minute = int(time_match.group(2))
                    
                    # Extract purpose (look for clean text after time)
                    lines = text.split('\n')
                    purpose = None
                    for line in lines:
                        line = line.strip()
                        if len(line) > 15 and not re.match(r'^\d', line):  # Not a date/time line
                            purpose = line
                            break
                    
                    if purpose:
                        # Create event time
                        event_time = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                        
                        # Check if completed
                        if target_date.date() == now.date():
                            completed = event_time < now
                        else:
                            completed = target_date.date() < now.date()
                        
                        # Extract location
                        location = self._extract_location(text)
                        
                        time_display = f"{target_date.strftime('%B %d, %Y')} - {time_match.group(0)}"
                        
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
        
        if 'paris' in text_lower:
            return 'Paris, France'
        elif 'strasbourg' in text_lower:
            return 'Strasbourg, France'
        elif 'luxembourg' in text_lower:
            return 'Luxembourg City, Luxembourg'
        elif 'brussels' in text_lower or 'bruxelles' in text_lower:
            return 'Brussels, Belgium'
        
        # Default to Brussels
        return 'Brussels, Belgium'
    
    def _save_generic_schedule(self, now):
        """Save generic schedule when no events found"""
        purpose = "EU Council President's official duties."
        location = "Brussels, Belgium"
        date_time = now.strftime("%B %d, %Y")
        
        self.db.add_or_update_figure(
            name="President of the European Council, António Costa",
            location=location,
            date_time=date_time,
            purpose=purpose,
            category_type="organization",
            category_id=self.org_id,
            source_url=self.url,
            display_order=2
        )
        
        print(f"\n{'='*50}")
        print(f"✓ Updated António Costa (no specific events today):")
        print(f"  Location: {location}")
        print(f"  Time: {date_time}")
        print(f"  Purpose: {purpose}")
        print(f"{'='*50}")

def main():
    scraper = CostaCalendarScraper()
    scraper.scrape()

if __name__ == "__main__":
    main()
