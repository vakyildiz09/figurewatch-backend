#
# canada_prime_minister.py
# Scraper for Canadian Prime Minister Mark Carney
# Created by V. Akyildiz on 31 January 2026.
# Copyright © 2026 FigureWatch. All rights reserved.
#

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import re
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import Database

class CarneyCalendarScraper:
    def __init__(self):
        self.base_url = "https://www.pm.gc.ca"
        self.advisories_url = "https://www.pm.gc.ca/en/news/media-advisories"
        self.db = Database()
        self.country_id = self.db.add_country("Canada")
        
    def scrape(self):
        """Scrape Prime Minister Carney's schedule"""
        try:
            # Get current time in Atlantic time
            atlantic = pytz.timezone('America/Halifax')
            now = datetime.now(atlantic)
            print(f"Current time in Halifax: {now.strftime('%B %d, %Y - %I:%M %p (GMT-3)')}")
            
            print(f"Fetching advisories list from {self.advisories_url}...")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            # Get the advisories list page
            response = requests.get(self.advisories_url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all advisory links
            advisory_links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                # Look for media advisory links
                if '/media-advisories/' in href and href not in advisory_links:
                    full_url = self.base_url + href if href.startswith('/') else href
                    advisory_links.append(full_url)
            
            print(f"Found {len(advisory_links)} advisory links")
            
            if not advisory_links:
                print("No advisory links found, using generic schedule")
                self._save_generic_schedule(now)
                return
            
            # Go through advisories one by one, most recent first
            for i, advisory_url in enumerate(advisory_links[:10], 1):  # Check up to 10 most recent
                print(f"\nChecking advisory {i}: {advisory_url}")
                
                try:
                    advisory_response = requests.get(advisory_url, headers=headers, timeout=10)
                    advisory_response.raise_for_status()
                    advisory_soup = BeautifulSoup(advisory_response.content, 'html.parser')
                    
                    # Extract events from this advisory
                    events = self._extract_events(advisory_soup, now)
                    
                    if events:
                        # Find the most recent completed event
                        completed_events = [e for e in events if e['completed']]
                        
                        if completed_events:
                            # Use the most recent completed event
                            latest = completed_events[-1]
                            
                            self.db.add_or_update_figure(
                                name="Prime Minister, Mark Carney",
                                location=latest['location'],
                                date_time=latest['time_display'],
                                purpose=latest['purpose'],
                                category_type="country",
                                category_id=self.country_id,
                                source_url=advisory_url,
                                display_order=1
                            )
                            
                            print(f"\n{'='*50}")
                            print(f"✓ Updated Mark Carney:")
                            print(f"  Location: {latest['location']}")
                            print(f"  Time: {latest['time_display']}")
                            print(f"  Purpose: {latest['purpose']}")
                            print(f"{'='*50}")
                            return
                        else:
                            print(f"  Advisory has {len(events)} event(s) but none completed yet")
                            # Continue to next advisory
                    else:
                        print("  No events found in this advisory")
                        
                except Exception as e:
                    print(f"  Error checking this advisory: {e}")
                    continue
            
            # If we've checked all advisories and found nothing
            print("\nNo completed events found in recent advisories")
            self._save_generic_schedule(now)
            
        except Exception as e:
            print(f"✗ Error scraping Carney's schedule: {e}")
            import traceback
            traceback.print_exc()
            self._save_generic_schedule(datetime.now(pytz.timezone('America/Halifax')))
    
    def _extract_events(self, soup, now):
        """Extract events from an advisory page"""
        events = []
        
        # Look for time patterns like "11:15 a.m." or "2:30 p.m."
        time_pattern = r'(\d{1,2}):(\d{2})\s*(a\.m\.|p\.m\.|AM|PM)'
        
        for paragraph in soup.find_all(['p', 'li']):
            text = paragraph.get_text()
            
            time_match = re.search(time_pattern, text, re.IGNORECASE)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2))
                meridiem = time_match.group(3).lower()
                
                # Convert to 24-hour format
                if 'p.m.' in meridiem or 'pm' in meridiem:
                    if hour != 12:
                        hour += 12
                elif hour == 12:
                    hour = 0
                
                # Extract purpose (text after the time)
                purpose = text[time_match.end():].strip()
                purpose = re.sub(r'^[-–—:]\s*', '', purpose)  # Remove leading dashes/colons
                purpose = purpose.split('.')[0] if '.' in purpose else purpose
                
                if purpose and len(purpose) > 10:  # Valid purpose
                    # Determine if event is completed
                    event_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    completed = event_time < now
                    
                    # Extract location
                    location = self._extract_location(text)
                    
                    time_display = f"{now.strftime('%B %d, %Y')} - {time_match.group(0).upper()} (GMT-3)"
                    
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
        
        # Common Canadian locations
        if 'ottawa' in text_lower:
            return 'Ottawa, Ontario'
        elif 'toronto' in text_lower:
            return 'Toronto, Ontario'
        elif 'montreal' in text_lower or 'montréal' in text_lower:
            return 'Montreal, Quebec'
        elif 'vancouver' in text_lower:
            return 'Vancouver, British Columbia'
        elif 'calgary' in text_lower:
            return 'Calgary, Alberta'
        elif 'quebec' in text_lower or 'québec' in text_lower:
            return 'Quebec City, Quebec'
        
        # Default to Ottawa
        return 'Ottawa, Ontario'
    
    def _save_generic_schedule(self, now):
        """Save generic schedule when no events found"""
        purpose = "Prime Minister's official duties and meetings."
        location = "Ottawa, Ontario"
        date_time = now.strftime("%B %d, %Y")
        
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
        print(f"✓ Updated Mark Carney (no specific events available):")
        print(f"  Location: {location}")
        print(f"  Time: {date_time}")
        print(f"  Purpose: {purpose}")
        print(f"{'='*50}")

def main():
    scraper = CarneyCalendarScraper()
    scraper.scrape()

if __name__ == "__main__":
    main()
