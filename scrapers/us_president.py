#
#  us_president.py
#  FigureWatch Backend
#
#  Created by V. Akyildiz on 7 January 2025.
#  Copyright © 2026 FigureWatch. All rights reserved.
#
#  This software is proprietary and confidential.
#  Unauthorized copying, distribution, or use is strictly prohibited.
#

#
#  us_president.py
#  FigureWatch Backend
#
#  Created by V. Akyildiz on 7 January 2025.
#  Copyright © 2026 FigureWatch. All rights reserved.
#
#  This software is proprietary and confidential.
#  Unauthorized copying, distribution, or use is strictly prohibited.
#

import requests
from bs4 import BeautifulSoup
from datetime import datetime, time as dt_time
import re
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import Database

class TrumpCalendarScraper:
    def __init__(self):
        self.url = "https://rollcall.com/factbase/trump/topic/calendar/"
        self.db = Database()
        self.country_id = self.db.add_country("United States")
    
    def extract_location(self, text):
        """Extract location from event text"""
        locations = {
            'Oval Office': 'Washington, D.C.',
            'White House': 'Washington, D.C.',
            'Mar-a-Lago': 'Palm Beach, Florida',
            'Trump International Golf Club': 'West Palm Beach, Florida',
            'Joint Base Andrews': 'Maryland',
            'Palm Beach International Airport': 'Palm Beach, Florida',
            'House GOP': 'Washington, D.C.',
            'Kennedy Center': 'Washington, D.C.',
            'Capitol': 'Washington, D.C.'
        }
        
        for key, location in locations.items():
            if key in text:
                return location
        
        return 'Washington, D.C.'
    
    def parse_time(self, time_str):
        """Parse time string to datetime.time object for comparison"""
        try:
            time_str = time_str.strip().upper()
            # Handle both "2:30 PM" and "2:30PM" formats
            time_str = re.sub(r'(\d+:\d+)\s*([AP]M)', r'\1 \2', time_str)
            return datetime.strptime(time_str, "%I:%M %p").time()
        except Exception as e:
            print(f"Error parsing time '{time_str}': {e}")
            return None
    
    def get_current_day_name(self):
        """Get current day name (e.g., 'Tuesday')"""
        return datetime.now().strftime("%A")
    
    def scrape(self):
        """Scrape Trump's calendar and get the CURRENT/ONGOING event for TODAY"""
        try:
            print(f"Fetching Trump's calendar from {self.url}...")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            response = requests.get(self.url, headers=headers, timeout=10)
            # Roll Call returns 404 status but still sends content, so don't raise for status
            # Just check if we got content
            if not response.text or len(response.text) < 1000:
                print(f"⚠ Response seems empty or too small")
                return
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Get current time in EST (Trump's schedule timezone)
            # Note: This assumes the server is running with proper timezone or we convert
            now = datetime.now()
            current_time = now.time()
            current_day = self.get_current_day_name()
            
            print(f"Looking for events on {current_day}, {now.strftime('%B %d, %Y')}")
            print(f"Current time for comparison: {current_time.strftime('%I:%M %p')} EST")
            
            # Find all tables
            tables = soup.find_all('table')
            
            events = []
            found_today = False
            
            for table in tables:
                table_text = table.get_text()
                
                # Check if this table contains today's date
                if current_day in table_text and str(now.day) in table_text:
                    found_today = True
                    print(f"✓ Found today's schedule ({current_day})")
                    
                    # Parse all time entries in this table
                    rows = table.find_all('tr')
                    
                    for row in rows:
                        row_text = row.get_text(separator=' ', strip=True)
                        
                        # Look for time pattern
                        time_matches = re.findall(r'(\d{1,2}:\d{2}\s*[AP]M)', row_text)
                        
                        if time_matches and 'President' in row_text:
                            time_str = time_matches[0]
                            event_time = self.parse_time(time_str)
                            
                            if event_time:
                                # Extract description
                                description = row_text
                                for tm in time_matches:
                                    description = description.replace(tm, '')
                                
                                description = re.sub(r'^\s*\d+\s*', '', description)
                                description = re.sub(r'\s+', ' ', description).strip()
                                
                                if len(description) > 10:
                                    events.append({
                                        'time': event_time,
                                        'time_str': time_str,
                                        'description': description
                                    })
                                    print(f"  Found event: {time_str} - {description[:80]}...")
                
                if found_today:
                    break
            
            if not found_today:
                print(f"⚠ Could not find today's schedule ({current_day})")
            
            if not events:
                print("No events found with times")
                return
            
            # Sort events by time
            events.sort(key=lambda x: x['time'])
            
            print(f"\nAnalyzing {len(events)} events:")
            for e in events:
                if e['time'] <= current_time:
                    status = "COMPLETED" if e['time'] < current_time else "CURRENT"
                else:
                    status = "UPCOMING"
                print(f"  {e['time_str']} - {status}")
            
            # Find CURRENT or most recent event
            # Logic: Find the event that is happening NOW or just finished
            current_event = None
            
            # First, check if there's an ongoing event (started but not yet surpassed by next event)
            for i, event in enumerate(events):
                # Event has started
                if event['time'] <= current_time:
                    # Check if next event has started
                    if i + 1 < len(events):
                        next_event = events[i + 1]
                        # If next event hasn't started yet, this is the current event
                        if next_event['time'] > current_time:
                            current_event = event
                            print(f"\n✓ Current ongoing event: {event['time_str']}")
                            break
                    else:
                        # This is the last event and it has started
                        current_event = event
                        print(f"\n✓ Last event of the day: {event['time_str']}")
                        break
            
            # If no ongoing event found, get the most recent completed one
            if not current_event:
                for event in reversed(events):
                    if event['time'] <= current_time:
                        current_event = event
                        print(f"\n✓ Most recent completed event: {event['time_str']}")
                        break
            
            # If still nothing (all events are in the future), get the first upcoming one
            if not current_event and events:
                current_event = events[0]
                print(f"\n⚠ No current events yet. Showing next upcoming: {current_event['time_str']}")
            
            if current_event:
                description = current_event['description']
                location = self.extract_location(description)
                
                # Clean up purpose
                purpose = description
                
                if 'The President' in purpose:
                    president_idx = purpose.find('The President')
                    purpose = purpose[president_idx:]
                    
                    stop_words = ['Oval Office', 'White House', 'Mar-a-Lago', 'Closed Press', 
                                'Open Press', 'In-Town Pool', 'Out-of-Town', 'Kennedy Center']
                    for stop in stop_words:
                        if stop in purpose:
                            purpose = purpose[:purpose.find(stop)].strip()
                            break
                
                purpose = re.sub(r'\s+', ' ', purpose).strip()
                purpose = purpose[:200]
                
                date_str = now.strftime("%B %d, %Y")
                # Add timezone indicator (EST)
                date_time = f"{date_str} - {current_event['time_str']} (EST)"
                
                self.db.add_or_update_figure(
                    name="President, Donald J. Trump",  # Added formal title
                    location=location,
                    date_time=date_time,
                    purpose=purpose,
                    category_type="country",
                    category_id=self.country_id,
                    source_url=self.url
                )
                
                print(f"\n{'='*50}")
                print(f"✓ Updated Donald Trump:")
                print(f"  Location: {location}")
                print(f"  Time: {date_time}")
                print(f"  Purpose: {purpose}")
                print(f"{'='*50}")
            else:
                print("Could not determine current event")
            
        except Exception as e:
            print(f"✗ Error scraping Trump's calendar: {str(e)}")
            import traceback
            traceback.print_exc()

def main():
    scraper = TrumpCalendarScraper()
    scraper.scrape()

if __name__ == "__main__":
    main()
