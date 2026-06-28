import sqlite3
conn = sqlite3.connect('./instance/real_estate_crm.db')
cursor = conn.cursor()
try:
    cursor.execute('SELECT name FROM sqlite_master WHERE type="table" ORDER BY name')
    tables = cursor.fetchall()
    print('Tables found:', len(tables))
    
    # Look for our key tables (might be plural)
    key_tables = ['properties', 'agents', 'customers', 'deals', 'tasks']
    for table in key_tables:
        if table in [t[0] for t in tables]:
            try:
                cursor.execute('SELECT COUNT(*) FROM ' + table)
                count = cursor.fetchone()[0]
                print(f'{table.capitalize()}: {count} records')
            except Exception as e:
                print(f'{table.capitalize()}: Error querying - {e}')
        else:
            print(f'{table.capitalize()}: Table not found in database')
    
    # Also check singular versions
    singular_tables = ['property', 'agent', 'customer', 'deal', 'task']
    for table in singular_tables:
        if table in [t[0] for t in tables]:
            try:
                cursor.execute('SELECT COUNT(*) FROM ' + table)
                count = cursor.fetchone()[0]
                print(f'{table.capitalize()} (singular): {count} records')
            except Exception as e:
                print(f'{table.capitalize()} (singular): Error querying - {e}')
                
except Exception as e:
    print('Error:', e)
finally:
    conn.close()
