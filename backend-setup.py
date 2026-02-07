from database import Database

def setup_initial_data():
    """Setup initial countries, regional arrangements, and organizations"""
    db = Database()
    
    print("Setting up initial data...")
    
    # Add countries
    countries = [
        "United States",
        "Germany",
        "Türkiye"
    ]
    
    for country in countries:
        country_id = db.add_country(country)
        print(f"✓ Added country: {country} (ID: {country_id})")
    
    # Add regional arrangements
    arrangements = [
        "European Union",
        "African Union",
        "Arab League"
    ]
    
    for arrangement in arrangements:
        arr_id = db.add_regional_arrangement(arrangement)
        print(f"✓ Added regional arrangement: {arrangement} (ID: {arr_id})")
    
    # Add organizations
    organizations = [
        "United Nations",
        "NATO",
        "World Bank"
    ]
    
    for org in organizations:
        org_id = db.add_organization(org)
        print(f"✓ Added organization: {org} (ID: {org_id})")
    
    print("\n✓ Initial setup complete!")
    print("\nNext steps:")
    print("1. Run scrapers to add political figures")
    print("2. Start the API server: python app.py")

if __name__ == "__main__":
    setup_initial_data()
