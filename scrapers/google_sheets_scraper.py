#
# google_sheets_scraper.py
# Scraper that reads manual entries from Google Sheets
# Created by V. Akyildiz on 28 March 2026.
# Copyright © 2026 FigureWatch. All rights reserved.
#

import os
import json
import re
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import Database

class GoogleSheetsScraper:
    def __init__(self):
        self.db = Database()
        self.sheet_id = '1dyFnXMZtaGICRnbeuWS77wlYvu_ClrOpMybye8B1RS4'
        self.range_name = 'Sheet1!A:E'  # Read columns A through E
        
    def scrape(self):
        """Read manual entries from Google Sheets"""
        try:
            print(f"Fetching manual entries from Google Sheets...")
            
            # Get credentials from environment variable
            creds_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
            if not creds_json:
                print("✗ No Google Sheets credentials found")
                return
            
            # Parse credentials
            creds_dict = json.loads(creds_json)
            credentials = Credentials.from_service_account_info(
                creds_dict,
                scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
            )
            
            # Build service
            service = build('sheets', 'v4', credentials=credentials)
            sheet = service.spreadsheets()
            
            # Read data
            result = sheet.values().get(
                spreadsheetId=self.sheet_id,
                range=self.range_name
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                print("No data found in sheet")
                return
            
            # Skip header row
            headers = values[0]
            rows = values[1:]
            
            print(f"Found {len(rows)} manual entries")
            
            # Process each figure's entries
            self._process_entries(rows)
            
        except Exception as e:
            print(f"✗ Error reading Google Sheets: {e}")
            import traceback
            traceback.print_exc()
    
    def _process_entries(self, rows):
        """Process entries for each figure"""
        
        # Group entries by figure name
        entries_by_figure = {}
        
        for row in rows:
            if len(row) < 5:
                continue  # Skip incomplete rows
            
            figure_name = row[0].strip()
            date_str = row[1].strip()
            time_str = row[2].strip()
            location = row[3].strip()
            purpose = row[4].strip()
            
            if not figure_name or not date_str:
                continue  # Skip rows without name or date
            
            if figure_name not in entries_by_figure:
                entries_by_figure[figure_name] = []
            
            entries_by_figure[figure_name].append({
                'date_str': date_str,
                'time_str': time_str,
                'location': location,
                'purpose': purpose
            })
        
        # Process each figure
        for figure_name, entries in entries_by_figure.items():
            self._update_figure(figure_name, entries)
    
    def _update_figure(self, figure_name, entries):
        """Update a specific figure with their most recent completed event"""
        
        try:
            # Parse and sort entries by date/time
            parsed_entries = []
            
            for entry in entries:
                try:
                    # Parse date (format: YYYY-MM-DD or DD/MM/YYYY or similar)
                    date_str = entry['date_str']
                    
                    # Try different date formats
                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y']:
                        try:
                            event_date = datetime.strptime(date_str, fmt)
                            break
                        except:
                            continue
                    else:
                        print(f"  ✗ Could not parse date: {date_str}")
                        continue
                    
                    # Parse time if provided
                    time_str = entry['time_str']
                    event_datetime = event_date
                    
                    if time_str:
                        # Extract hour from time string (e.g., "11:00 AM (EST)" or "15:00")
                        time_match = re.search(r'(\d{1,2}):(\d{2})', time_str)
                        if time_match:
                            hour = int(time_match.group(1))
                            minute = int(time_match.group(2))
                            
                            # Check for AM/PM
                            if 'PM' in time_str.upper() and hour != 12:
                                hour += 12
                            elif 'AM' in time_str.upper() and hour == 12:
                                hour = 0
                            
                            event_datetime = event_date.replace(hour=hour, minute=minute)
                    
                    # Determine if completed
                    now = datetime.now()
                    completed = event_datetime < now
                    
                    parsed_entries.append({
                        'datetime': event_datetime,
                        'time_display': f"{event_date.strftime('%d %B %Y')}{' - ' + time_str if time_str else ''}",
                        'location': entry['location'],
                        'purpose': entry['purpose'],
                        'completed': completed
                    })
                    
                except Exception as e:
                    print(f"  ✗ Error parsing entry: {e}")
                    continue
            
            if not parsed_entries:
                print(f"  No valid entries for {figure_name}")
                return
            
            # Sort by datetime (most recent first)
            parsed_entries.sort(key=lambda x: x['datetime'], reverse=True)
            
            # Find most recent completed event
            completed_entries = [e for e in parsed_entries if e['completed']]
            
            if not completed_entries:
                print(f"  No completed events yet for {figure_name}")
                return
            
            latest = completed_entries[0]
            
            # Get figure from database to find category info
            figure = self.db.get_figure_by_name(figure_name)
            
            if not figure:
                print(f"  ✗ Figure not found in database: {figure_name}")
                return
            
            # Update in database
            self.db.add_or_update_figure(
                name=figure_name,
                location=latest['location'],
                date_time=latest['time_display'],
                purpose=latest['purpose'],
                category_type=figure['category_type'],
                category_id=figure['category_id'],
                source_url=f"https://docs.google.com/spreadsheets/d/{self.sheet_id}",
                display_order=figure['display_order']
            )
            
            print(f"\n{'='*50}")
            print(f"✓ Updated {figure_name}:")
            print(f"  Location: {latest['location']}")
            print(f"  Time: {latest['time_display']}")
            print(f"  Purpose: {latest['purpose']}")
            print(f"{'='*50}")
            
        except Exception as e:
            print(f"✗ Error updating {figure_name}: {e}")
            import traceback
            traceback.print_exc()

def main():
    scraper = GoogleSheetsScraper()
    scraper.scrape()

if __name__ == "__main__":
    main()
