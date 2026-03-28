import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional

class Database:
    def __init__(self, db_path='figurewatch.db'):
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        """Initialize database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Countries table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS countries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Regional Arrangements table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS regional_arrangements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Organizations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS organizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Political Figures table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS political_figures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                location TEXT NOT NULL,
                date_time TEXT NOT NULL,
                purpose TEXT NOT NULL,
                category_type TEXT NOT NULL,
                category_id INTEGER NOT NULL,
                source_url TEXT,
                display_order INTEGER DEFAULT 999,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, category_type, category_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    # Country operations
    def add_country(self, name: str) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO countries (name) VALUES (?)', (name,))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            cursor.execute('SELECT id FROM countries WHERE name = ?', (name,))
            return cursor.fetchone()[0]
        finally:
            conn.close()
    
    def get_all_countries(self) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM countries ORDER BY name')
        countries = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return countries
    
    # Regional Arrangement operations
    def add_regional_arrangement(self, name: str) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO regional_arrangements (name) VALUES (?)', (name,))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            cursor.execute('SELECT id FROM regional_arrangements WHERE name = ?', (name,))
            return cursor.fetchone()[0]
        finally:
            conn.close()
    
    def get_all_regional_arrangements(self) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM regional_arrangements ORDER BY name')
        arrangements = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return arrangements
    
    # Organization operations
    def add_organization(self, name: str) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO organizations (name) VALUES (?)', (name,))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            cursor.execute('SELECT id FROM organizations WHERE name = ?', (name,))
            return cursor.fetchone()[0]
        finally:
            conn.close()
    
    def get_all_organizations(self) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM organizations ORDER BY name')
        organizations = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return organizations
    
    # Political Figure operations
    def add_or_update_figure(self, name: str, location: str, date_time: str, 
                            purpose: str, category_type: str, category_id: int,
                            source_url: str = None, display_order: int = 999):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO political_figures 
            (name, location, date_time, purpose, category_type, category_id, source_url, display_order, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(name, category_type, category_id) 
            DO UPDATE SET 
                location = excluded.location,
                date_time = excluded.date_time,
                purpose = excluded.purpose,
                source_url = excluded.source_url,
                display_order = excluded.display_order,
                last_updated = CURRENT_TIMESTAMP
        ''', (name, location, date_time, purpose, category_type, category_id, source_url, display_order))
        
        conn.commit()
        conn.close()
    
    def get_figure_by_name(self, name: str) -> Optional[Dict]:
        """Get a figure by their exact name"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM political_figures 
            WHERE name = ?
            LIMIT 1
        ''', (name,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    def get_figures_by_category(self, category_type: str, category_id: int) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM political_figures 
            WHERE category_type = ? AND category_id = ?
            ORDER BY display_order, name
        ''', (category_type, category_id))
        figures = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return figures
    
    def get_all_figures(self) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM political_figures ORDER BY display_order, name')
        figures = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return figures
    
    def delete_figure(self, figure_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM political_figures WHERE id = ?', (figure_id,))
        conn.commit()
        conn.close()
