#
# turkiye_foreign_minister.py
# Scraper for Turkish Foreign Minister Hakan Fidan
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

class FidanCalendarScraper:
    def __init__(self):
        self.url = "https://www.mfa.gov.tr/sub.en.mfa?7342a8d1-3117-42aa-8ddd-01adb5653889"
        self.db = Database()
        self.country_id = self.db.add_country("Türkiye")
        
    def scrape(self):
        """Scrape Foreign Minister Fidan's schedule"""
        try:
            print(f"Fetching Fidan's news from {self.url}...")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            response = requests.get(self.url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all links on the page
            links = soup.find_all('a', href=True)
            
            # Filter for news/activity links and get the first (most recent) one
            for link in links:
                href = link.get('href', '')
                link_text = link.get_text().strip()
                
                # Look for actual news article links (end with .en.mfa and have descriptive slugs)
                if not '.en.mfa' in href:
                    continue
                
                # Skip if it's the main page or navigation
                if href == self.url or 'sub.en.mfa' in href:
                    continue
                
                # Skip empty or very short links
                if len(link_text) < 20:
                    continue
                
                # Skip header/navigation links
                if 'REPUBLIC' in link_text.upper() or 'MINISTRY' in link_text.upper():
                    continue
                
                # This should be a news item
                print(f"Found latest link: {link_text}")
                
                # Extract purpose from link text
                purpose = self._convert_to_present_tense(link_text)
                
                # Extract location from link text
                location = self._extract_location(link_text)
                
                # Extract date from link text or page
                date_str = self._extract_date(link_text, soup)
                
                # Save to database
                self.db.add_or_update_figure(
                    name="Foreign Minister, Hakan Fidan",
                    location=location,
                    date_time=date_str,
                    purpose=purpose,
                    category_type="country",
                    category_id=self.country_id,
                    source_url=self.url,
                    display_order=2
                )
                
                print(f"\n{'='*50}")
                print(f"✓ Updated Hakan Fidan:")
                print(f"  Location: {location}")
                print(f"  Time: {date_str}")
                print(f"  Purpose: {purpose}")
                print(f"{'='*50}")
                return
            
            # If no suitable links found
            print("No news links found")
            self._save_generic_schedule(datetime.now())
            
        except Exception as e:
            print(f"✗ Error scraping Fidan's schedule: {e}")
            import traceback
            traceback.print_exc()
            self._save_generic_schedule(datetime.now())
    
    def _convert_to_present_tense(self, text):
        """Convert past tense phrases to present tense and clean up"""
        # Remove "Minister of Foreign Affairs Hakan Fidan" prefix
        text = re.sub(r'^Minister of Foreign Affairs Hakan Fidan\s+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'^Foreign Minister Hakan Fidan\s+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'^Hakan Fidan\s+', '', text, flags=re.IGNORECASE)
        
        # Remove dates in format "23 March 2026"
        text = re.sub(r',?\s*\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}', '', text, flags=re.IGNORECASE)
        
        # Remove dates in format "23.03.2026"
        text = re.sub(r',?\s*\d{1,2}\.\d{1,2}\.\d{4}', '', text)
        
        # Remove trailing location mentions like ", Ankara"
        text = re.sub(r',\s+(?:Ankara|Istanbul|Brussels|Washington|New York|Paris|Berlin|London|Moscow|Damascus|Baghdad|Cairo)\s*$', '', text, flags=re.IGNORECASE)
        
        # Convert "met with" to "Meeting with"
        text = re.sub(r'\bmet with\b', 'Meeting with', text, flags=re.IGNORECASE)
        
        # Convert "held talks with" to "Holding talks with"
        text = re.sub(r'\bheld talks with\b', 'Holding talks with', text, flags=re.IGNORECASE)
        
        # Convert "received" to "Receiving"
        text = re.sub(r'\breceived\b', 'Receiving', text, flags=re.IGNORECASE)
        
        # Convert "attended" to "Attending"
        text = re.sub(r'\battended\b', 'Attending', text, flags=re.IGNORECASE)
        
        # Convert "participated in" to "Participating in"
        text = re.sub(r'\bparticipated in\b', 'Participating in', text, flags=re.IGNORECASE)
        
        # Convert "visited" to "Visiting"
        text = re.sub(r'\bvisited\b', 'Visiting', text, flags=re.IGNORECASE)
        
        # Clean up extra spaces and commas
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r',\s*,', ',', text)
        text = text.strip(', ')
        
        return text.strip()
    
    def _extract_location(self, text):
        """Extract location from link text"""
        text_lower = text.lower()
        
        # Check for specific locations
        if 'ankara' in text_lower:
            return 'Ankara, Türkiye'
        elif 'istanbul' in text_lower:
            return 'Istanbul, Türkiye'
        elif 'brussels' in text_lower or 'brüksel' in text_lower:
            return 'Brussels, Belgium'
        elif 'washington' in text_lower:
            return 'Washington, D.C., United States'
        elif 'new york' in text_lower:
            return 'New York, United States'
        elif 'paris' in text_lower:
            return 'Paris, France'
        elif 'berlin' in text_lower:
            return 'Berlin, Germany'
        elif 'london' in text_lower:
            return 'London, United Kingdom'
        elif 'moscow' in text_lower:
            return 'Moscow, Russia'
        elif 'damascus' in text_lower:
            return 'Damascus, Syria'
        elif 'baghdad' in text_lower:
            return 'Baghdad, Iraq'
        elif 'cairo' in text_lower:
            return 'Cairo, Egypt'
        
        # Default to Ankara
        return 'Ankara, Türkiye'
    
    def _extract_date(self, text, soup):
        """Extract date from link text or page"""
        # Look for date patterns in the text
        # Turkish date format: DD.MM.YYYY or DD Month YYYY
        
        # Try DD.MM.YYYY format
        date_match = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', text)
        if date_match:
            day = int(date_match.group(1))
            month = int(date_match.group(2))
            year = int(date_match.group(3))
            try:
                date_obj = datetime(year, month, day)
                return date_obj.strftime("%B %d, %Y")
            except:
                pass
        
        # Try to find date in English format
        months = ['January', 'February', 'March', 'April', 'May', 'June',
                  'July', 'August', 'September', 'October', 'November', 'December']
        
        for month in months:
            pattern = rf'(\d{{1,2}})\s+{month}\s+(\d{{4}})'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                day = int(match.group(1))
                year = int(match.group(2))
                month_num = months.index(month) + 1
                try:
                    date_obj = datetime(year, month_num, day)
                    return date_obj.strftime("%B %d, %Y")
                except:
                    pass
        
        # Fallback to today's date
        return datetime.now().strftime("%B %d, %Y")
    
    def _save_generic_schedule(self, now):
        """Save generic schedule when no events found"""
        purpose = "Foreign Minister's official duties and meetings."
        location = "Ankara, Türkiye"
        date_time = now.strftime("%B %d, %Y")
        
        self.db.add_or_update_figure(
            name="Foreign Minister, Hakan Fidan",
            location=location,
            date_time=date_time,
            purpose=purpose,
            category_type="country",
            category_id=self.country_id,
            source_url=self.url,
            display_order=2
        )
        
        print(f"\n{'='*50}")
        print(f"✓ Updated Hakan Fidan (no specific events today):")
        print(f"  Location: {location}")
        print(f"  Time: {date_time}")
        print(f"  Purpose: {purpose}")
        print(f"{'='*50}")

def main():
    scraper = FidanCalendarScraper()
    scraper.scrape()

if __name__ == "__main__":
    main()
