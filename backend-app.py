from flask import Flask, jsonify, request
from flask_cors import CORS
from database import Database
import os

app = Flask(__name__)
CORS(app)  # Allow iOS app to connect

db = Database()

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'FigureWatch API is running'})

# Countries endpoints
@app.route('/api/countries', methods=['GET'])
def get_countries():
    countries = db.get_all_countries()
    # Add figures for each country
    for country in countries:
        country['figures'] = db.get_figures_by_category('country', country['id'])
    return jsonify(countries)

@app.route('/api/countries/<int:country_id>/figures', methods=['GET'])
def get_country_figures(country_id):
    figures = db.get_figures_by_category('country', country_id)
    return jsonify(figures)

# Regional Arrangements endpoints
@app.route('/api/regional-arrangements', methods=['GET'])
def get_regional_arrangements():
    arrangements = db.get_all_regional_arrangements()
    # Add figures for each arrangement
    for arrangement in arrangements:
        arrangement['figures'] = db.get_figures_by_category('regional_arrangement', arrangement['id'])
    return jsonify(arrangements)

@app.route('/api/regional-arrangements/<int:arrangement_id>/figures', methods=['GET'])
def get_arrangement_figures(arrangement_id):
    figures = db.get_figures_by_category('regional_arrangement', arrangement_id)
    return jsonify(figures)

# Organizations endpoints
@app.route('/api/organizations', methods=['GET'])
def get_organizations():
    organizations = db.get_all_organizations()
    # Add figures for each organization
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

# Admin endpoints for adding data
@app.route('/api/admin/country', methods=['POST'])
def add_country():
    data = request.json
    country_id = db.add_country(data['name'])
    return jsonify({'id': country_id, 'name': data['name']}), 201

@app.route('/api/admin/regional-arrangement', methods=['POST'])
def add_regional_arrangement():
    data = request.json
    arrangement_id = db.add_regional_arrangement(data['name'])
    return jsonify({'id': arrangement_id, 'name': data['name']}), 201

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
    # Run on all network interfaces so iOS simulator can connect
    app.run(host='0.0.0.0', port=5000, debug=True)
