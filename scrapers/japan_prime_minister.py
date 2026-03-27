#
# japan_prime_minister.py
# Scraper for Japanese Prime Minister Sanae Takaichi
# Created by V. Akyildiz on 31 January 2026.
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
            
            response = requests.get(self.url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Get today's date
            now = datetime.now()
            today_str = now.strftime("%B %d, %Y")
            
            # Look for news/schedule items
            news_items = soup.find_all(['article', 'div'], class_=['news', 'schedule', 'item'])
            
            latest_event = None
            for item in news_items[:10]:  # Check first 10 items
                item_text = item.get_text()
                
                # Check if this is today's event
                if self._contains_today(item_text, now):
                    # Extract title
                    title = item.find(['h2', 'h3', 'a'])
                    if title:
                        purpose = title.get_text().strip()
                        
                        # Remove "Prime Minister in Action" prefix if present
                        purpose = re.sub(r'^Prime Minister in Action\s*[-:]\s*', '', purpose, flags=re.IGNORECASE)
                        
                        latest_event = {
                            'purpose': purpose,
                            'location': 'Tokyo, Japan'
                        }
                        break
            
            if latest_event:
                self.db.add_or_update_figure(
                    name="Prime Minister, Sanae Takaichi",
                    location=latest_event['location'],
                    date_time=today_str,
                    purpose=latest_event['purpose'],
                    category_type="country",
                    category_id=self.country_id,
                    source_url=self.url,
                    display_order=1
                )
                
                print(f"\n{'='*50}")
                print(f"✓ Updated Sanae Takaichi:")
                print(f"  Location: {latest_event['location']}")
                print(f"  Time: {today_str}")
                print(f"  Purpose: {latest_event['purpose']}")
                print(f"{'='*50}")
            else:
                # No events for today
                self._save_generic_schedule(now)
            
        except requests.exceptions.HTTPError as e:
            # Handle 404 or other HTTP errors gracefully
            print(f"✗ Website returned error ({e.response.status_code}), using generic schedule")
            self._save_generic_schedule(datetime.now())
        except Exception as e:
            print(f"✗ Error scraping Takaichi's schedule: {e}")
            self._save_generic_schedule(datetime.now())
    
    def _contains_today(self, text, now):
        """Check if text contains today's date"""
        formats = [
            now.strftime("%B %d, %Y"),
            now.strftime("%Y/%m/%d"),
            now.strftime("%Y-%m-%d"),
        ]
        
        for date_format in formats:
            if date_format in text:
                return True
        
        return False
    
    def _save_generic_schedule(self, now):
        """Save generic schedule when no events found"""
        purpose = "Prime Minister's official duties and meetings."
        location = "Tokyo, Japan"
        date_time = now.strftime("%B %d, %Y")
        
        self.db.add_or_update_figure(
            name="Prime Minister, Sanae Takaichi",
            location=location,
            date_time=date_time,
            purpose=purpose,
            category_type="country",
            category_id=self.country_id,
            source_url=self.url,
            display_order=1
        )
        
        print(f"\n{'='*50}")
        print(f"✓ Updated Sanae Takaichi (no specific events today):")
        print(f"  Location: {location}")
        print(f"  Time: {date_time}")
        print(f"  Purpose: {purpose}")
        print(f"{'='*50}")

def main():
    scraper = TakaichiCalendarScraper()
    scraper.scrape()

if __name__ == "__main__":
    main()
