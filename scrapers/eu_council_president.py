#
# eu_council_president.py
# Created by V. Akyildiz on 3 February 2026.
# Copyright © 2026 FigureWatch. All rights reserved.
#

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from datetime import datetime
import re
import time
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import Database

class CostaCalendarScraper:
    def __init__(self):
        self.url = "https://www.consilium.europa.eu/en/european-council/president/calendar/"
        self.db = Database()
        self.org_id = self.db.add_organization("European Union")
        
        self.english_months = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12
        }
    
    def scrape(self):
        """Scrape President Costa's schedule"""
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
            
            print("Fetching President Costa's calendar...")
            driver.get(self.url)
            time.sleep(6)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Find the main excerpt list
            excerpt_list = soup.find('ul', class_='gsc-excerpt-list')
            
            if not excerpt_list:
                print("✗ Could not find calendar list")
                return
            
            items = excerpt_list.find_all('li', class_='gsc-excerpt-list__item')
            
            if not items:
                print("✗ No calendar items found")
                return
            
            print(f"✓ Found {len(items)} days on calendar")
            
            now = datetime.now()
            today_day = now.day
            today_month = now.month
            today_year = now.year
            
            # Parse all days into structured data
            # Dates are in descending order (most recent first)
            parsed_days = []
            
            for item in items:
                # Get date from <h2>
                date_h2 = item.find('h2', class_='gsc-excerpt-list__item-date')
                if not date_h2:
                    continue
                
                date_text = date_h2.get_text(strip=True)  # "4 February 2026"
                
                # Parse date
                date_match = re.match(r'(\d{1,2})\s+(\w+)\s+(\d{4})', date_text)
                if not date_match:
                    continue
                
                day = int(date_match.group(1))
                month_name = date_match.group(2).lower()
                year = int(date_match.group(3))
                month = self.english_months.get(month_name)
                
                if not month:
                    continue
                
                # Get the inner excerpt item
                excerpt_item = item.find('li', class_='gsc-excerpt-item')
                if not excerpt_item:
                    continue
                
                # Check for location (pin icon paragraph)
                location = "Brussels, Belgium"  # Default
                location_p = excerpt_item.find('p', class_='gsc-u-flex-container')
                if location_p:
                    # Get text, remove any whitespace artifacts
                    loc_text = location_p.get_text(strip=True)
                    # Remove "(local time)" if present
                    loc_text = re.sub(r'\(local time\)', '', loc_text).strip()
                    if loc_text:
                        location = loc_text
                
                # Extract events from <p> tags containing <span>
                events = []
                for p in excerpt_item.find_all('p'):
                    span = p.find('span')
                    if span:
                        event_text = span.get_text(strip=True)
                        if event_text:
                            # Get time if present
                            time_elem = p.find('time')
                            event_time_str = time_elem.get_text(strip=True) if time_elem else None
                            
                            # Parse time into minutes since midnight for comparison
                            event_minutes = None
                            if event_time_str:
                                time_match = re.match(r'(\d{1,2}):(\d{2})', event_time_str)
                                if time_match:
                                    event_minutes = int(time_match.group(1)) * 60 + int(time_match.group(2))
                            
                            events.append({
                                'text': event_text,
                                'time_str': event_time_str,
                                'minutes': event_minutes
                            })
                
                parsed_days.append({
                    'day': day,
                    'month': month,
                    'month_name': month_name.capitalize(),
                    'year': year,
                    'location': location,
                    'events': events
                })
            
            if not parsed_days:
                print("✗ No days could be parsed")
                return
            
            # Find today or the most recent PAST date
            target_day = None
            
            # First try today
            for day in parsed_days:
                if day['day'] == today_day and day['month'] == today_month and day['year'] == today_year:
                    target_day = day
                    print(f"✓ Found events for today ({today_day} {day['month_name']})")
                    break
            
            # If not today, find most recent past date
            # parsed_days is descending, so first past date we hit is the most recent
            if not target_day:
                for day in parsed_days:
                    day_date = (day['year'], day['month'], day['day'])
                    today_date = (today_year, today_month, today_day)
                    if day_date <= today_date:
                        target_day = day
                        print(f"✓ Using most recent past day: {day['day']} {day['month_name']} {day['year']}")
                        break
            
            if not target_day:
                print("✗ No past or current events found")
                return
            
            if not target_day['events']:
                print("✗ No events for selected day")
                return
            
            print(f"✓ Found {len(target_day['events'])} event(s) for the day")
            
            # Determine current event based on time
            # Only applies when target_day is today
            now_minutes = now.hour * 60 + now.minute
            is_today = (target_day['day'] == today_day and 
                       target_day['month'] == today_month and 
                       target_day['year'] == today_year)
            
            if is_today:
                # Find the current event: the last timed event that has already started,
                # where the next timed event hasn't started yet
                timed_events = [e for e in target_day['events'] if e['minutes'] is not None]
                untimed_events = [e for e in target_day['events'] if e['minutes'] is None]
                
                current_event = None
                
                if timed_events:
                    # Sort by time
                    timed_events.sort(key=lambda e: e['minutes'])
                    
                    # Find the last event whose time has passed
                    for i, event in enumerate(timed_events):
                        if event['minutes'] <= now_minutes:
                            current_event = event
                        else:
                            break  # This event hasn't started yet, stop
                
                if current_event:
                    purpose = current_event['text']
                    event_time = current_event['time_str']
                    print(f"✓ Current event (now {now.strftime('%H:%M')}): {event_time} - {purpose}")
                elif untimed_events:
                    # No timed event has started yet, show untimed events
                    purpose = "; ".join([e['text'] for e in untimed_events])
                    event_time = None
                    print(f"✓ Showing untimed event(s): {purpose}")
                else:
                    # All timed events are in the future
                    # Show the next upcoming event
                    next_event = timed_events[0] if timed_events else None
                    if next_event:
                        purpose = next_event['text']
                        event_time = next_event['time_str']
                        print(f"✓ Next event: {event_time} - {purpose}")
                    else:
                        print("✗ No current or upcoming events")
                        return
            else:
                # Not today — show all events of that past day
                all_texts = []
                for e in target_day['events']:
                    if e['time_str']:
                        all_texts.append(f"{e['time_str']} - {e['text']}")
                    else:
                        all_texts.append(e['text'])
                purpose = "; ".join(all_texts)
                event_time = None
                print(f"✓ Showing all events for past day")
            
            if len(purpose) > 200:
                purpose = purpose[:197] + "..."
            
            # Format date — append time if available
            date_time = f"{target_day['month_name']} {target_day['day']}, {target_day['year']}"
            if event_time:
                date_time = f"{date_time}, {event_time}"
            location = target_day['location']
            
            # Save to database
            self.db.add_or_update_figure(
                name="President of the European Council, António Costa",
                location=location,
                date_time=date_time,
                purpose=purpose,
                category_type="organization",
                category_id=self.org_id,
                source_url=self.url,
                display_order=1
            )
            
            print(f"\n{'='*50}")
            print(f"✓ Updated António Costa:")
            print(f"  Location: {location}")
            print(f"  Time: {date_time}")
            print(f"  Purpose: {purpose}")
            print(f"{'='*50}")
            
        except Exception as e:
            print(f"✗ Error scraping Costa's calendar: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            if driver:
                driver.quit()

def main():
    scraper = CostaCalendarScraper()
    scraper.scrape()

if __name__ == "__main__":
    main()
