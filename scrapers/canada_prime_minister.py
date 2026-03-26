#
# canada_prime_minister.py
# Scraper for Canadian Prime Minister Mark Carney
# Created by V. Akyildiz on 26 March 2026.
# Copyright © 2026 FigureWatch. All rights reserved.
#

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import Database

class CarneyCalendarScraper:
    def __init__(self):
        self.base_url = "https://www.pm.gc.ca/en/news/media-advisories"
        self.db = Database()
        self.country_id = self.db.add_country("Canada")
        
    def scrape(self):
        """Scrape Prime Minister Carney's schedule"""
        try:
            # Get today's date to find the right advisory
            now = datetime.now()
            
            # Format the URL for today's advisory
            # Format: /2026/03/26/wednesday-march-26-2026
            day_name = now.strftime("%A").lower()  # "thursday"
            month_name = now.strftime("%B").lower()  # "march"
            day = now.strftime("%d")  # "26"
            year = now.strftime("%Y")  # "2026"
            
            # Try today's URL
            today_url = f"{self.base_url}/{year}/{now.month:02d}/{day}/{day_name}-{month_name}-{day}-{year}"
            
            print(f"Fetching Carney's schedule from {today_url}...")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            response = requests.get(today_url, headers=headers, timeout=30)
            
            if response.status_code == 404:
                # No schedule for today, use generic
                self._save_generic_schedule(now)
                return
            
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all event entries (times + descriptions)
            events = []
            
            # Look for time patterns like "11:15 a.m." or "1:35 p.m."
            time_pattern = re.compile(r'\d{1,2}:\d{2}\s*[ap]\.m\.')
            
            # Get main content
            main_content = soup.find('div', id='main-content') or soup.find('main')
            
            if main_content:
                # Split content by "Notes for media" to exclude that section
                content_text = main_content.get_text()
                
                # Stop at "Notes for media"
                if "Notes for media:" in content_text:
                    content_text = content_text.split("Notes for media:")[0]
                elif "Note for media:" in content_text:
                    content_text = content_text.split("Note for media:")[0]
                
                # Find all time entries
                lines = content_text.split('\n')
                current_time = None
                current_desc = []
                current_location = None
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Check if line has a time
                    time_match = time_pattern.search(line)
                    
                    if time_match:
                        # Save previous event if exists
                        if current_time and current_desc:
                            events.append({
                                'time': current_time,
                                'description': ' '.join(current_desc),
                                'location': current_location or 'Ottawa, Ontario'
                            })
                        
                        # Start new event
                        current_time = time_match.group()
                        # Get description after the time
                        desc = line.split(current_time, 1)[-1].strip()
                        current_desc = [desc] if desc else []
                    elif current_time:
                        # Add to current event description
                        # Skip if it's a "Note for media" line
                        if not line.startswith('Note'):
                            current_desc.append(line)
                    elif line.endswith(', Ontario') or line.endswith(', Canada'):
                        # This is a location header
                        current_location = line
                
                # Save last event
                if current_time and current_desc:
                    events.append({
                        'time': current_time,
                        'description': ' '.join(current_desc),
                        'location': current_location or 'Ottawa, Ontario'
                    })
            
            if events:
                # Use the first event of the day
                first_event = events[0]
                
                time_str = first_event['time']
                purpose = first_event['description']
                location = first_event['location']
                
                # Clean up purpose (remove "The Prime Minister will" prefix)
                purpose = purpose.replace('The Prime Minister will ', '')
                purpose = purpose.strip()
                
                # Capitalize first letter
                if purpose:
                    purpose = purpose[0].upper() + purpose[1:]
                
                # Format date/time
                date_time = f"{now.strftime('%B %d, %Y')} - {time_str}"
                
                # Save to database
                self.db.add_or_update_figure(
                    name="Prime Minister, Mark Carney",
                    location=location,
                    date_time=date_time,
                    purpose=purpose,
                    category_type="country",
                    category_id=self.country_id,
                    source_url=today_url,
                    display_order=1
                )
                
                print(f"\n{'='*50}")
                print(f"✓ Updated Mark Carney:")
                print(f"  Location: {location}")
                print(f"  Time: {date_time}")
                print(f"  Purpose: {purpose}")
                print(f"{'='*50}")
                
            else:
                # No events found
                self._save_generic_schedule(now)
            
        except Exception as e:
            print(f"✗ Error scraping Carney's schedule: {e}")
            import traceback
            traceback.print_exc()
            # Save generic schedule on error
            self._save_generic_schedule(datetime.now())
    
    def _save_generic_schedule(self, now):
        """Save generic schedule when no specific events found"""
        purpose = "Prime Minister's daily duties and government meetings."
        location = "Ottawa, Ontario"
        date_time = now.strftime("%B %d, %Y")
        
        self.db.add_or_update_figure(
            name="Prime Minister, Mark Carney",
            location=location,
            date_time=date_time,
            purpose=purpose,
            category_type="country",
            category_id=self.country_id,
            source_url=self.base_url,
            display_order=1
        )
        
        print(f"\n{'='*50}")
        print(f"✓ Updated Mark Carney (generic schedule):")
        print(f"  Location: {location}")
        print(f"  Time: {date_time}")
        print(f"  Purpose: {purpose}")
        print(f"{'='*50}")

def main():
    scraper = CarneyCalendarScraper()
    scraper.scrape()

if __name__ == "__main__":
    main()
