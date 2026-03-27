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
        self.base_url = "https://japan.kantei.go.jp"
        self.news_url = "https://japan.kantei.go.jp/news/index.html"
        self.db = Database()
        self.country_id = self.db.add_country("Japan")
        
    def scrape(self):
        """Scrape Prime Minister Takaichi's schedule"""
        try:
            print(f"Fetching Takaichi's news from {self.news_url}...")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            # Get the news list page
            response = requests.get(self.news_url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all links on the news page
            article_links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                # Look for article links (e.g., /105/statement/, /105/actions/)
                if '/105/' in href and ('.html' in href):
                    full_url = self.base_url + href if href.startswith('/') else href
                    if full_url not in article_links:
                        article_links.append(full_url)
            
            print(f"Found {len(article_links)} article links")
            
            if not article_links:
                print("No article links found, using generic schedule")
                self._save_generic_schedule(datetime.now())
                return
            
            # Open the FIRST (latest/most recent) link
            latest_url = article_links[0]
            print(f"\nOpening latest article: {latest_url}")
            
            article_response = requests.get(latest_url, headers=headers, timeout=10)
            article_response.raise_for_status()
            article_soup = BeautifulSoup(article_response.content, 'html.parser')
            
            # Extract title (purpose)
            title_elem = article_soup.find('h1')
            if not title_elem:
                title_elem = article_soup.find('title')
            
            if title_elem:
                purpose = title_elem.get_text().strip()
                # Remove "Prime Minister in Action" prefix
                purpose = re.sub(r'^Prime Minister in Action\s*[-:•]\s*', '', purpose, flags=re.IGNORECASE)
                purpose = purpose.strip()
            else:
                print("No title found, using generic schedule")
                self._save_generic_schedule(datetime.now())
                return
            
            # Extract location from content
            location = self._extract_location(article_soup)
            
            # Extract date from article or URL
            article_date = self._extract_date(article_soup, latest_url)
            
            # Save to database
            self.db.add_or_update_figure(
                name="Prime Minister, Sanae Takaichi",
                location=location,
                date_time=article_date,
                purpose=purpose,
                category_type="country",
                category_id=self.country_id,
                source_url=latest_url,
                display_order=1
            )
            
            print(f"\n{'='*50}")
            print(f"✓ Updated Sanae Takaichi:")
            print(f"  Location: {location}")
            print(f"  Time: {article_date}")
            print(f"  Purpose: {purpose}")
            print(f"{'='*50}")
            
        except requests.exceptions.HTTPError as e:
            print(f"✗ Website returned error ({e.response.status_code}), using generic schedule")
            self._save_generic_schedule(datetime.now())
        except Exception as e:
            print(f"✗ Error scraping Takaichi's schedule: {e}")
            import traceback
            traceback.print_exc()
            self._save_generic_schedule(datetime.now())
    
    def _extract_location(self, soup):
        """Extract location from article content"""
        # Get all text from the page
        page_text = soup.get_text()
        
        # Look for specific locations
        if 'Washington, D.C.' in page_text or 'Washington D.C.' in page_text:
            return 'Washington, D.C., United States'
        elif "Prime Minister's Office" in page_text or "Prime Minister's Residence" in page_text:
            return "Prime Minister's Office, Tokyo, Japan"
        elif 'New York' in page_text:
            return 'New York, United States'
        elif 'Paris' in page_text:
            return 'Paris, France'
        elif 'London' in page_text:
            return 'London, United Kingdom'
        elif 'Beijing' in page_text:
            return 'Beijing, China'
        elif 'Seoul' in page_text:
            return 'Seoul, South Korea'
        elif 'Brussels' in page_text:
            return 'Brussels, Belgium'
        
        # Default to Tokyo
        return 'Tokyo, Japan'
    
    def _extract_date(self, soup, url):
        """Extract date from article or URL"""
        now = datetime.now()
        
        # Try to find date in URL (e.g., /202603/27message.html)
        date_match = re.search(r'/(\d{4})(\d{2})/(\d{2})', url)
        if date_match:
            year = int(date_match.group(1))
            month = int(date_match.group(2))
            day = int(date_match.group(3))
            
            article_date = datetime(year, month, day)
            
            # Check if it's today
            if article_date.date() == now.date():
                return now.strftime("%B %d, %Y")
            else:
                return article_date.strftime("%B %d, %Y")
        
        # If no date found in URL, use today
        return now.strftime("%B %d, %Y")
    
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
            source_url=self.news_url,
            display_order=1
        )
        
        print(f"\n{'='*50}")
        print(f"✓ Updated Sanae Takaichi (no specific events available):")
        print(f"  Location: {location}")
        print(f"  Time: {date_time}")
        print(f"  Purpose: {purpose}")
        print(f"{'='*50}")

def main():
    scraper = TakaichiCalendarScraper()
    scraper.scrape()

if __name__ == "__main__":
    main()
