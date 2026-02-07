#
# france_president.py
# Created by V. Akyildiz on 21 January 2026.
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

class MacronCalendarScraper:
    def __init__(self):
        self.url = "https://www.elysee.fr/en/diary"
        self.db = Database()
        self.country_id = self.db.add_country("France")
        self.translator = GoogleTranslator(source='fr', target='en')
        
    def translate_french_to_english(self, text):
        """Translate French text to English"""
        try:
            if not text or len(text.strip()) < 3:
                return text
            
            # Check for "agenda being updated" message
            if "agenda" in text.lower() and "mise à jour" in text.lower():
                return "Agenda being updated"
            
            # Don't translate if already in English
            french_indicators = ['des', 'avec', 'pour', 'dans', 'sur', 'les', 'du', 'de la', 'au', 'à']
            has_french = any(f' {word} ' in f' {text.lower()} ' for word in french_indicators)
            
            if not has_french:
                return text
            
            translated = self.translator.translate(text)
            print(f"  Translated: '{text[:40]}...' → '{translated[:40]}...'")
            return translated
        except Exception as e:
            print(f"  Translation error: {e}")
            return text
    
    def scrape(self):
        """Scrape President Macron's schedule"""
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
            
            print("Fetching Macron's diary...")
            driver.get(self.url)
            time.sleep(3)
            
            # Scroll down to load more content
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Scroll back up
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Get main content
            main = soup.find('main')
            if not main:
                print("✗ Could not find main content")
                return
            
            main_text = main.get_text()
            
            # Find all date patterns - must match both 1-digit and 2-digit days
            date_patterns = re.findall(r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', main_text)
            
            if not date_patterns:
                print("✗ No dates found")
                return
            
            # Normalize to 2-digit format
            date_patterns = [(d, day.zfill(2), m) for d, day, m in date_patterns]
            
            # Remove duplicates while preserving order
            seen = set()
            unique_patterns = []
            for pattern in date_patterns:
                if pattern not in seen:
                    seen.add(pattern)
                    unique_patterns.append(pattern)
            date_patterns = unique_patterns
            
            print(f"✓ Found {len(date_patterns)} unique dates in calendar")
            print(f"All dates: {date_patterns}")
            print(f"Date range: {date_patterns[0]} to {date_patterns[-1]}")
            
            # Try dates from most recent backwards
            date_found = False
            latest_day_name, latest_day, latest_month = None, None, None
            section_text = None
            
            for day_name, day, month in reversed(date_patterns):
                print(f"Checking: {day_name} {day} {month}")
                # Find this date in the text
                date_pattern = rf"{day_name}\s+{day}\s+{month}"
                
                # Find all occurrences of this date
                for date_match in re.finditer(date_pattern, main_text):
                    date_pos = date_match.start()
                    
                    # Get next 1000 chars to check for content
                    context = main_text[date_pos:date_pos + 1000]
                    
                    # Check if this section has either:
                    # 1. Time patterns (events with times)
                    # 2. "All day long" (untimed events)
                    # 3. Event descriptions
                    has_time = bool(re.search(r'\d{1,2}h\d{2}', context))
                    has_allday = 'All day long' in context
                    has_event_text = bool(re.search(r'(Déplacement|Entretien|Conseil|Réunion|Cérémonie|Rencontre)', context))
                    
                    if has_time or has_allday or has_event_text:
                        # Find where this date section ends (next date or end)
                        next_date_pos = len(main_text)
                        for next_dn, next_dd, next_dm in date_patterns:
                            if (next_dn, next_dd, next_dm) != (day_name, day, month):
                                next_pattern = rf"{next_dn}\s+{next_dd}\s+{next_dm}"
                                next_match = re.search(next_pattern, main_text[date_pos + 10:])
                                if next_match:
                                    next_date_pos = date_pos + 10 + next_match.start()
                                    break
                        
                        section_text = main_text[date_pos:next_date_pos]
                        latest_day_name, latest_day, latest_month = day_name, day, month
                        date_found = True
                        print(f"✓ Found events for {day_name} {day} {month}")
                        break
                
                if date_found:
                    break
            
            if not date_found or not section_text:
                print("✗ No dates with events found")
                return
            
            print(f"✓ Extracted section ({len(section_text)} chars)")
            
            # Debug: show the section
            print(f"Section preview: {section_text[:200]}")
            
            # Parse events FIRST
            # Look for "All day long" events first
            allday_match = re.search(r'All day long\s+(.*?)(?:\n|$)', section_text)
            
            # Look for timed events
            time_matches = list(re.finditer(r'(\d{1,2}h\d{2})', section_text))
            
            event_time = None
            event_description = None
            
            if allday_match:
                event_time = "All day"
                # Get text after "All day long"
                context = section_text[allday_match.end():allday_match.end() + 300]
                lines = [l.strip() for l in context.split('\n') if l.strip()]
                event_description = lines[0] if lines else ""
                print(f"  Found all-day event: {event_description[:60]}...")
                
            elif time_matches:
                # Use first timed event
                first_match = time_matches[0]
                event_time = first_match.group(1)
                
                # Get text after time
                event_start = first_match.end()
                if len(time_matches) > 1:
                    event_end = time_matches[1].start()
                else:
                    event_end = event_start + 250
                
                event_text = section_text[event_start:event_end].strip()
                lines = [l.strip() for l in event_text.split('\n') if l.strip() and len(l.strip()) > 5]
                
                event_description = lines[0] if lines else ""
                print(f"  Found timed event at {event_time}: {event_description[:60]}...")
            
            # ONLY check for "agenda being updated" if NO events found
            if not event_description:
                agenda_update_pattern = r"L'agenda du Président est en cours de mise à jour"
                if re.search(agenda_update_pattern, section_text):
                    print("✓ Found 'agenda being updated' message with no events")
                
                # Format date
                month_map = {
                    'Jan': 'January', 'Feb': 'February', 'Mar': 'March', 
                    'Apr': 'April', 'May': 'May', 'Jun': 'June',
                    'Jul': 'July', 'Aug': 'August', 'Sep': 'September',
                    'Oct': 'October', 'Nov': 'November', 'Dec': 'December'
                }
                
                full_month = month_map.get(latest_month, latest_month)
                date_str = f"{full_month} {latest_day}, 2026"
                date_time = f"{date_str} - N/A"
                
                # Save to database
                self.db.add_or_update_figure(
                    name="President, Emmanuel Macron",
                    location="Paris, France",
                    date_time=date_time,
                    purpose="Agenda being updated.",
                    category_type="country",
                    category_id=self.country_id,
                    source_url=self.url
                )
                
                print(f"\n{'='*50}")
                print(f"✓ Updated Emmanuel Macron:")
                print(f"  Location: Paris, France")
                print(f"  Time: {date_time}")
                print(f"  Purpose: Agenda being updated.")
                print(f"{'='*50}")
                return
            
            # Parse events
            # Look for "All day long" events first
            allday_match = re.search(r'All day long\s+(.*?)(?:\n|$)', section_text)
            
            # Look for timed events
            time_matches = list(re.finditer(r'(\d{1,2}h\d{2})', section_text))
            
            event_time = None
            event_description = None
            
            if allday_match:
                event_time = "All day"
                # Get text after "All day long"
                context = section_text[allday_match.end():allday_match.end() + 300]
                lines = [l.strip() for l in context.split('\n') if l.strip()]
                event_description = lines[0] if lines else ""
                print(f"  Found all-day event: {event_description[:60]}...")
                
            elif time_matches:
                # Use first timed event
                first_match = time_matches[0]
                event_time = first_match.group(1)
                
                # Get text after time
                event_start = first_match.end()
                if len(time_matches) > 1:
                    event_end = time_matches[1].start()
                else:
                    event_end = event_start + 250
                
                event_text = section_text[event_start:event_end].strip()
                lines = [l.strip() for l in event_text.split('\n') if l.strip() and len(l.strip()) > 5]
                
                event_description = lines[0] if lines else ""
                print(f"  Found timed event at {event_time}: {event_description[:60]}...")
            
            if not event_description:
                print("✗ Could not parse event")
                return
            
            # Extract location
            location = self._extract_location(event_description)
            
            # Translate description
            purpose_translated = self.translate_french_to_english(event_description)
            
            purpose = purpose_translated
            if not purpose.endswith('.'):
                purpose += '.'
            if len(purpose) > 200:
                purpose = purpose[:197] + '...'
            
            # Format date/time
            month_map = {
                'Jan': 'January', 'Feb': 'February', 'Mar': 'March', 
                'Apr': 'April', 'May': 'May', 'Jun': 'June',
                'Jul': 'July', 'Aug': 'August', 'Sep': 'September',
                'Oct': 'October', 'Nov': 'November', 'Dec': 'December'
            }
            
            full_month = month_map.get(latest_month, latest_month)
            date_str = f"{full_month} {latest_day}, 2026"
            
            if event_time == "All day":
                date_time = f"{date_str} - All day"
            elif event_time:
                time_formatted = self._format_time(event_time)
                date_time = f"{date_str} - {time_formatted} (CET)"
            else:
                date_time = f"{date_str} - N/A"
            
            # Save to database
            self.db.add_or_update_figure(
                name="President, Emmanuel Macron",
                location=location,
                date_time=date_time,
                purpose=purpose,
                category_type="country",
                category_id=self.country_id,
                source_url=self.url
            )
            
            print(f"\n{'='*50}")
            print(f"✓ Updated Emmanuel Macron:")
            print(f"  Location: {location}")
            print(f"  Time: {date_time}")
            print(f"  Purpose: {purpose}")
            print(f"{'='*50}")
            
        except Exception as e:
            print(f"✗ Error scraping Macron's calendar: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            if driver:
                driver.quit()
    
    def _extract_location(self, description):
        """Extract location from description"""
        description_lower = description.lower()
        
        # Check for specific locations
        if 'davos' in description_lower:
            return 'Davos, Switzerland'
        elif 'palais de l' in description_lower or 'élysée' in description_lower:
            return 'Élysée Palace, Paris'
        elif 'versailles' in description_lower:
            return 'Versailles, France'
        
        # Check for French cities
        french_cities = {
            'paris': 'Paris, France',
            'lyon': 'Lyon, France',
            'marseille': 'Marseille, France',
            'nice': 'Nice, France',
            'toulouse': 'Toulouse, France',
            'bordeaux': 'Bordeaux, France',
            'strasbourg': 'Strasbourg, France',
            'lille': 'Lille, France',
            'nantes': 'Nantes, France'
        }
        
        for city, location in french_cities.items():
            if city in description_lower:
                return location
        
        return "Paris, France"
    
    def _format_time(self, french_time):
        """Convert French time (10h00) to standard (10:00 AM)"""
        try:
            match = re.match(r'(\d{1,2})h(\d{2})', french_time)
            if match:
                hour = int(match.group(1))
                minute = match.group(2)
                
                if hour == 0:
                    return f"12:{minute} AM"
                elif hour < 12:
                    return f"{hour}:{minute} AM"
                elif hour == 12:
                    return f"12:{minute} PM"
                else:
                    return f"{hour-12}:{minute} PM"
        except:
            pass
        
        return french_time

def main():
    scraper = MacronCalendarScraper()
    scraper.scrape()

if __name__ == "__main__":
    main()
