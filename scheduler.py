from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import time
import sys
import os

# Import scrapers - only the ones that work reliably
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from scrapers.us_president import TrumpCalendarScraper
from scrapers.germany_chancellor import MerzCalendarScraper
from scrapers.italy_prime_minister import MeloniCalendarScraper
from scrapers.turkiye_foreign_minister import FidanCalendarScraper
from scrapers.canada_prime_minister import CarneyCalendarScraper

# Try importing Google Sheets scraper with detailed error handling
try:
    print("DEBUG: Attempting to import GoogleSheetsScraper...")
    from scrapers.google_sheets_scraper import GoogleSheetsScraper
    print("DEBUG: GoogleSheetsScraper import successful!")
    GOOGLE_SHEETS_AVAILABLE = True
except Exception as e:
    print(f"WARNING: Could not import Google Sheets scraper: {e}")
    import traceback
    traceback.print_exc()
    GOOGLE_SHEETS_AVAILABLE = False

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
    
    # Run Fidan scraper
    print("\n--- Scraping Foreign Minister Fidan ---")
    try:
        fidan_scraper = FidanCalendarScraper()
        fidan_scraper.scrape()
    except Exception as e:
        print(f"Error running Fidan scraper: {e}")
    
    # Run Carney scraper
    print("\n--- Scraping Canadian PM Carney ---")
    try:
        carney_scraper = CarneyCalendarScraper()
        carney_scraper.scrape()
    except Exception as e:
        print(f"Error running Carney scraper: {e}")
    
    # ALL MANUAL ENTRIES (Tricky Four + Problematic Five):
    # - Rubio, Erdogan, Sanchez, Takaichi (tricky four)
    # - NATO Rutte, Costa, Macron, Albares, Barrot (problematic five)
    # All handled by Google Sheets only
    
    # Run Google Sheets scraper for manual entries (runs LAST to ensure fresh data)
    if GOOGLE_SHEETS_AVAILABLE:
        print("\n--- Reading Manual Entries from Google Sheets ---")
        try:
            print("DEBUG: Creating GoogleSheetsScraper instance...")
            sheets_scraper = GoogleSheetsScraper()
            print("DEBUG: Running Google Sheets scraper...")
            sheets_scraper.scrape()
            print("DEBUG: Google Sheets scraper completed")
        except Exception as e:
            print(f"Error running Google Sheets scraper: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\n--- Skipping Google Sheets (import failed) ---")
    
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
