#
# italy_prime_minister.py
# Scraper for Italian Prime Minister Giorgia Meloni
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

class MeloniCalendarScraper:
    def __init__(self):
        self.base_url = "https://www.governo.it"
        self.news_url = "https://www.governo.it/en/notizie-presidente-en"
        self.db = Database()
        self.country_id = self.db.add_country("Italy")
        
    def scrape(self):
        """Scrape Prime Minister Meloni's schedule"""
        try:
            print(f"Fetching Meloni's news from {self.news_url}...")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            # Get the news list page
            response = requests.get(self.news_url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all news article links
            article_links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                link_text = link.get_text().strip().lower()
                
                # Skip "Statement by" articles
                if 'statement by' in link_text:
                    continue
                
                # Look for article links (typically /en/articolo/...)
                if '/en/articolo/' in href or '/articolo/' in href:
                    full_url = self.base_url + href if href.startswith('/') else href
                    if full_url not in article_links:
                        article_links.append(full_url)
            
            print(f"Found {len(article_links)} article links (excluding statements)")
            
            if not article_links:
                print("No article links found, using generic schedule")
                self._save_generic_schedule(datetime.now())
                return
            
            # Try articles one by one, most recent first
            for i, article_url in enumerate(article_links[:5], 1):
                print(f"\nChecking article {i}: {article_url}")
                
                try:
                    article_response = requests.get(article_url, headers=headers, timeout=10)
                    article_response.raise_for_status()
                    article_soup = BeautifulSoup(article_response.content, 'html.parser')
                    
                    # Extract article title
                    title = None
                    title_tag = article_soup.find('h1')
                    if title_tag:
                        title = title_tag.get_text().strip()
                    
                    if not title:
                        print("  No title found, skipping")
                        continue
                    
                    print(f"  Title: {title}")
                    
                    # Extract date from article
                    date_str = None
                    date_tag = article_soup.find('time')
                    if date_tag and date_tag.get('datetime'):
                        date_str = date_tag.get('datetime')
                    
                    # Parse date
                    article_date = None
                    if date_str:
                        try:
                            # Format: 2026-03-25T00:00:00+01:00
                            article_date = datetime.fromisoformat(date_str.replace('+01:00', ''))
                            print(f"  Date: {article_date.strftime('%B %d, %Y')}")
                        except:
                            pass
                    
                    # Check if article is recent (within last 3 days)
                    now = datetime.now()
                    if article_date:
                        days_ago = (now - article_date).days
                        if days_ago > 3:
                            print(f"  Article is {days_ago} days old, skipping")
                            continue
                    
                    # Extract purpose from title
                    purpose = self._extract_purpose(title)
                    
                    # Extract location
                    location = self._extract_location(title, article_soup)
                    
                    # Format date/time
                    if article_date:
                        date_time = article_date.strftime("%B %d, %Y")
                    else:
                        date_time = now.strftime("%B %d, %Y")
                    
                    # Save to database
                    self.db.add_or_update_figure(
                        name="Prime Minister, Giorgia Meloni",
                        location=location,
                        date_time=date_time,
                        purpose=purpose,
                        category_type="country",
                        category_id=self.country_id,
                        source_url=article_url,
                        display_order=1
                    )
                    
                    print(f"\n{'='*50}")
                    print(f"✓ Updated Giorgia Meloni:")
                    print(f"  Location: {location}")
                    print(f"  Time: {date_time}")
                    print(f"  Purpose: {purpose}")
                    print(f"{'='*50}")
                    return
                    
                except Exception as e:
                    print(f"  Error checking this article: {e}")
                    continue
            
            # If no suitable articles found
            print("\nNo recent articles found")
            self._save_generic_schedule(datetime.now())
            
        except Exception as e:
            print(f"✗ Error scraping Meloni's schedule: {e}")
            import traceback
            traceback.print_exc()
            self._save_generic_schedule(datetime.now())
    
    def _extract_purpose(self, title):
        """Extract purpose from article title"""
        # Remove "President Meloni's" prefix variations
        title = re.sub(r"^President Meloni'?s?\s*", '', title, flags=re.IGNORECASE)
        title = re.sub(r"^Prime Minister Meloni'?s?\s*", '', title, flags=re.IGNORECASE)
        
        # Clean up common patterns
        title = title.strip()
        
        # Make first letter lowercase for grammatical flow
        if title:
            title = title[0].lower() + title[1:]
        
        # Ensure it ends with a period
        if title and not title.endswith('.'):
            title += '.'
        
        return title
    
    def _extract_location(self, title, soup):
        """Extract location from title or article content"""
        title_lower = title.lower()
        
        # Check for country names in title
        countries = {
            'algeria': 'Algiers, Algeria',
            'france': 'Paris, France',
            'germany': 'Berlin, Germany',
            'united states': 'Washington, D.C., United States',
            'china': 'Beijing, China',
            'japan': 'Tokyo, Japan',
            'united kingdom': 'London, United Kingdom',
            'spain': 'Madrid, Spain',
            'poland': 'Warsaw, Poland',
            'libya': 'Tripoli, Libya',
            'tunisia': 'Tunis, Tunisia',
            'egypt': 'Cairo, Egypt',
            'turkey': 'Ankara, Turkey',
            'greece': 'Athens, Greece',
            'austria': 'Vienna, Austria',
            'switzerland': 'Bern, Switzerland',
            'belgium': 'Brussels, Belgium',
            'netherlands': 'Amsterdam, Netherlands',
        }
        
        for country, capital in countries.items():
            if country in title_lower:
                return capital
        
        # Check for Italian cities
        italian_cities = [
            'rome', 'roma', 'milan', 'milano', 'naples', 'napoli', 
            'turin', 'torino', 'florence', 'firenze', 'venice', 'venezia',
            'bologna', 'genoa', 'genova', 'palermo', 'bari'
        ]
        
        for city in italian_cities:
            if city in title_lower:
                return f"{city.title()}, Italy"
        
        # Look for "in [location]" pattern in title
        location_match = re.search(r'\bin\s+(?:the\s+)?([A-Z][a-zA-Z\s]+?)(?:\.|,|$)', title)
        if location_match:
            location = location_match.group(1).strip()
            # Check if it's a known place
            if len(location.split()) <= 3:  # Reasonable location name
                return location + ', Italy' if ',' not in location else location
        
        # Default to Rome
        return 'Rome, Italy'
    
    def _save_generic_schedule(self, now):
        """Save generic schedule when no events found"""
        purpose = "Prime Minister's official duties and meetings."
        location = "Rome, Italy"
        date_time = now.strftime("%B %d, %Y")
        
        self.db.add_or_update_figure(
            name="Prime Minister, Giorgia Meloni",
            location=location,
            date_time=date_time,
            purpose=purpose,
            category_type="country",
            category_id=self.country_id,
            source_url=self.news_url,
            display_order=1
        )
        
        print(f"\n{'='*50}")
        print(f"✓ Updated Giorgia Meloni (no specific events available):")
        print(f"  Location: {location}")
        print(f"  Time: {date_time}")
        print(f"  Purpose: {purpose}")
        print(f"{'='*50}")

def main():
    scraper = MeloniCalendarScraper()
    scraper.scrape()

if __name__ == "__main__":
    main()
