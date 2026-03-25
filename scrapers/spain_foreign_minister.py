#
# spain_foreign_minister.py
# Scraper for Spanish Minister for Foreign Affairs
# Created by V. Akyildiz on 7 February 2026.
# Copyright © 2026 FigureWatch. All rights reserved.
#

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
from datetime import datetime
import re
import time
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import Database

class AlbaresCalendarScraper:
    def __init__(self):
        self.url = "https://www.exteriores.gob.es/en/Ministerio/Ministro/Paginas/AgendaMinistro.aspx"
        self.db = Database()
        self.country_id = self.db.add_country("Spain")
        self.translator = GoogleTranslator(source='es', target='en')
        
    def translate_spanish_to_english(self, text):
        """Translate Spanish text to English"""
        try:
            if not text or len(text.strip()) < 3:
                return text
            
            # Skip if already in English
            if text.lower().startswith(('meeting', 'visit', 'conference', 'reception')):
                return text
            
            translated = self.translator.translate(text)
            print(f"  Translated: '{text[:40]}...' → '{translated[:40]}...'")
            return translated
        except Exception as e:
            print(f"  Translation error: {e}")
            return text
    
    def scrape(self):
        """Scrape Minister Albares' schedule"""
        driver = None
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
            
            print("Starting Chrome browser...")
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=chrome_options
            )
            
            print("Fetching Albares' agenda...")
            driver.get(self.url)
            time.sleep(5)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Get today's date for comparison
            now = datetime.now()
            today = now.date()
            
            # Look for agenda items
            # The page might use various structures - let's try multiple approaches
            
            # Strategy 1: Look for date patterns in English
            date_pattern = r'(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})'
            page_text = soup.get_text()
            dates_found = re.findall(date_pattern, page_text, re.IGNORECASE)
            
            if dates_found:
                print(f"✓ Found {len(dates_found)} date(s) in English format")
                most_recent = dates_found[-1]  # Last date is usually most recent
                day, month_name, year = most_recent
                
                # Parse the date
                month_map = {
                    'january': 1, 'february': 2, 'march': 3, 'april': 4,
                    'may': 5, 'june': 6, 'july': 7, 'august': 8,
                    'september': 9, 'october': 10, 'november': 11, 'december': 12
                }
                month_num = month_map.get(month_name.lower(), 1)
                
                # Try to find event description near this date
                # Look for common event indicators
                event_text = self._extract_event_near_date(soup, day, month_name)
                
                if event_text:
                    purpose = event_text
                else:
                    purpose = "Ministerial duties and diplomatic engagements."
                
                # Extract location
                location = self._extract_location(page_text)
                
                # Format date
                date_time = f"{month_name} {day}, {year}"
                
            else:
                # Fallback: Use generic recent activity
                print("ℹ No specific dates found, using generic schedule")
                purpose = "Ongoing ministerial duties and diplomatic meetings."
                location = "Madrid, Spain"
                date_time = f"{now.strftime('%B')} {now.day}, {now.year}"
            
            # Translate if in Spanish
            if self._is_spanish(purpose):
                purpose = self.translate_spanish_to_english(purpose)
            
            # Format purpose
            if not purpose.endswith('.'):
                purpose += '.'
            if len(purpose) > 200:
                purpose = purpose[:197] + '...'
            
            # Save to database
            self.db.add_or_update_figure(
                name="Minister for Foreign Affairs, José Manuel Albares Bueno",
                location=location,
                date_time=date_time,
                purpose=purpose,
                category_type="country",
                category_id=self.country_id,
                source_url=self.url
            )
            
            print(f"\n{'='*50}")
            print(f"✓ Updated José Manuel Albares:")
            print(f"  Location: {location}")
            print(f"  Time: {date_time}")
            print(f"  Purpose: {purpose}")
            print(f"{'='*50}")
            
        except Exception as e:
            print(f"✗ Error scraping Albares' calendar: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            if driver:
                driver.quit()
    
    def _extract_event_near_date(self, soup, day, month):
        """Try to extract event description near a specific date"""
        # Look for paragraphs or divs containing event information
        for element in soup.find_all(['p', 'div', 'li', 'td']):
            text = element.get_text(strip=True)
            if day in text and month.lower() in text.lower():
                # Found a section with this date
                # Try to get the event description
                if len(text) > 30:  # Substantial text
                    # Clean up the text
                    text = re.sub(r'\s+', ' ', text)
                    return text[:200]
        
        return None
    
    def _extract_location(self, text):
        """Extract location from text"""
        text_lower = text.lower()
        
        # Check for Spanish cities
        locations = {
            'madrid': 'Madrid, Spain',
            'barcelona': 'Barcelona, Spain',
            'valencia': 'Valencia, Spain',
            'sevilla': 'Seville, Spain',
            'seville': 'Seville, Spain',
            'bilbao': 'Bilbao, Spain',
            'brussels': 'Brussels, Belgium',
            'bruselas': 'Brussels, Belgium',
            'paris': 'Paris, France',
            'parís': 'Paris, France',
            'berlin': 'Berlin, Germany',
            'berlín': 'Berlin, Germany',
            'rome': 'Rome, Italy',
            'roma': 'Rome, Italy',
            'lisbon': 'Lisbon, Portugal',
            'lisboa': 'Lisbon, Portugal',
            'london': 'London, United Kingdom',
            'londres': 'London, United Kingdom',
            'washington': 'Washington, D.C., United States',
            'new york': 'New York City, United States',
            'nueva york': 'New York City, United States',
        }
        
        for keyword, location in locations.items():
            if keyword in text_lower:
                return location
        
        return "Madrid, Spain"
    
    def _is_spanish(self, text):
        """Check if text is in Spanish"""
        spanish_indicators = [
            'reunión', 'visita', 'encuentro', 'conferencia',
            'ministro', 'embajador', 'presidente', 'gobierno'
        ]
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in spanish_indicators)

def main():
    scraper = AlbaresCalendarScraper()
    scraper.scrape()

if __name__ == "__main__":
    main()
