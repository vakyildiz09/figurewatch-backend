#
# figure_history.py
# Historical snapshots for Past Week's Events feature
# Created by V. Akyildiz on 6 February 2026.
# Copyright © 2026 FigureWatch. All rights reserved.
#

import sqlite3
from datetime import datetime, timedelta
from flask import Blueprint, jsonify

history_bp = Blueprint('history', __name__)

DB_FILE = 'figurewatch.db'

def init_history_db():
    """Initialize the figure history database table"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create table for historical snapshots
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS figure_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            figure_id INTEGER NOT NULL,
            snapshot_date DATE NOT NULL,
            location TEXT NOT NULL,
            date_time TEXT NOT NULL,
            purpose TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (figure_id) REFERENCES political_figures(id),
            UNIQUE(figure_id, snapshot_date)
        )
    ''')
    
    # Create index for faster queries
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_figure_date 
        ON figure_history(figure_id, snapshot_date)
    ''')
    
    conn.commit()
    conn.close()
    print("✓ Figure history database initialized")

def save_daily_snapshot(figure_id, location, date_time, purpose):
    """
    Save a daily snapshot for a figure
    Only saves if snapshot for today doesn't already exist
    
    Args:
        figure_id (int): The figure's database ID
        location (str): Current location
        date_time (str): Current date/time
        purpose (str): Current purpose
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        today = datetime.now().date()
        
        # Check if snapshot already exists for today
        cursor.execute('''
            SELECT id FROM figure_history 
            WHERE figure_id = ? AND snapshot_date = ?
        ''', (figure_id, today))
        
        if cursor.fetchone():
            # Snapshot already exists for today, skip
            conn.close()
            return False
        
        # Insert new snapshot
        cursor.execute('''
            INSERT INTO figure_history 
            (figure_id, snapshot_date, location, date_time, purpose)
            VALUES (?, ?, ?, ?, ?)
        ''', (figure_id, today, location, date_time, purpose))
        
        conn.commit()
        conn.close()
        
        print(f"✓ Saved snapshot for figure {figure_id} on {today}")
        
        # Clean up old snapshots (older than 7 days)
        cleanup_old_snapshots()
        
        return True
        
    except Exception as e:
        print(f"✗ Error saving snapshot for figure {figure_id}: {e}")
        return False

def cleanup_old_snapshots():
    """Delete snapshots older than 7 days"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cutoff_date = datetime.now().date() - timedelta(days=7)
        
        cursor.execute('''
            DELETE FROM figure_history 
            WHERE snapshot_date < ?
        ''', (cutoff_date,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        if deleted_count > 0:
            print(f"✓ Cleaned up {deleted_count} old snapshot(s)")
        
        return deleted_count
        
    except Exception as e:
        print(f"✗ Error cleaning up old snapshots: {e}")
        return 0

@history_bp.route('/api/figures/<int:figure_id>/history', methods=['GET'])
def get_figure_history(figure_id):
    """
    Get past 7 days of snapshots for a figure
    
    Returns:
        JSON with status and history array
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Get last 7 days of snapshots
        cursor.execute('''
            SELECT snapshot_date, location, date_time, purpose
            FROM figure_history
            WHERE figure_id = ?
            ORDER BY snapshot_date DESC
            LIMIT 7
        ''', (figure_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return jsonify({
                'status': 'no_history',
                'message': 'History not available yet. Please check again later.',
                'history': []
            }), 200
        
        history = []
        for row in rows:
            history.append({
                'date': row[0],
                'location': row[1],
                'date_time': row[2],
                'purpose': row[3]
            })
        
        return jsonify({
            'status': 'success',
            'history': history
        }), 200
        
    except Exception as e:
        print(f"✗ Error retrieving history for figure {figure_id}: {e}")
        return jsonify({
            'status': 'error',
            'message': 'History not available yet. Please check again later.',
            'history': []
        }), 500
