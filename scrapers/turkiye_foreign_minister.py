#
# turkiye_foreign_minister.py
# Created by V. Akyildiz on 31 January 2026.
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

class FidanCalendarScraper:
    def __init__(self):
        self.url = "https://www.mfa.gov.tr/sub.tr.mfa?978045a8-225a-487d-8fd8-8d371874e8ec"
        self.db = Database()
        self.country_id = self.db.add_country("Türkiye")
        self.translator = GoogleTranslator(source='tr', target='en')
        
    def translate_turkish_to_english(self, text):
        """Translate Turkish text to English"""
        try:
            if not text or len(text.strip()) < 3:
                return text
            
            translated = self.translator.translate(text)
            return translated
        except Exception as e:
            print(f"  Translation error: {e}")
            return text
    
    def scrape(self):
        """Scrape Foreign Minister Fidan's schedule"""
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
            
            print("Fetching Foreign Minister Fidan's press releases...")
            driver.get(self.url)
            time.sleep(5)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Find all press release links in sub_lstitm divs
            press_divs = soup.find_all('div', class_='sub_lstitm')
            
            if not press_divs:
                print("✗ No press releases found")
                return
            
            print(f"✓ Found {len(press_divs)} press releases")
            
            # Turkish month names
            turkish_months = {
                'ocak': 'January', 'şubat': 'February', 'mart': 'March',
                'nisan': 'April', 'mayıs': 'May', 'haziran': 'June',
                'temmuz': 'July', 'ağustos': 'August', 'eylül': 'September',
                'ekim': 'October', 'kasım': 'November', 'aralık': 'December'
            }
            
            # Get the MOST RECENT (first) press release
            first_div = press_divs[0]
            link = first_div.find('a')
            
            if not link:
                print("✗ No link found in first press release")
                return
            
            title_tr = link.get_text(strip=True)
            print(f"\nMost recent press release:")
            print(f"  {title_tr}")
            
            # Extract date from title using Turkish month pattern
            # Pattern: "DD Month YYYY"
            month_pattern = '|'.join(turkish_months.keys())
            date_pattern = rf'(\d{{1,2}})\s+({month_pattern})\s+(\d{{4}})'
            date_match = re.search(date_pattern, title_tr, re.IGNORECASE)
            
            if not date_match:
                print("✗ Could not extract date from title")
                return
            
            day, month_tr, year = date_match.groups()
            month_tr = month_tr.lower()
            month_en = turkish_months.get(month_tr, month_tr.capitalize())
            
            # Format date in English
            date_time = f"{month_en} {day}, {year}"
            
            print(f"  Date extracted: {date_time}")
            
            # Extract location (usually after the date, at the end)
            # Split by the date and take what comes after
            parts = re.split(date_pattern, title_tr, flags=re.IGNORECASE)
            
            location = "Ankara, Türkiye"  # Default
            
            if len(parts) > 4:
                # parts[4] contains text after the date
                location_text = parts[4].strip()
                # Remove leading comma
                location_text = location_text.lstrip(',').strip()
                
                if location_text:
                    # Translate location
                    location_en = self.translate_turkish_to_english(location_text)
                    
                    # Clean up common location names
                    if 'ankara' in location_text.lower():
                        location = "Ankara, Türkiye"
                    elif 'istanbul' in location_text.lower():
                        location = "Istanbul, Türkiye"
                    elif location_en and len(location_en) > 0:
                        # Use translated location with Türkiye appended if not already there
                        if 'türkiye' not in location_en.lower() and 'turkey' not in location_en.lower():
                            location = f"{location_en}, Türkiye"
                        else:
                            location = location_en
            
            print(f"  Location extracted: {location}")
            
            # Extract purpose (everything before the date)
            purpose_match = re.search(rf'^(.+?),?\s*{date_pattern}', title_tr, re.IGNORECASE)
            
            if purpose_match:
                purpose_tr = purpose_match.group(1).strip()
                # Remove "Sayın Bakanımızın" prefix (Our Minister's)
                purpose_tr = re.sub(r'^Sayın Bakanımızın\s+', '', purpose_tr, flags=re.IGNORECASE)
                
                # Translate purpose
                purpose_en = self.translate_turkish_to_english(purpose_tr)
                purpose = purpose_en
                
                print(f"  Purpose extracted: {purpose[:80]}...")
            else:
                # Fallback: translate entire title
                purpose = self.translate_turkish_to_english(title_tr)
            
            # Ensure purpose is not too long
            if len(purpose) > 200:
                purpose = purpose[:197] + "..."
            
            # Save to database
            self.db.add_or_update_figure(
                name="Minister of Foreign Affairs, Hakan Fidan",
                location=location,
                date_time=date_time,
                purpose=purpose,
                category_type="country",
                category_id=self.country_id,
                source_url=self.url,
                display_order=2
            )
            
            print(f"\n{'='*50}")
            print(f"✓ Updated Hakan Fidan:")
            print(f"  Location: {location}")
            print(f"  Time: {date_time}")
            print(f"  Purpose: {purpose}")
            print(f"{'='*50}")
            
        except Exception as e:
            print(f"✗ Error scraping Fidan's calendar: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            if driver:
                driver.quit()

def main():
    scraper = FidanCalendarScraper()
    scraper.scrape()

if __name__ == "__main__":
    main()
