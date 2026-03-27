#
#  us_secretary_of_state.py
#  FigureWatch Backend
#
#  Created by V. Akyildiz on 9 January 2025.
#  Copyright © 2026 FigureWatch. All rights reserved.
#
#  This software is proprietary and confidential.
#  Unauthorized copying, distribution, or use is strictly prohibited.
#

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import Database

class RubioCalendarScraper:
    def __init__(self):
        self.db = Database()
        self.country_id = self.db.add_country("United States")
    
    def parse_time(self, time_str):
        """Parse time string to datetime.time object for comparison"""
        try:
            time_str = time_str.strip().upper()
            time_str = re.sub(r'(\d+:\d+)\s*([AP])\.?M\.?', r'\1 \2M', time_str)
            return datetime.strptime(time_str, "%I:%M %p").time()
        except Exception as e:
            print(f"Error parsing time '{time_str}': {e}")
            return None
    
    def scrape(self):
        """Scrape Rubio's schedule and get the CURRENT/ONGOING event for TODAY"""
        try:
            now = datetime.now()
            current_time = now.time()
            
            # Construct today's schedule URL directly
            # Format: https://www.state.gov/releases/office-of-the-spokesperson/2026/03/public-schedule-march-27-2026/
            date_path = now.strftime("%Y/%m/public-schedule-%B-%d-%Y").lower()
            schedule_url = f"https://www.state.gov/releases/office-of-the-spokesperson/{date_path}/"
            
            print(f"Fetching Rubio's schedule from {schedule_url}...")
            print(f"Looking for events on {now.strftime('%B %d, %Y')}")
            print(f"Current time for comparison: {current_time.strftime('%I:%M %p')} EST")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            # Get the schedule page directly
            response = requests.get(schedule_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            print(f"✓ Found today's schedule")
            
            # Find Rubio's header
            rubio_header = None
            for strong_tag in soup.find_all(['strong', 'b']):
                text = strong_tag.get_text()
                if 'SECRETARY' in text.upper() and 'RUBIO' in text.upper():
                    rubio_header = strong_tag
                    print(f"✓ Found Rubio's schedule section")
                    break
            
            if not rubio_header:
                print("Could not find Secretary Rubio's section")
                self._save_generic_schedule(now)
                return
            
            # Collect events from following elements
            events = []
            current_element = rubio_header.parent
            
            while True:
                current_element = current_element.find_next(['p', 'div'])
                if not current_element:
                    break
                
                # Stop if we hit another person's header
                if current_element.find(['strong', 'b']):
                    strong_text = current_element.find(['strong', 'b']).get_text()
                    if re.search(r'DEPUTY|UNDER SECRETARY|BRIEFING SCHEDULE', strong_text, re.IGNORECASE):
                        break
                
                text = current_element.get_text(strip=True)
                if not text or len(text) < 10:
                    continue
                
                # Look for time pattern
                time_match = re.match(r'^(\d{1,2}:\d{2}\s*[ap]\.?m\.?)\s*(.*)', text, re.IGNORECASE)
                
                if time_match:
                    time_str = time_match.group(1)
                    description = time_match.group(2).strip()
                    event_time = self.parse_time(time_str)
                    
                    if event_time and description:
                        time_str = time_str.replace('.', '').upper()
                        if not time_str.endswith('M'):
                            time_str += 'M'
                        
                        events.append({
                            'time': event_time,
                            'time_str': time_str,
                            'description': description
                        })
                        print(f"  Found event: {time_str} - {description[:80]}...")
                elif 'Secretary Rubio' in text or 'Secretary' in text:
                    events.append({
                        'time': None,
                        'time_str': None,
                        'description': text
                    })
                    print(f"  Found untimed event: {text[:80]}...")
            
            if not events:
                print("No events found for Secretary Rubio")
                self._save_generic_schedule(now)
                return
            
            # Separate timed and untimed events
            timed_events = [e for e in events if e['time'] is not None]
            untimed_events = [e for e in events if e['time'] is None]
            
            # Sort timed events
            timed_events.sort(key=lambda x: x['time'])
            
            if timed_events:
                print(f"\nAnalyzing {len(timed_events)} timed events:")
                for e in timed_events:
                    if e['time'] <= current_time:
                        status = "COMPLETED" if e['time'] < current_time else "CURRENT"
                    else:
                        status = "UPCOMING"
                    print(f"  {e['time_str']} - {status}")
            
            # Find CURRENT or most recent event
            current_event = None
            
            if timed_events:
                # Check for ongoing event
                for i, event in enumerate(timed_events):
                    if event['time'] <= current_time:
                        if i + 1 < len(timed_events):
                            next_event = timed_events[i + 1]
                            if next_event['time'] > current_time:
                                current_event = event
                                print(f"\n✓ Current ongoing event: {event['time_str']}")
                                break
                        else:
                            current_event = event
                            print(f"\n✓ Last event of the day: {event['time_str']}")
                            break
                
                # If no ongoing, get most recent completed
                if not current_event:
                    for event in reversed(timed_events):
                        if event['time'] <= current_time:
                            current_event = event
                            print(f"\n✓ Most recent completed event: {event['time_str']}")
                            break
                
                # If all future, get first upcoming
                if not current_event:
                    current_event = timed_events[0]
                    print(f"\n⚠ No current events yet. Showing next upcoming: {current_event['time_str']}")
            
            # Use untimed event if no timed events
            if not current_event and untimed_events:
                current_event = untimed_events[0]
                print(f"\n⚠ Using untimed event")
            
            if not current_event:
                print("Could not determine current event")
                self._save_generic_schedule(now)
                return
            
            # Extract location and purpose
            description = current_event['description']
            description = re.sub(r'^Secretary\s+Rubio\s+', '', description, flags=re.IGNORECASE)
            
            # Extract location
            location_match = re.search(r'\bat\s+(?:the\s+)?(.*?)(?:\.|$|\()', description, re.IGNORECASE)
            
            if location_match:
                location = location_match.group(1).strip()
                location = re.sub(r'\s*\(.*?\)\s*$', '', location).strip()
                location = re.sub(r'^the\s+', '', location, flags=re.IGNORECASE)
                
                if 'white house' in location.lower():
                    location = 'The White House'
                elif 'department of state' in location.lower():
                    location = 'Department of State'
                else:
                    location = location.title()
            else:
                location = "Washington, D.C."
            
            # Format purpose
            purpose = description.strip()
            if not purpose.endswith('.'):
                purpose += '.'
            if len(purpose) > 200:
                purpose = purpose[:197] + '...'
            
            # Format date/time
            date_str = now.strftime("%B %d, %Y")
            if current_event['time_str']:
                date_time = f"{date_str} - {current_event['time_str']} (EST)"
            else:
                date_time = f"{date_str} - N/A"
            
            # Save to database
            self.db.add_or_update_figure(
                name="Secretary of State, Marco Rubio",
                location=location,
                date_time=date_time,
                purpose=purpose,
                category_type="country",
                category_id=self.country_id,
                source_url=schedule_url
            )
            
            print(f"\n{'='*50}")
            print(f"✓ Updated Marco Rubio:")
            print(f"  Location: {location}")
            print(f"  Time: {date_time}")
            print(f"  Purpose: {purpose}")
            print(f"{'='*50}")
            
        except requests.exceptions.HTTPError as e:
            print(f"✗ Website returned error ({e.response.status_code}), using generic schedule")
            self._save_generic_schedule(datetime.now())
        except Exception as e:
            print(f"✗ Error scraping Rubio's calendar: {str(e)}")
            import traceback
            traceback.print_exc()
            self._save_generic_schedule(datetime.now())
    
    def _save_generic_schedule(self, now):
        """Save generic schedule when no events found"""
        purpose = "Secretary of State's official duties and meetings."
        location = "Washington, D.C."
        date_time = now.strftime("%B %d, %Y")
        
        self.db.add_or_update_figure(
            name="Secretary of State, Marco Rubio",
            location=location,
            date_time=date_time,
            purpose=purpose,
            category_type="country",
            category_id=self.country_id,
            source_url="https://www.state.gov/public-schedule/"
        )
        
        print(f"\n{'='*50}")
        print(f"✓ Updated Marco Rubio (no specific events available):")
        print(f"  Location: {location}")
        print(f"  Time: {date_time}")
        print(f"  Purpose: {purpose}")
        print(f"{'='*50}")

def main():
    scraper = RubioCalendarScraper()
    scraper.scrape()

if __name__ == "__main__":
    main()
