#
# turkiye_president.py
# Scraper for Turkish President Recep Tayyip Erdoğan
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
from deep_translator import GoogleTranslator
import re
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import Database

class ErdoganCalendarScraper:
    def __init__(self):
        self.base_url = "https://www.akparti.org.tr"
        self.news_url = "https://www.akparti.org.tr/haberler/genel-baskan"
        self.db = Database()
        self.country_id = self.db.add_country("Türkiye")
        
    def scrape(self):
        """Scrape President Erdoğan's schedule"""
        driver = None
        try:
            print(f"Fetching Erdoğan's news from {self.news_url}...")
            
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
            driver.set_page_load_timeout(120)
            driver.get(self.news_url)
            
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Find the first (most recent) news link
            news_links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                if '/haberler/cumhurbaskanimiz' in href.lower():
                    full_url = self.base_url + href if href.startswith('/') else href
                    if full_url not in news_links:
                        news_links.append(full_url)
            
            print(f"Found {len(news_links)} news articles")
            
            if not news_links:
                print("No news articles found")
                self._save_generic_schedule(datetime.now())
                return
            
            # Load the most recent article
            article_url = news_links[0]
            print(f"Loading article: {article_url}")
            
            driver.get(article_url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            article_soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Extract date from URL (format: 27-03-2026)
            date_match = re.search(r'(\d{2})-(\d{2})-(\d{4})', article_url)
            if date_match:
                day = int(date_match.group(1))
                month = int(date_match.group(2))
                year = int(date_match.group(3))
                event_date = datetime(year, month, day)
                date_str = event_date.strftime("%d %B %Y")
            else:
                date_str = datetime.now().strftime("%d %B %Y")
            
            # Extract article content (first few paragraphs)
            article_text = ""
            for p in article_soup.find_all('p'):
                article_text += p.get_text() + " "
                if len(article_text) > 500:  # Get first ~500 chars
                    break
            
            # Extract location and purpose
            location = self._extract_location(article_text)
            purpose = self._extract_purpose(article_text, article_soup)
            
            # Translate purpose to English
            try:
                purpose_en = GoogleTranslator(source='tr', target='en').translate(purpose)
            except:
                purpose_en = purpose
            
            # Save to database
            self.db.add_or_update_figure(
                name="President, Recep Tayyip Erdoğan",
                location=location,
                date_time=date_str,
                purpose=purpose_en,
                category_type="country",
                category_id=self.country_id,
                source_url=article_url,
                display_order=1
            )
            
            print(f"\n{'='*50}")
            print(f"✓ Updated Recep Tayyip Erdoğan:")
            print(f"  Location: {location}")
            print(f"  Time: {date_str}")
            print(f"  Purpose: {purpose_en}")
            print(f"{'='*50}")
            
        except Exception as e:
            print(f"✗ Error scraping Erdoğan's schedule: {e}")
            import traceback
            traceback.print_exc()
            self._save_generic_schedule(datetime.now())
        finally:
            if driver:
                driver.quit()
    
    def _extract_location(self, text):
        """Extract location from Turkish text"""
        text_lower = text.lower()
        
        # Look for specific office locations
        if 'dolmabahçe' in text_lower or 'dolmabahce' in text_lower:
            return 'Presidential Dolmabahçe Office, Istanbul'
        elif 'beştepe' in text_lower or 'bestepe' in text_lower or 'külliye' in text_lower or 'kulliye' in text_lower:
            return 'Presidential Complex, Ankara'
        
        # Look for city names with Turkish locative suffix patterns
        # Turkish: "İstanbul'da", "Ankara'da", "Brüksel'de" etc.
        city_patterns = [
            (r"istanbul['\']?d[ae]", 'Istanbul, Türkiye'),
            (r"ankara['\']?d[ae]", 'Ankara, Türkiye'),
            (r"izmir['\']?d[ae]", 'Izmir, Türkiye'),
            (r"brüksel['\']?d[ae]|brussels?['\']?d[ae]", 'Brussels, Belgium'),
            (r"paris['\']?t[ae]", 'Paris, France'),
            (r"washington['\']?d[ae]", 'Washington, D.C., United States'),
            (r"moskova['\']?d[ae]|moscow['\']?d[ae]", 'Moscow, Russia'),
        ]
        
        for pattern, location in city_patterns:
            if re.search(pattern, text_lower):
                return location
        
        # Check simple mentions
        if 'istanbul' in text_lower:
            return 'Istanbul, Türkiye'
        elif 'ankara' in text_lower:
            return 'Ankara, Türkiye'
        
        # Default
        return 'Ankara, Türkiye'
    
    def _extract_purpose(self, text, soup):
        """Extract purpose from article text"""
        # Try to get the article title/headline first
        title = soup.find('h1')
        if title:
            title_text = title.get_text().strip()
            # Remove "Cumhurbaşkanımız Erdoğan" prefix if present
            title_text = re.sub(r'^Cumhurbaşkanımız\s+Erdoğan[,:\s]*', '', title_text, flags=re.IGNORECASE)
            if len(title_text) > 20:
                return title_text
        
        # Fallback: extract first sentence from article text
        sentences = text.split('.')
        if sentences:
            first_sentence = sentences[0].strip()
            # Remove "Cumhurbaşkanımız Erdoğan" prefix
            first_sentence = re.sub(r'^Cumhurbaşkanımız\s+Recep\s+Tayyip\s+Erdoğan[,:\s]*', '', first_sentence, flags=re.IGNORECASE)
            first_sentence = re.sub(r'^Cumhurbaşkanımız\s+Erdoğan[,:\s]*', '', first_sentence, flags=re.IGNORECASE)
            return first_sentence
        
        return "Official duties and meetings"
    
    def _save_generic_schedule(self, now):
        """Save generic schedule when no events found"""
        purpose = "President's official duties and meetings."
        location = "Ankara, Türkiye"
        date_time = now.strftime("%d %B %Y")
        
        self.db.add_or_update_figure(
            name="President, Recep Tayyip Erdoğan",
            location=location,
            date_time=date_time,
            purpose=purpose,
            category_type="country",
            category_id=self.country_id,
            source_url=self.news_url,
            display_order=1
        )
        
        print(f"\n{'='*50}")
        print(f"✓ Updated Recep Tayyip Erdoğan (no specific events available):")
        print(f"  Location: {location}")
        print(f"  Time: {date_time}")
        print(f"  Purpose: {purpose}")
        print(f"{'='*50}")

def main():
    scraper = ErdoganCalendarScraper()
    scraper.scrape()

if __name__ == "__main__":
    main()
