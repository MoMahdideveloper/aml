import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect('instance/real_estate_crm.db')
c = conn.cursor()
hashed = generate_password_hash('password123')
c.execute("UPDATE users SET password_hash = ?, is_active = 1 WHERE username = 'testuser'", (hashed,))
if c.rowcount == 0:
    c.execute("INSERT INTO users (username, email, password_hash, is_active, role) VALUES ('testuser', 'test@example.com', ?, 1, 'admin')", (hashed,))
conn.commit()
print("Updated testuser password to 'password123'")
