# SOLUTION: Update your admin password to plain text

import sqlite3
import hashlib

def fix_admin_password():
    """Convert admin password from hash back to plain text for streamlit_authenticator"""
    
    conn = sqlite3.connect('personen.db')
    cursor = conn.cursor()
    
    # Update admin password to plain text
    cursor.execute('''
        UPDATE users 
        SET password = ? 
        WHERE username = ?
    ''', ('admin123', 'admin'))
    
    # Also update any other users that were created with hashed passwords
    # You might want to reset all user passwords to plain text
    
    # Check what users exist
    cursor.execute("SELECT username, password FROM users")
    users = cursor.fetchall()
    
    print("Current users and their passwords:")
    for user in users:
        username, password = user
        # Check if password looks like a hash (64 characters = SHA256)
        if len(password) == 64 and all(c in '0123456789abcdef' for c in password):
            print(f"  {username}: HASHED PASSWORD (needs fixing)")
            
            # Set default plain text passwords for hashed users
            if username.startswith('user'):
                new_password = 'password123'
            elif username == 'admin':
                new_password = 'admin123'
            else:
                new_password = 'changeme123'
            
            cursor.execute('UPDATE users SET password = ? WHERE username = ?', 
                         (new_password, username))
            print(f"    → Updated to: {new_password}")
        else:
            print(f"  {username}: PLAIN TEXT (OK)")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Password fix completed!")
    print("🔑 Login credentials:")
    print("   Admin: username='admin', password='admin123'")
    print("   Users: username='user1', 'user2', etc., password='password123'")

if __name__ == "__main__":
    fix_admin_password()