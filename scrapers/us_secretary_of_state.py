#
# us_secretary_of_state.py
# Scraper for U.S. Secretary of State Marco Rubio
# Created by V. Akyildiz on 31 January 2026.
# Copyright © 2026 FigureWatch. All rights reserved.
#

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import Database

class RubioCalendarScraper:
    def __init__(self):
        self.base_url = "https://www.state.gov"
        self.schedule_list_url = "https://www.state.gov/public-schedule/"
        self.db = Database()
        self.country_id = self.db.add_country("United States")
        
    def scrape(self):
        """Scrape Secretary Rubio's schedule"""
        try:
            print(f"Fetching Rubio's schedule list from {self.schedule_list_url}...")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            # Try Carney pattern first
            schedule_url = None
            try:
                response = requests.get(self.schedule_list_url, headers=headers, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find all schedule links
                schedule_links = []
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if '/public-schedule-' in href and '-2026' in href:
                        full_url = self.base_url + href if href.startswith('/') else href
                        if full_url not in schedule_links:
                            schedule_links.append(full_url)
                
                print(f"Found {len(schedule_links)} schedule links")
                
                if schedule_links:
                    schedule_url = schedule_links[0]  # Most recent
                    
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 407:
                    print("✗ 407 error when accessing list page, using URL construction fallback")
                else:
                    raise
            
            # Fallback to URL construction if Carney pattern failed
            if not schedule_url:
                print("Using URL construction fallback...")
                today = datetime.now()
                # Try today first, then yesterday, then day before
                for days_back in range(7):
                    target_date = today - timedelta(days=days_back)
                    constructed_url = f"https://www.state.gov/releases/office-of-the-spokesperson/{target_date.year}/{target_date.month:02d}/public-schedule-{target_date.strftime('%B-%d-%Y').lower()}/"
                    
                    try:
                        test_response = requests.get(constructed_url, headers=headers, timeout=10)
                        if test_response.status_code == 200:
                            schedule_url = constructed_url
                            print(f"Found schedule at: {schedule_url}")
                            break
                    except:
                        continue
            
            if not schedule_url:
                print("No schedule found")
                self._save_generic_schedule(datetime.now())
                return
            
            # Now scrape the schedule page
            print(f"Loading schedule from {schedule_url}")
            schedule_response = requests.get(schedule_url, headers=headers, timeout=10)
            schedule_response.raise_for_status()
            schedule_soup = BeautifulSoup(schedule_response.content, 'html.parser')
            
            # Extract date from URL (e.g., "public-schedule-march-27-2026")
            date_match = re.search(r'public-schedule-(\w+)-(\d+)-(\d{4})', schedule_url)
            if date_match:
                month_name = date_match.group(1).capitalize()
                day = int(date_match.group(2))
                year = int(date_match.group(3))
                
                months = ['January', 'February', 'March', 'April', 'May', 'June',
                          'July', 'August', 'September', 'October', 'November', 'December']
                month_num = months.index(month_name) + 1
                
                schedule_date = datetime(year, month_num, day)
                print(f"Schedule date: {schedule_date.strftime('%B %d, %Y')}")
            else:
                schedule_date = datetime.now()
            
            # Extract events
            events = self._extract_events(schedule_soup, schedule_date, datetime.now())
            
            if events:
                # Find most recent completed event
                completed_events = [e for e in events if e['completed']]
                
                if completed_events:
                    latest = completed_events[-1]
                    
                    self.db.add_or_update_figure(
                        name="Secretary of State, Marco Rubio",
                        location=latest['location'],
                        date_time=latest['time_display'],
                        purpose=latest['purpose'],
                        category_type="country",
                        category_id=self.country_id,
                        source_url=schedule_url,
                        display_order=999
                    )
                    
                    print(f"\n{'='*50}")
                    print(f"✓ Updated Marco Rubio:")
                    print(f"  Location: {latest['location']}")
                    print(f"  Time: {latest['time_display']}")
                    print(f"  Purpose: {latest['purpose']}")
                    print(f"{'='*50}")
                else:
                    print(f"Found {len(events)} event(s) but none completed yet")
                    self._save_generic_schedule(datetime.now())
            else:
                print("No events found in schedule")
                self._save_generic_schedule(datetime.now())
                
        except Exception as e:
            print(f"✗ Error scraping Rubio's schedule: {e}")
            import traceback
            traceback.print_exc()
            self._save_generic_schedule(datetime.now())
    
    def _get_timezone_offset(self, location):
        """Get timezone offset from UTC for a given location"""
        # Mapping of locations to UTC offset
        timezone_map = {
            'Washington, D.C., U.S.': -5,  # EST
            'White House, Washington, D.C.': -5,
            'Department of State, Washington, D.C.': -5,
            'Paris, France': 1,  # CET
            'London, United Kingdom': 0,  # GMT
            'Berlin, Germany': 1,  # CET
            'Brussels, Belgium': 1,  # CET
            'Tokyo, Japan': 9,  # JST
            'Beijing, China': 8,  # CST
            'Moscow, Russia': 3,  # MSK
            'Kyiv, Ukraine': 2,  # EET
        }
        
        return timezone_map.get(location, 1)  # Default to CET
    
    def _get_timezone_name(self, location):
        """Get timezone abbreviation for display"""
        timezone_names = {
            'Washington, D.C., U.S.': 'EST',
            'White House, Washington, D.C.': 'EST',
            'Department of State, Washington, D.C.': 'EST',
            'Paris, France': 'CET',
            'London, United Kingdom': 'GMT',
            'Berlin, Germany': 'CET',
            'Brussels, Belgium': 'CET',
            'Tokyo, Japan': 'JST',
            'Beijing, China': 'CST',
            'Moscow, Russia': 'MSK',
            'Kyiv, Ukraine': 'EET',
        }
        
        return timezone_names.get(location, 'CET')
    
    def _extract_events(self, soup, schedule_date, current_time):
        """Extract events from schedule page"""
        events = []
        
        # Look for time patterns like "8:45 AM" or "2:15 PM"
        time_pattern = r'(\d{1,2}):(\d{2})\s*(AM|PM|a\.m\.|p\.m\.)'
        
        # Vienna is in CET (UTC+1)
        vienna_offset = 1
        
        # Search in all text elements
        for element in soup.find_all(['p', 'li', 'div']):
            text = element.get_text()
            
            # Check if "LOCAL" is present (means not in Washington D.C.)
            is_local = 'LOCAL' in text.upper()
            
            # Remove "LOCAL" prefix
            text = re.sub(r'\bLOCAL\s*', '', text, flags=re.IGNORECASE)
            
            time_match = re.search(time_pattern, text, re.IGNORECASE)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2))
                meridiem = time_match.group(3).upper()
                
                # Convert to 24-hour format
                if 'PM' in meridiem or 'p.m.' in meridiem.lower():
                    if hour != 12:
                        hour += 12
                elif hour == 12:
                    hour = 0
                
                # Extract purpose (text after the time, up to next time or line break)
                purpose_start = time_match.end()
                remaining_text = text[purpose_start:]
                
                # Find the next time pattern or double line break to end the purpose
                next_time = re.search(time_pattern, remaining_text)
                if next_time:
                    purpose = remaining_text[:next_time.start()].strip()
                else:
                    # Take text until line break or reasonable length
                    lines = remaining_text.split('\n')
                    purpose = lines[0].strip() if lines else remaining_text[:200].strip()
                
                purpose = re.sub(r'^[-–—:.\s]+', '', purpose)
                
                # Only include events for Secretary Rubio
                # Must contain "Secretary Rubio" or "the Secretary" or just "Secretary" at start
                purpose_lower = purpose.lower()
                if not any(phrase in purpose_lower for phrase in ['secretary rubio', 'the secretary']):
                    # Also check if it starts with "Secretary" (not Assistant/Deputy Secretary)
                    if not (purpose_lower.startswith('secretary ') and 
                            'assistant' not in purpose_lower and 
                            'deputy' not in purpose_lower):
                        continue
                
                if purpose and len(purpose) > 10:
                    # Extract location from the cleaned purpose text
                    location = self._extract_location(purpose)
                    
                    # Get timezone offset for the location
                    location_offset = self._get_timezone_offset(location)
                    timezone_name = self._get_timezone_name(location)
                    
                    # Convert event time to Vienna time (CET)
                    # Formula: Vienna_time = Local_time + (Vienna_offset - Location_offset)
                    time_difference = vienna_offset - location_offset
                    vienna_hour = (hour + time_difference) % 24
                    
                    # Create event time using schedule date and Vienna-adjusted hour
                    event_time = schedule_date.replace(hour=vienna_hour, minute=minute, second=0, microsecond=0)
                    
                    # Build time display
                    # Show timezone only if not in Vienna timezone (CET)
                    if location_offset == vienna_offset:
                        time_display = f"{schedule_date.strftime('%d %B %Y')} - {time_match.group(0).upper()}"
                    else:
                        time_display = f"{schedule_date.strftime('%d %B %Y')} - {time_match.group(0).upper()} ({timezone_name})"
                    
                    # Determine if completed by comparing against current actual time
                    completed = event_time < current_time
                    
                    events.append({
                        'time': event_time,
                        'time_display': time_display,
                        'purpose': purpose.strip(),
                        'location': location,
                        'completed': completed
                    })
        
        return sorted(events, key=lambda x: x['time'])
    
    def _extract_location(self, text):
        """Extract location from event text"""
        text_lower = text.lower()
        
        # Check for specific buildings in Washington D.C.
        if 'white house' in text_lower:
            return 'White House, Washington, D.C.'
        elif 'department of state' in text_lower or 'state department' in text_lower:
            return 'Department of State, Washington, D.C.'
        
        # Look for pattern "in [City], [Country]"
        location_match = re.search(r'\bin\s+([A-Za-z\-]+(?:\s+[A-Za-z\-]+)?),\s*([A-Za-z\s]+?)\.', text)
        if location_match:
            city = location_match.group(1).strip()
            country = location_match.group(2).strip()
            return f"{city}, {country}"
        
        # Check for other cities/countries
        if 'france' in text_lower and 'paris' not in text_lower:
            # Extract French city if mentioned
            france_match = re.search(r'([A-Z][a-z]+(?:-[A-Z][a-z]+)*),?\s+France', text, re.IGNORECASE)
            if france_match:
                return f"{france_match.group(1)}, France"
            return 'Paris, France'
        elif 'paris' in text_lower:
            return 'Paris, France'
        elif 'london' in text_lower:
            return 'London, United Kingdom'
        elif 'berlin' in text_lower:
            return 'Berlin, Germany'
        elif 'brussels' in text_lower:
            return 'Brussels, Belgium'
        elif 'tokyo' in text_lower:
            return 'Tokyo, Japan'
        elif 'beijing' in text_lower:
            return 'Beijing, China'
        elif 'moscow' in text_lower:
            return 'Moscow, Russia'
        elif 'kyiv' in text_lower or 'kiev' in text_lower:
            return 'Kyiv, Ukraine'
        
        # Default to Washington D.C.
        return 'Washington, D.C., U.S.'
    
    def _save_generic_schedule(self, now):
        """Save generic schedule when no events found"""
        purpose = "Secretary of State's official duties and meetings."
        location = "Washington, D.C., U.S."
        date_time = now.strftime("%d %B %Y")
        
        self.db.add_or_update_figure(
            name="Secretary of State, Marco Rubio",
            location=location,
            date_time=date_time,
            purpose=purpose,
            category_type="country",
            category_id=self.country_id,
            source_url=self.schedule_list_url,
            display_order=999
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
