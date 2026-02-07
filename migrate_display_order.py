"""
Migration script to add display_order column and set proper ordering
Run this once: python3 migrate_display_order.py
"""

import sqlite3

def migrate():
    conn = sqlite3.connect('figurewatch.db')
    cursor = conn.cursor()
    
    print("Starting migration...")
    
    # Check if column already exists
    cursor.execute("PRAGMA table_info(political_figures)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'display_order' not in columns:
        print("Adding display_order column...")
        cursor.execute('ALTER TABLE political_figures ADD COLUMN display_order INTEGER DEFAULT 999')
        conn.commit()
        print("✓ Column added")
    else:
        print("✓ Column already exists")
    
    # Set display orders for specific figures
    display_orders = {
        # USA
        'President, Donald J. Trump': 1,
        'Secretary of State, Marco Rubio': 2,
        
        # France
        'President, Emmanuel Macron': 1,
        
        # Germany
        'Chancellor, Friedrich Merz': 1,
        
        # Italy
        'Prime Minister, Giorgia Meloni': 1,
        
        # Türkiye
        'President, Recep Tayyip Erdoğan': 1,
        'Minister of Foreign Affairs, Hakan Fidan': 2,
        
        # NATO
        'Secretary General, Mark Rutte': 1,
    }
    
    print("\nSetting display orders...")
    for name, order in display_orders.items():
        cursor.execute('''
            UPDATE political_figures 
            SET display_order = ? 
            WHERE name = ?
        ''', (order, name))
        if cursor.rowcount > 0:
            print(f"  ✓ Set {name} to order {order}")
        else:
            print(f"  ⚠ {name} not found in database")
    
    conn.commit()
    
    # Verify the results
    print("\n" + "="*60)
    print("VERIFICATION - Türkiye figures order:")
    print("="*60)
    cursor.execute('''
        SELECT name, display_order 
        FROM political_figures 
        WHERE name LIKE '%Erdoğan%' OR name LIKE '%Fidan%'
        ORDER BY display_order, name
    ''')
    for row in cursor.fetchall():
        print(f"  {row[1]}: {row[0]}")
    
    print("\n" + "="*60)
    print("VERIFICATION - USA figures order:")
    print("="*60)
    cursor.execute('''
        SELECT name, display_order 
        FROM political_figures 
        WHERE name LIKE '%Trump%' OR name LIKE '%Rubio%'
        ORDER BY display_order, name
    ''')
    for row in cursor.fetchall():
        print(f"  {row[1]}: {row[0]}")
    
    conn.close()
    print("\n✓ Migration complete!")

if __name__ == "__main__":
    migrate()
