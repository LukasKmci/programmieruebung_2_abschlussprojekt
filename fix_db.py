import sqlite3
import hashlib

# Connect to your database
conn = sqlite3.connect('personen.db')
cursor = conn.cursor()

# Get your existing users
cursor.execute("SELECT * FROM users")
existing_users = cursor.fetchall()
print(f"Found {len(existing_users)} existing users")

# Drop and recreate the table with the right structure
cursor.execute("DROP TABLE users")
cursor.execute('''
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT NOT NULL,
        full_name TEXT NOT NULL,
        firstname TEXT,
        lastname TEXT,
        date_of_birth TEXT,
        gender TEXT,
        height_cm INTEGER,
        weight_kg REAL,
        picture_path TEXT,
        picture_data BLOB,
        role TEXT DEFAULT 'user',
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP
    )
''')

# Add your existing users back with proper structure
for i, user in enumerate(existing_users, 1):
    firstname = user[1] if len(user) > 1 else f"User{i}"
    lastname = user[2] if len(user) > 2 else ""
    full_name = f"{firstname} {lastname}".strip()
    username = f"user{i}"
    password = hashlib.sha256('password123'.encode()).hexdigest()
    email = f"user{i}@example.com"
    
    cursor.execute('''
        INSERT INTO users (username, password, email, full_name, firstname, lastname, 
                          date_of_birth, gender, picture_path, role, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (username, password, email, full_name, firstname, lastname, 
          user[3] if len(user) > 3 else "", user[4] if len(user) > 4 else "", 
          user[5] if len(user) > 5 else "", 'user', 1))
    
    print(f"Migrated: {username} (password: password123)")

# Add admin user
admin_password = hashlib.sha256('admin123'.encode()).hexdigest()
cursor.execute('''
    INSERT INTO users (username, password, email, full_name, firstname, lastname, 
                      date_of_birth, gender, height_cm, weight_kg, role, is_active)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', ('admin', admin_password, 'admin@example.com', 'Administrator', 'Admin', 'User',
      '1990-01-01', 'other', 175, 70.0, 'admin', 1))

conn.commit()
conn.close()

print("\n✅ Database fixed!")
print("👑 Admin login: username='admin', password='admin123'")
print("👤 User logins: username='user1', 'user2', etc., password='password123'")