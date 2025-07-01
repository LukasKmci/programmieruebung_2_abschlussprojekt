import streamlit_authenticator as stauth
import sqlite3

def test_hasher_api():
    """Test which Hasher API version we have"""
    try:
        # Try the old API
        hasher = stauth.Hasher(['test'])
        hashed = hasher.generate()
        print("Using old API: stauth.Hasher(['password']).generate()")
        return 'old'
    except:
        try:
            # Try newer API
            hasher = stauth.utilities.hasher.Hasher()
            hashed = hasher.hash('test')
            print("Using new API: stauth.utilities.hasher.Hasher().hash()")
            return 'new'
        except:
            try:
                # Try direct import
                from streamlit_authenticator.utilities.hasher import Hasher
                hasher = Hasher()
                hashed = hasher.hash('test')
                print("Using direct import API")
                return 'direct'
            except:
                print("Cannot determine API version")
                return 'unknown'

def hash_password_correct(password):
    """Hash password using the correct API"""
    api_version = test_hasher_api()
    
    if api_version == 'old':
        return stauth.Hasher([password]).generate()[0]
    elif api_version == 'new':
        hasher = stauth.utilities.hasher.Hasher()
        return hasher.hash(password)
    elif api_version == 'direct':
        from streamlit_authenticator.utilities.hasher import Hasher
        hasher = Hasher()
        return hasher.hash(password)
    else:
        # Fallback to bcrypt directly
        import bcrypt
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def reset_all_passwords():
    """Reset all user passwords to known values with proper hashing"""
    
    # Test the API first
    print("Testing streamlit_authenticator API...")
    api_version = test_hasher_api()
    
    # Define default passwords for each user
    default_passwords = {
        'admin': 'admin123',
        # Add other users as needed
        # 'user1': 'password123',
    }
    
    conn = sqlite3.connect('personen.db')
    cursor = conn.cursor()
    
    # Get all current users
    cursor.execute('SELECT username FROM users')
    users = cursor.fetchall()
    
    print("Resetting passwords for all users...")
    
    for (username,) in users:
        if username in default_passwords:
            password = default_passwords[username]
        else:
            # Set a default password for users not in the list
            password = 'password123'
        
        # Hash with the correct method
        try:
            hashed_password = hash_password_correct(password)
        except Exception as e:
            print(f"Error hashing password for {username}: {e}")
            continue
        
        # Update in database
        cursor.execute(
            'UPDATE users SET password = ? WHERE username = ?',
            (hashed_password, username)
        )
        
        print(f"✅ Reset password for {username} to: {password}")
    
    conn.commit()
    conn.close()
    
    print("\n🎉 All passwords have been reset!")
    print("You can now login with the passwords shown above.")

# Simple alternative using bcrypt directly
def reset_passwords_with_bcrypt():
    """Reset passwords using bcrypt directly (more reliable)"""
    import bcrypt
    
    # Define default passwords for each user
    default_passwords = {
        'admin': 'admin123',
        # Add other users as needed
    }
    
    conn = sqlite3.connect('personen.db')
    cursor = conn.cursor()
    
    # Get all current users
    cursor.execute('SELECT username FROM users')
    users = cursor.fetchall()
    
    print("Resetting passwords using bcrypt...")
    
    for (username,) in users:
        if username in default_passwords:
            password = default_passwords[username]
        else:
            password = 'password123'
        
        # Hash with bcrypt
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        
        # Update in database
        cursor.execute(
            'UPDATE users SET password = ? WHERE username = ?',
            (hashed_password, username)
        )
        
        print(f"✅ Reset password for {username} to: {password}")
    
    conn.commit()
    conn.close()
    
    print("\n🎉 All passwords have been reset with bcrypt!")

if __name__ == "__main__":
    print("Choose method:")
    print("1. Try streamlit_authenticator (auto-detect API)")
    print("2. Use bcrypt directly (recommended)")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "2":
        reset_passwords_with_bcrypt()
    else:
        reset_all_passwords()