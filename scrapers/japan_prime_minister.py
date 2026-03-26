#
# japan_prime_minister.py
# Scraper for Japanese Prime Minister Sanae Takaichi
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

class TakaichiCalendarScraper:
    def __init__(self):
        self.url = "https://japan.kantei.go.jp/news/index.html"
        self.db = Database()
        self.country_id = self.db.add_country("Japan")
        
    def scrape(self):
        """Scrape Prime Minister Takaichi's schedule"""
        try:
            print(f"Fetching Takaichi's schedule from {self.url}...")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            response = requests.get(self.url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Get today's date
            now = datetime.now()
            today_str = now.strftime("%B %d, %Y")
            
            # Find all news items
            items = soup.find_all('li')
            
            events = []
            for item in items:
                # Look for date
                date_text = item.get_text(strip=True)
                
                # Check if it's from today
                if self._is_today(date_text, now):
                    # Extract link for more details
                    link = item.find('a')
                    if link and link.get('href'):
                        event_url = link.get('href')
                        if not event_url.startswith('http'):
                            event_url = f"https://japan.kantei.go.jp{event_url}"
                        
                        # Extract title/purpose
                        title_parts = []
                        for text in item.stripped_strings:
                            title_parts.append(text)
                        
                        if len(title_parts) >= 2:
                            # Usually format: "Date Category Title"
                            category = title_parts[1] if len(title_parts) > 1 else ""
                            title = title_parts[-1] if len(title_parts) > 0 else ""
                            
                            events.append({
                                'title': title,
                                'category': category,
                                'url': event_url
                            })
            
            if events:
                # Use the most recent event
                latest_event = events[0]
                
                purpose = latest_event['title']
                if latest_event['category']:
                    purpose = f"{latest_event['category']}: {purpose}"
                
                location = self._extract_location(purpose)
                
                # Save to database
                self.db.add_or_update_figure(
                    name="Prime Minister, Sanae Takaichi",
                    location=location,
                    date_time=today_str,
                    purpose=purpose,
                    category_type="country",
                    category_id=self.country_id,
                    source_url=self.url,
                    display_order=1
                )
                
                print(f"\n{'='*50}")
                print(f"✓ Updated Sanae Takaichi:")
                print(f"  Location: {location}")
                print(f"  Time: {today_str}")
                print(f"  Purpose: {purpose}")
                print(f"{'='*50}")
                
            else:
                # No events today, use generic message
                purpose = "Prime Minister's daily duties and engagements."
                location = "Tokyo, Japan"
                
                self.db.add_or_update_figure(
                    name="Prime Minister, Sanae Takaichi",
                    location=location,
                    date_time=today_str,
                    purpose=purpose,
                    category_type="country",
                    category_id=self.country_id,
                    source_url=self.url,
                    display_order=1
                )
                
                print(f"\n{'='*50}")
                print(f"✓ Updated Sanae Takaichi (no specific events today):")
                print(f"  Location: {location}")
                print(f"  Time: {today_str}")
                print(f"  Purpose: {purpose}")
                print(f"{'='*50}")
            
        except Exception as e:
            print(f"✗ Error scraping Takaichi's schedule: {e}")
            import traceback
            traceback.print_exc()
    
    def _is_today(self, text, now):
        """Check if the text contains today's date"""
        # Format: "March 25, 2026"
        today_variants = [
            now.strftime("%B %d, %Y"),  # March 25, 2026
            now.strftime("%B %#d, %Y") if os.name == 'nt' else now.strftime("%B %-d, %Y"),  # March 25, 2026 (no leading zero)
        ]
        
        for variant in today_variants:
            if variant in text:
                return True
        
        return False
    
    def _extract_location(self, text):
        """Extract location from event text"""
        text_lower = text.lower()
        
        # Check for specific locations
        if 'united states' in text_lower or 'usa' in text_lower or 'washington' in text_lower:
            return 'Washington, D.C., United States'
        elif 'china' in text_lower or 'beijing' in text_lower:
            return 'Beijing, China'
        elif 'singapore' in text_lower:
            return 'Singapore'
        elif 'philippines' in text_lower or 'manila' in text_lower:
            return 'Manila, Philippines'
        elif 'malaysia' in text_lower or 'kuala lumpur' in text_lower:
            return 'Kuala Lumpur, Malaysia'
        elif 'arlington' in text_lower:
            return 'Arlington, Virginia, United States'
        elif 'south korea' in text_lower or 'seoul' in text_lower:
            return 'Seoul, South Korea'
        elif 'india' in text_lower or 'new delhi' in text_lower:
            return 'New Delhi, India'
        elif 'australia' in text_lower or 'canberra' in text_lower:
            return 'Canberra, Australia'
        elif 'france' in text_lower or 'paris' in text_lower:
            return 'Paris, France'
        elif 'germany' in text_lower or 'berlin' in text_lower:
            return 'Berlin, Germany'
        elif 'united kingdom' in text_lower or 'london' in text_lower:
            return 'London, United Kingdom'
        
        # Default to Tokyo
        return "Tokyo, Japan"

def main():
    scraper = TakaichiCalendarScraper()
    scraper.scrape()

if __name__ == "__main__":
    main()
