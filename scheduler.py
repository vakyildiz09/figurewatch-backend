from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import time
import sys
import os

# Import scrapers
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from scrapers.us_president import TrumpCalendarScraper
from scrapers.us_secretary_of_state import RubioCalendarScraper
from scrapers.nato_secretary_general import RutteCalendarScraper
from scrapers.france_president import MacronCalendarScraper
from scrapers.germany_chancellor import MerzCalendarScraper
from scrapers.italy_prime_minister import MeloniCalendarScraper
from scrapers.turkiye_president import ErdoganCalendarScraper
from scrapers.turkiye_foreign_minister import FidanCalendarScraper
from scrapers.france_foreign_minister import BarrotCalendarScraper
from scrapers.eu_council_president import CostaCalendarScraper
from scrapers.spain_prime_minister import SanchezCalendarScraper

def run_all_scrapers():
    """Run all configured scrapers"""
    print(f"\n{'='*50}")
    print(f"Running scrapers at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}\n")
    
    # Run Trump scraper
    print("--- Scraping President Trump ---")
    try:
        trump_scraper = TrumpCalendarScraper()
        trump_scraper.scrape()
    except Exception as e:
        print(f"Error running Trump scraper: {e}")
    
    # Run Rubio scraper
    print("\n--- Scraping Secretary Rubio ---")
    try:
        rubio_scraper = RubioCalendarScraper()
        rubio_scraper.scrape()
    except Exception as e:
        print(f"Error running Rubio scraper: {e}")
    
    # Run Rutte scraper
    print("\n--- Scraping NATO Secretary General ---")
    try:
        rutte_scraper = RutteCalendarScraper()
        rutte_scraper.scrape()
    except Exception as e:
        print(f"Error running NATO scraper: {e}")
    
    # Run Macron scraper
    print("\n--- Scraping President Macron ---")
    try:
        macron_scraper = MacronCalendarScraper()
        macron_scraper.scrape()
    except Exception as e:
        print(f"Error running Macron scraper: {e}")
    
    # Run Merz scraper
    print("\n--- Scraping Chancellor Merz ---")
    try:
        merz_scraper = MerzCalendarScraper()
        merz_scraper.scrape()
    except Exception as e:
        print(f"Error running Merz scraper: {e}")
    
    # Run Meloni scraper
    print("\n--- Scraping Prime Minister Meloni ---")
    try:
        meloni_scraper = MeloniCalendarScraper()
        meloni_scraper.scrape()
    except Exception as e:
        print(f"Error running Meloni scraper: {e}")
    
    # Run Erdoğan scraper
    print("\n--- Scraping President Erdoğan ---")
    try:
        erdogan_scraper = ErdoganCalendarScraper()
        erdogan_scraper.scrape()
    except Exception as e:
        print(f"Error running Erdoğan scraper: {e}")
    
    # Run Fidan scraper
    print("\n--- Scraping Foreign Minister Fidan ---")
    try:
        fidan_scraper = FidanCalendarScraper()
        fidan_scraper.scrape()
    except Exception as e:
        print(f"Error running Fidan scraper: {e}")
    
    # Run Barrot scraper
    print("\n--- Scraping Foreign Minister Barrot ---")
    try:
        barrot_scraper = BarrotCalendarScraper()
        barrot_scraper.scrape()
    except Exception as e:
        print(f"Error running Barrot scraper: {e}")
    
    # Run Costa scraper
    print("\n--- Scraping EU Council President Costa ---")
    try:
        costa_scraper = CostaCalendarScraper()
        costa_scraper.scrape()
    except Exception as e:
        print(f"Error running Costa scraper: {e}")
    
    # Run Sánchez scraper
    print("\n--- Scraping Spanish PM Sánchez ---")
    try:
        sanchez_scraper = SanchezCalendarScraper()
        sanchez_scraper.scrape()
    except Exception as e:
        print(f"Error running Sánchez scraper: {e}")
    
    print(f"\n{'='*50}")
    print("Scraper run complete")
    print(f"{'='*50}\n")

def start_scheduler():
    """Start the background scheduler"""
    scheduler = BackgroundScheduler()
    
    # Run scrapers every 30 minutes
    scheduler.add_job(
        func=run_all_scrapers,
        trigger=IntervalTrigger(minutes=30),
        id='scraper_job',
        name='Run all scrapers every 30 minutes',
        replace_existing=True
    )
    
    scheduler.start()
    print("✓ Scheduler started!")
    print("✓ Scrapers will run every 30 minutes")
    print("✓ Press Ctrl+C to stop\n")
    
    # Run once immediately on startup
    run_all_scrapers()
    
    return scheduler

if __name__ == "__main__":
    scheduler = start_scheduler()
    
    try:
        # Keep the script running
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        print("\nShutting down scheduler...")
        scheduler.shutdown()
        print("Scheduler stopped.")
