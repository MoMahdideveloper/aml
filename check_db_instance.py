import sqlite3
conn = sqlite3.connect('./instance/real_estate_crm.db')
cursor = conn.cursor()
try:
    cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
    tables = cursor.fetchall()
    print('Tables:', [t[0] for t in tables])
    
    # Check a few key tables
    for table in ['property', 'agent', 'customer', 'deal', 'task']:
        try:
            cursor.execute('SELECT COUNT(*) FROM ' + table)
            count = cursor.fetchone()[0]
            print(table.capitalize() + ':', count)
        except:
            print(table.capitalize() + ': Table not found or error')
except Exception as e:
    print('Error:', e)
finally:
    conn.close()
