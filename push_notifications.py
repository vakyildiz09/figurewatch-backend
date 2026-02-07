#
# push_notifications.py
# Push notification backend for FigureWatch
# Created by V. Akyildiz on 6 February 2026.
# Copyright © 2026 FigureWatch. All rights reserved.
#

from flask import Blueprint, request, jsonify
import sqlite3
from datetime import datetime

notifications_bp = Blueprint('notifications', __name__)

# Database file
DB_FILE = 'figurewatch.db'

def init_notifications_db():
    """Initialize the notifications database table"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create table for device tokens
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS device_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_token TEXT UNIQUE NOT NULL,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create table for figure notification preferences
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notification_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_token TEXT NOT NULL,
            figure_id INTEGER NOT NULL,
            enabled BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (device_token) REFERENCES device_tokens(device_token),
            FOREIGN KEY (figure_id) REFERENCES political_figures(id),
            UNIQUE(device_token, figure_id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✓ Notifications database initialized")

@notifications_bp.route('/api/register-device', methods=['POST'])
def register_device():
    """
    Register a device for push notifications
    
    Expected JSON:
    {
        "device_token": "abc123...",
        "enabled_figures": [1, 3, 5]
    }
    """
    try:
        data = request.json
        device_token = data.get('device_token')
        enabled_figures = data.get('enabled_figures', [])
        
        if not device_token:
            return jsonify({'status': 'error', 'message': 'No device token provided'}), 400
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Register or update device token
        cursor.execute('''
            INSERT INTO device_tokens (device_token, last_updated)
            VALUES (?, ?)
            ON CONFLICT(device_token) 
            DO UPDATE SET last_updated = ?
        ''', (device_token, datetime.now(), datetime.now()))
        
        # Clear old preferences for this device
        cursor.execute('DELETE FROM notification_preferences WHERE device_token = ?', (device_token,))
        
        # Add new preferences
        for figure_id in enabled_figures:
            cursor.execute('''
                INSERT INTO notification_preferences (device_token, figure_id, enabled)
                VALUES (?, ?, 1)
            ''', (device_token, figure_id))
        
        conn.commit()
        conn.close()
        
        print(f"✓ Device registered: {device_token[:10]}... with {len(enabled_figures)} figures")
        
        return jsonify({
            'status': 'success',
            'message': 'Device registered successfully',
            'enabled_figures': enabled_figures
        }), 200
        
    except Exception as e:
        print(f"✗ Error registering device: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@notifications_bp.route('/api/notification-status', methods=['GET'])
def notification_status():
    """
    Get notification statistics
    Returns total devices and figures being tracked
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Count devices
        cursor.execute('SELECT COUNT(*) FROM device_tokens')
        device_count = cursor.fetchone()[0]
        
        # Count active preferences
        cursor.execute('SELECT COUNT(*) FROM notification_preferences WHERE enabled = 1')
        pref_count = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'status': 'success',
            'total_devices': device_count,
            'total_preferences': pref_count
        }), 200
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

def get_devices_for_figure(figure_id):
    """
    Get all device tokens that have notifications enabled for a specific figure
    
    Args:
        figure_id (int): The ID of the political figure
    
    Returns:
        list: List of device token strings
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT device_token 
            FROM notification_preferences 
            WHERE figure_id = ? AND enabled = 1
        ''', (figure_id,))
        
        tokens = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return tokens
        
    except Exception as e:
        print(f"✗ Error getting devices for figure {figure_id}: {e}")
        return []

def send_notification_for_figure_update(figure_id, figure_name, message):
    """
    Send push notification to all devices interested in this figure
    
    Args:
        figure_id (int): The ID of the political figure
        figure_name (str): The name of the figure
        message (str): The notification message
    
    This function is called by scrapers when a figure's schedule changes
    
    NOTE: This is a placeholder. For production, you need to:
    1. Install apns2: pip install apns2
    2. Add your APNs certificate/key
    3. Implement actual push notification sending
    """
    tokens = get_devices_for_figure(figure_id)
    
    if not tokens:
        print(f"ℹ No devices to notify for figure {figure_id}")
        return
    
    print(f"📱 Would send notification to {len(tokens)} device(s):")
    print(f"   Figure: {figure_name}")
    print(f"   Message: {message}")
    
    # TODO: Implement actual APNs push notification
    # Example with apns2 (after setup):
    """
    from apns2.client import APNsClient
    from apns2.payload import Payload
    
    client = APNsClient('path/to/certificate.pem', use_sandbox=False)
    
    payload = Payload(
        alert=message,
        badge=1,
        sound="default",
        custom={'figure_id': figure_id}
    )
    
    for token in tokens:
        client.send_notification(token, payload, topic='com.yourapp.figurewatch')
    """
    
    return len(tokens)

# ==============================================================
# HOW TO USE IN SCRAPERS
# ==============================================================
"""
When a scraper detects a schedule change, call:

from push_notifications import send_notification_for_figure_update

# In your scraper, after updating the database:
if schedule_changed:
    send_notification_for_figure_update(
        figure_id=figure_id,
        figure_name="President Trump",
        message="New event scheduled for tomorrow in Paris"
    )
"""
