from flask import Flask, jsonify, request
from flask_cors import CORS
from database import Database
from push_notifications import notifications_bp, init_notifications_db
from scheduler import start_scheduler
from datetime import datetime
import os
import atexit

app = Flask(__name__)

# CORS configuration for production
CORS(app, resources={
    r"/api/*": {
        "origins": "*",  # Change to your domain after launch
        "methods": ["GET", "POST", "DELETE"],
        "allow_headers": ["Content-Type"]
    }
})

db = Database()

# Initialize databases
init_notifications_db()

# Initialize the tricky four if they don't exist
def init_tricky_four():
    """One-time initialization of the tricky four figures"""
    try:
        # Check if Rubio exists
        if not db.get_figure_by_name("Secretary of State, Marco Rubio"):
            print("Initializing tricky four figures...")
            
            # Add countries if they don't exist
            us_id = db.add_country("United States")
            turkiye_id = db.add_country("Türkiye")
            spain_id = db.add_country("Spain")
            japan_id = db.add_country("Japan")
            
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
            
            print("✓ Tricky four initialized successfully")
    except Exception as e:
        print(f"Note: Tricky four initialization: {e}")

# Run initialization
init_tricky_four()

# Register blueprints
app.register_blueprint(notifications_bp)

# Start the background scheduler
scheduler = start_scheduler()

# Shutdown scheduler gracefully when app stops
def shutdown_scheduler():
    if scheduler:
        scheduler.shutdown()
        
atexit.register(shutdown_scheduler)

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy', 
        'message': 'FigureWatch API is running',
        'scheduler': 'active' if scheduler and scheduler.running else 'inactive'
    })

# Countries endpoints
@app.route('/api/countries', methods=['GET'])
def get_countries():
    countries = db.get_all_countries()
    for country in countries:
        country['figures'] = db.get_figures_by_category('country', country['id'])
    return jsonify(countries)

@app.route('/api/countries/<int:country_id>/figures', methods=['GET'])
def get_country_figures(country_id):
    figures = db.get_figures_by_category('country', country_id)
    return jsonify(figures)

# Organizations endpoints
@app.route('/api/organizations', methods=['GET'])
def get_organizations():
    organizations = db.get_all_organizations()
    for org in organizations:
        org['figures'] = db.get_figures_by_category('organization', org['id'])
    return jsonify(organizations)

@app.route('/api/organizations/<int:org_id>/figures', methods=['GET'])
def get_organization_figures(org_id):
    figures = db.get_figures_by_category('organization', org_id)
    return jsonify(figures)

# All figures endpoint (for search)
@app.route('/api/figures', methods=['GET'])
def get_all_figures():
    figures = db.get_all_figures()
    return jsonify(figures)

# Admin endpoints
@app.route('/api/admin/country', methods=['POST'])
def add_country():
    data = request.json
    country_id = db.add_country(data['name'])
    return jsonify({'id': country_id, 'name': data['name']}), 201

@app.route('/api/admin/organization', methods=['POST'])
def add_organization():
    data = request.json
    org_id = db.add_organization(data['name'])
    return jsonify({'id': org_id, 'name': data['name']}), 201

@app.route('/api/admin/figure', methods=['POST'])
def add_figure():
    data = request.json
    db.add_or_update_figure(
        name=data['name'],
        location=data['location'],
        date_time=data['date_time'],
        purpose=data['purpose'],
        category_type=data['category_type'],
        category_id=data['category_id'],
        source_url=data.get('source_url')
    )
    return jsonify({'message': 'Figure added successfully'}), 201

@app.route('/api/admin/figure/<int:figure_id>', methods=['DELETE'])
def delete_figure(figure_id):
    db.delete_figure(figure_id)
    return jsonify({'message': 'Figure deleted successfully'}), 200

if __name__ == '__main__':
    # Get port from environment variable (DigitalOcean sets this)
    port = int(os.environ.get('PORT', 5001))
    
    # In production, gunicorn will run the app
    # This is only for local testing
    app.run(host='0.0.0.0', port=port, debug=False)
