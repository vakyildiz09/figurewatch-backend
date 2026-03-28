#!/usr/bin/env python3
#
# init_tricky_four.py
# One-time script to initialize the tricky four figures in database
#

from database import Database
from datetime import datetime

db = Database()

# Add countries if they don't exist
us_id = db.add_country("United States")
turkiye_id = db.add_country("Türkiye")
spain_id = db.add_country("Spain")
japan_id = db.add_country("Japan")

# Initialize the tricky four with placeholder data
print("Initializing tricky four figures...")

# Rubio
db.add_or_update_figure(
    name="Secretary of State, Marco Rubio",
    location="Washington, D.C., U.S.",
    date_time=datetime.now().strftime("%d %B %Y"),
    purpose="Awaiting manual entry from Google Sheets",
    category_type="country",
    category_id=us_id,
    source_url="https://docs.google.com/spreadsheets",
    display_order=999
)
print("✓ Added Marco Rubio")

# Erdogan
db.add_or_update_figure(
    name="President, Recep Tayyip Erdoğan",
    location="Ankara, Türkiye",
    date_time=datetime.now().strftime("%d %B %Y"),
    purpose="Awaiting manual entry from Google Sheets",
    category_type="country",
    category_id=turkiye_id,
    source_url="https://docs.google.com/spreadsheets",
    display_order=1
)
print("✓ Added Recep Tayyip Erdoğan")

# Sánchez
db.add_or_update_figure(
    name="Prime Minister, Pedro Sánchez",
    location="Madrid, Spain",
    date_time=datetime.now().strftime("%d %B %Y"),
    purpose="Awaiting manual entry from Google Sheets",
    category_type="country",
    category_id=spain_id,
    source_url="https://docs.google.com/spreadsheets",
    display_order=1
)
print("✓ Added Pedro Sánchez")

# Takaichi
db.add_or_update_figure(
    name="Prime Minister, Sanae Takaichi",
    location="Tokyo, Japan",
    date_time=datetime.now().strftime("%d %B %Y"),
    purpose="Awaiting manual entry from Google Sheets",
    category_type="country",
    category_id=japan_id,
    source_url="https://docs.google.com/spreadsheets",
    display_order=1
)
print("✓ Added Sanae Takaichi")

print("\nAll done! The tricky four are now in the database.")
print("Google Sheets scraper will update them on next run.")
