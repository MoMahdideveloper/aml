import sqlite3
import os

# Check the database in current directory (what the config points to)
db_path = './real_estate_crm.db'
if os.path.exists(db_path):
    print(f'Checking database: {db_path}')
    print(f'Size: {os.path.getsize(db_path)} bytes')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f'Tables found: {[t[0] for t in tables]}')
        
        # Check row counts for key tables
        for table in ['property', 'agent', 'customer', 'deal', 'task']:
            try:
                cursor.execute(f'SELECT COUNT(*) FROM {table}')
                count = cursor.fetchone()[0]
                print(f'  {table}: {count} records')
            except sqlite3.OperationalError as e:
                print(f'  {table}: Error - {e}')
        
        conn.close()
    except Exception as e:
        print(f'Error accessing database: {e}')
else:
    print(f'Database file not found: {db_path}')

print()

# Check the database in instance directory
db_path_instance = './instance/real_estate_crm.db'
if os.path.exists(db_path_instance):
    print(f'Checking database: {db_path_instance}')
    print(f'Size: {os.path.getsize(db_path_instance)} bytes')
    
    try:
        conn = sqlite3.connect(db_path_instance)
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f'Tables found: {[t[0] for t in tables]}')
        
        # Check row counts for key tables
        for table in ['property', 'agent', 'customer', 'deal', 'task']:
            try:
                cursor.execute(f'SELECT COUNT(*) FROM {table}')
                count = cursor.fetchone()[0]
                print(f'  {table}: {count} records')
            except sqlite3.OperationalError as e:
                print(f'  {table}: Error - {e}')
        
        conn.close()
    except Exception as e:
        print(f'Error accessing database: {e}')
else:
    print(f'Database file not found: {db_path_instance}")
