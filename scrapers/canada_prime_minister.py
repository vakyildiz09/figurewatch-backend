#
# canada_prime_minister.py
# Scraper for Canadian Prime Minister Mark Carney
# Created by V. Akyildiz on 26 March 2026.
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

class CarneyCalendarScraper:
    def __init__(self):
        self.advisories_url = "https://www.pm.gc.ca/en/news/media-advisories"
        self.db = Database()
        self.country_id = self.db.add_country("Canada")
        
    def scrape(self):
        """Scrape Prime Minister Carney's schedule"""
        try:
            # Get current UTC time and convert to Halifax time (GMT-3)
            utc_now = datetime.utcnow()
            halifax_now = utc_now - timedelta(hours=3)
            
            print(f"Current time in Halifax: {halifax_now.strftime('%B %d, %Y - %I:%M %p')} (GMT-3)")
            
            # Step 1: Get the main advisories page
            print(f"Fetching advisories list from {self.advisories_url}...")
            
            headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
            response = requests.get(self.advisories_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Step 2: Find all advisory links - try multiple patterns
            advisory_links = []
            
            # Pattern 1: Look in any <a> tag
            all_links = soup.find_all('a', href=True)
            print(f"Found {len(all_links)} total links on page")
            
            for link in all_links:
                href = link['href']
                
                # Check if this is a media advisory link
                # Format: /en/news/media-advisories/YYYY/MM/DD/title
                if '/media-advisories/' in href:
                    # Count slashes to ensure it's a specific advisory, not the main page
                    if href.count('/') >= 7:
                        # Make absolute
                        if href.startswith('/'):
                            full_url = f"https://www.pm.gc.ca{href}"
                        else:
                            full_url = href
                        
                        if full_url not in advisory_links:
                            advisory_links.append(full_url)
                            print(f"  Found advisory: {full_url}")
            
            print(f"\nTotal advisory links found: {len(advisory_links)}")
            
            if not advisory_links:
                print("No advisory links found - trying fallback to construct today's URL")
                # Fallback: try to construct today's and yesterday's URLs
                fallback_links = self._get_fallback_urls(halifax_now)
                advisory_links = fallback_links
                print(f"Using {len(fallback_links)} fallback URLs")
            
            if not advisory_links:
                print("No advisories available")
                self._save_generic_schedule()
                return
            
            # Step 3: Try advisories in order until we find a past event
            for advisory_url in advisory_links[:5]:  # Check up to 5 most recent
                print(f"\nChecking: {advisory_url}")
                
                latest_event = self._get_latest_event_from_url(advisory_url, halifax_now)
                
                if latest_event:
                    # Found a past event! Save and return
                    self.db.add_or_update_figure(
                        name="Prime Minister, Mark Carney",
                        location=latest_event['location'],
                        date_time=latest_event['date_time'],
                        purpose=latest_event['description'],
                        category_type="country",
                        category_id=self.country_id,
                        source_url=advisory_url,
                        display_order=1
                    )
                    
                    print(f"\n{'='*50}")
                    print(f"✓ Updated Mark Carney:")
                    print(f"  Location: {latest_event['location']}")
                    print(f"  Time: {latest_event['date_time']}")
                    print(f"  Purpose: {latest_event['description']}")
                    print(f"{'='*50}")
                    return
            
            # No past events found in any recent advisory
            print("No past events found in recent advisories")
            self._save_generic_schedule()
            
        except Exception as e:
            print(f"✗ Error scraping Carney's schedule: {e}")
            import traceback
            traceback.print_exc()
            self._save_generic_schedule()
    
    def _get_fallback_urls(self, halifax_now):
        """Generate fallback URLs for recent dates"""
        urls = []
        
        for days_ago in range(5):  # Try last 5 days
            target_date = halifax_now.date() - timedelta(days=days_ago)
            
            # Try both publication date = event date and publication date = event date - 1
            for pub_offset in [0, 1, 2]:
                pub_date = target_date - timedelta(days=pub_offset)
                
                pub_year = pub_date.strftime("%Y")
                pub_month = pub_date.strftime("%m")
                pub_day = pub_date.strftime("%d")
                
                event_day_name = target_date.strftime("%A").lower()
                event_month_name = target_date.strftime("%B").lower()
                event_day = target_date.strftime("%d")
                event_year = target_date.strftime("%Y")
                
                url = f"https://www.pm.gc.ca/en/news/media-advisories/{pub_year}/{pub_month}/{pub_day}/{event_day_name}-{event_month_name}-{event_day}-{event_year}"
                urls.append(url)
        
        return urls
    
    def _get_latest_event_from_url(self, advisory_url, current_time):
        """Extract latest past event from an advisory page"""
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
            response = requests.get(advisory_url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                print(f"  Status: {response.status_code}")
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract event date from URL
            # Pattern: /2026/03/24/wednesday-march-25-2026
            title_match = re.search(r'/([a-z]+)-([a-z]+)-(\d{1,2})-(\d{4})$', advisory_url)
            
            if title_match:
                month_name = title_match.group(2).capitalize()
                day = int(title_match.group(3))
                year = int(title_match.group(4))
                event_date = datetime.strptime(f"{month_name} {day}, {year}", "%B %d, %Y")
            else:
                # Fallback to today
                event_date = datetime.now()
            
            # Extract events - try multiple selectors
            main_content = soup.find('div', id='main-content')
            if not main_content:
                main_content = soup.find('main')
            if not main_content:
                main_content = soup.find('div', class_='main-content')
            if not main_content:
                main_content = soup.find('article')
            if not main_content:
                # Just use the whole body if we can't find specific content area
                main_content = soup.find('body')
            
            if not main_content:
                print("  No content found at all")
                return None
            
            events = []
            current_location = "Ottawa, Ontario"
            
            for elem in main_content.find_all(['h2', 'p']):
                text = elem.get_text(strip=True)
                
                # Location header
                if elem.name == 'h2':
                    if ', ' in text and 'Share' not in text:
                        current_location = text
                        continue
                
                # Event with time
                if elem.name == 'p':
                    if text.startswith('Note for media') or text.startswith('Notes for media'):
                        break
                    
                    time_match = re.search(r'\b(\d{1,2}):(\d{2})\s*([ap])\.m\.\b', text)
                    
                    if time_match:
                        hour = int(time_match.group(1))
                        minute = int(time_match.group(2))
                        period = time_match.group(3)
                        
                        # Convert to 24-hour
                        if period == 'p' and hour != 12:
                            hour_24 = hour + 12
                        elif period == 'a' and hour == 12:
                            hour_24 = 0
                        else:
                            hour_24 = hour
                        
                        # Create datetime for this event
                        event_datetime = datetime(
                            event_date.year,
                            event_date.month,
                            event_date.day,
                            hour_24,
                            minute,
                            0
                        )
                        
                        time_str = f"{time_match.group(1)}:{time_match.group(2)} {period}.m."
                        
                        # Get description
                        description = text.split(time_match.group(0), 1)[-1].strip()
                        description = description.replace('The Prime Minister will ', '')
                        description = description.strip()
                        
                        if description and description[0].islower():
                            description = description[0].upper() + description[1:]
                        
                        if description and not description.endswith('.'):
                            description += '.'
                        
                        events.append({
                            'time': time_str,
                            'datetime': event_datetime,
                            'description': description,
                            'location': current_location
                        })
            
            # Filter to only past events
            past_events = [e for e in events if e['datetime'] <= current_time]
            
            if past_events:
                # Get the most recent past event
                past_events.sort(key=lambda x: x['datetime'])
                latest = past_events[-1]
                
                print(f"  Found {len(past_events)} past events, showing latest")
                
                return {
                    'location': latest['location'],
                    'date_time': f"{event_date.strftime('%B %d, %Y')} - {latest['time']} (GMT-3)",
                    'description': latest['description']
                }
            
            print(f"  Found {len(events)} events, but none have occurred yet")
            return None
            
        except Exception as e:
            print(f"  Error: {e}")
            return None
    
    def _save_generic_schedule(self):
        """Save generic schedule when no events found"""
        purpose = "Prime Minister's daily duties and government meetings."
        location = "Ottawa, Ontario"
        date_time = datetime.now().strftime("%B %d, %Y")
        
        self.db.add_or_update_figure(
            name="Prime Minister, Mark Carney",
            location=location,
            date_time=date_time,
            purpose=purpose,
            category_type="country",
            category_id=self.country_id,
            source_url=self.advisories_url,
            display_order=1
        )
        
        print(f"\n{'='*50}")
        print(f"✓ Updated Mark Carney (no recent events):")
        print(f"  Location: {location}")
        print(f"  Time: {date_time}")
        print(f"  Purpose: {purpose}")
        print(f"{'='*50}")

def main():
    scraper = CarneyCalendarScraper()
    scraper.scrape()

if __name__ == "__main__":
    main()
