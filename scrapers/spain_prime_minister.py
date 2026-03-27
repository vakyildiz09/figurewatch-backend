#
# spain_prime_minister.py
# Scraper for Spanish Prime Minister Pedro Sánchez
# Created by V. Akyildiz on 31 January 2026.
# Copyright © 2026 FigureWatch. All rights reserved.
#

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from datetime import datetime
import re
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import Database

class SanchezCalendarScraper:
    def __init__(self):
        self.base_url = "https://www.lamoncloa.gob.es"
        self.agenda_url = "https://www.lamoncloa.gob.es/presidente/agenda/Paginas/index.aspx"
        self.db = Database()
        self.country_id = self.db.add_country("Spain")
        
    def scrape(self):
        """Scrape Prime Minister Sánchez's schedule"""
        driver = None
        try:
            print(f"Fetching Sánchez's agenda list from {self.agenda_url}...")
            
            chrome_options = Options()
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-software-rasterizer')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36')
            
            service = Service('/usr/local/bin/chromedriver')
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.set_page_load_timeout(120)  # 2 minutes timeout
            driver.get(self.agenda_url)
            
            # Wait for content to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Get page source after JavaScript execution
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Find all agenda links
            agenda_links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                # Look for agenda.aspx links with date parameter
                if 'agenda.aspx' in href and 'd=' in href:
                    full_url = self.base_url + href if href.startswith('/') else href
                    if full_url not in agenda_links:
                        agenda_links.append(full_url)
            
            print(f"Found {len(agenda_links)} agenda links")
            
            if not agenda_links:
                print("No agenda links found, using generic schedule")
                self._save_generic_schedule(datetime.now())
                return
            
            # Go through agendas one by one, most recent first
            for i, agenda_url in enumerate(agenda_links[:10], 1):  # Check up to 10 most recent
                print(f"\nChecking agenda {i}: {agenda_url}")
                
                try:
                    driver.get(agenda_url)
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    
                    agenda_soup = BeautifulSoup(driver.page_source, 'html.parser')
                    
                    # Extract events from this agenda
                    events = self._extract_events(agenda_soup, datetime.now())
                    
                    if events:
                        # Find the most recent completed event
                        completed_events = [e for e in events if e['completed']]
                        
                        if completed_events:
                            # Use the most recent completed event
                            latest = completed_events[-1]
                            
                            self.db.add_or_update_figure(
                                name="Prime Minister, Pedro Sánchez",
                                location=latest['location'],
                                date_time=latest['time_display'],
                                purpose=latest['purpose'],
                                category_type="country",
                                category_id=self.country_id,
                                source_url=agenda_url,
                                display_order=1
                            )
                            
                            print(f"\n{'='*50}")
                            print(f"✓ Updated Pedro Sánchez:")
                            print(f"  Location: {latest['location']}")
                            print(f"  Time: {latest['time_display']}")
                            print(f"  Purpose: {latest['purpose']}")
                            print(f"{'='*50}")
                            return
                        else:
                            print(f"  Agenda has {len(events)} event(s) but none completed yet")
                            # Continue to next agenda
                    else:
                        print("  No events found in this agenda")
                        
                except Exception as e:
                    print(f"  Error checking this agenda: {e}")
                    continue
            
            # If we've checked all agendas and found nothing
            print("\nNo completed events found in recent agendas")
            self._save_generic_schedule(datetime.now())
            
        except Exception as e:
            print(f"✗ Error scraping Sánchez's schedule: {e}")
            import traceback
            traceback.print_exc()
            self._save_generic_schedule(datetime.now())
        finally:
            if driver:
                driver.quit()
    
    def _extract_events(self, soup, now):
        """Extract events from an agenda page"""
        events = []
        
        # Look for time patterns like "10:00h" or "12:30h"
        time_pattern = r'(\d{1,2}):(\d{2})h'
        
        for paragraph in soup.find_all(['p', 'li', 'div']):
            text = paragraph.get_text()
            
            time_match = re.search(time_pattern, text)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2))
                
                # Extract purpose (text after the time)
                purpose = text[time_match.end():].strip()
                purpose = re.sub(r'^[-–—:.\s]+', '', purpose)  # Remove leading dashes/colons/dots
                
                if purpose and len(purpose) > 10:  # Valid purpose
                    # Determine if event is completed
                    event_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    completed = event_time < now
                    
                    # Extract location
                    location = self._extract_location(text)
                    
                    time_display = f"{now.strftime('%B %d, %Y')} - {time_match.group(0).upper()}"
                    
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
        
        # Common Spanish locations
        if 'madrid' in text_lower or 'moncloa' in text_lower:
            return 'Madrid, Spain'
        elif 'barcelona' in text_lower:
            return 'Barcelona, Spain'
        elif 'valencia' in text_lower:
            return 'Valencia, Spain'
        elif 'sevilla' in text_lower or 'seville' in text_lower:
            return 'Seville, Spain'
        elif 'bruselas' in text_lower or 'brussels' in text_lower:
            return 'Brussels, Belgium'
        elif 'paris' in text_lower or 'parís' in text_lower:
            return 'Paris, France'
        
        # Default to Madrid
        return 'Madrid, Spain'
    
    def _save_generic_schedule(self, now):
        """Save generic schedule when no events found"""
        purpose = "Prime Minister's official duties and meetings."
        location = "Madrid, Spain"
        date_time = now.strftime("%B %d, %Y")
        
        self.db.add_or_update_figure(
            name="Prime Minister, Pedro Sánchez",
            location=location,
            date_time=date_time,
            purpose=purpose,
            category_type="country",
            category_id=self.country_id,
            source_url=self.agenda_url,
            display_order=1
        )
        
        print(f"\n{'='*50}")
        print(f"✓ Updated Pedro Sánchez (no specific events today):")
        print(f"  Location: {location}")
        print(f"  Time: {date_time}")
        print(f"  Purpose: {purpose}")
        print(f"{'='*50}")

def main():
    scraper = SanchezCalendarScraper()
    scraper.scrape()

if __name__ == "__main__":
    main()
