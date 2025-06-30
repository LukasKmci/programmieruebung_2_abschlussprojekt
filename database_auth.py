# database_auth.py - Enhanced Authentication and User Management Module
import sqlite3
import hashlib
import secrets
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import streamlit as st
import pandas as pd
import os
from PIL import Image
import io

class DatabaseAuth:
    """
    Enhanced Authentication and User Management Class for EKG Dashboard
    Handles user authentication, registration, profile management, and database operations
    Compatible with both personen.db and ekg_database.db structures
    """
    
    def __init__(self, db_path: str = "personen.db"):
        """
        Initialize the DatabaseAuth class
        
        Args:
            db_path (str): Path to the SQLite database file
        """
        self.db_path = db_path
        self.init_auth_tables()
    
    def get_db_connection(self) -> sqlite3.Connection:
        """Create and return a database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
        return conn
    
    def init_auth_tables(self):
        """
        Initialize authentication tables in the database
        Creates users table with all necessary fields including profile picture support
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # Create comprehensive users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
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
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                person_id INTEGER
            )
        ''')
        
        # Check if admin user exists, if not create default admin
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
        if cursor.fetchone()[0] == 0:
            # Create default admin user with hashed password
            admin_password = self._hash_password_simple("admin123")
            
            cursor.execute('''
                INSERT INTO users (username, password, email, full_name, role)
                VALUES (?, ?, ?, ?, ?)
            ''', ("admin", admin_password, "admin@ekg-dashboard.com", "Administrator", "admin"))
            
            print("✅ Default admin user created: username='admin', password='admin123'")
        
        conn.commit()
        conn.close()
    
    def _hash_password_simple(self, password: str) -> str:
        """
        Simple password hashing using SHA-256 (compatible with existing system)
        
        Args:
            password (str): Plain text password
            
        Returns:
            str: Hashed password
        """
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _verify_password_simple(self, password: str, password_hash: str) -> bool:
        """
        Verify a password against its hash
        
        Args:
            password (str): Plain text password to verify
            password_hash (str): Stored password hash
            
        Returns:
            bool: True if password is correct
        """
        return self._hash_password_simple(password) == password_hash
    
    def create_user(self, user_data: Dict[str, Any], picture_file=None) -> Tuple[bool, str]:
        """
        Create a new user account with profile picture support
        
        Args:
            user_data (Dict): User data dictionary
            picture_file: Uploaded picture file (optional)
            
        Returns:
            Tuple[bool, str]: Success status and message
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Check if username already exists
            cursor.execute("SELECT username FROM users WHERE username = ?", (user_data['username'],))
            if cursor.fetchone():
                return False, "Benutzername bereits vergeben!"
            
            # Handle picture upload
            picture_path = None
            picture_data = None
            
            if picture_file is not None:
                # Create pictures directory if it doesn't exist
                pictures_dir = "user_pictures"
                os.makedirs(pictures_dir, exist_ok=True)
                
                # Save picture file
                picture_filename = f"{user_data['username']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                picture_path = os.path.join(pictures_dir, picture_filename)
                
                # Convert and save image
                image = Image.open(picture_file)
                # Resize image to reasonable size
                image.thumbnail((300, 300), Image.Resampling.LANCZOS)
                image.save(picture_path, "JPEG")
                
                # Also store as BLOB in database
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='JPEG')
                picture_data = img_byte_arr.getvalue()
            
            # Hash password
            hashed_password = self._hash_password_simple(user_data['password'])
            
            # Insert user
            cursor.execute('''
                INSERT INTO users (
                    username, password, email, full_name, firstname, lastname,
                    date_of_birth, gender, height_cm, weight_kg, picture_path, 
                    picture_data, role, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_data['username'],
                hashed_password,
                user_data['email'],
                user_data['full_name'],
                user_data.get('firstname', ''),
                user_data.get('lastname', ''),
                user_data.get('date_of_birth', ''),
                user_data.get('gender', ''),
                user_data.get('height_cm', 0),
                user_data.get('weight_kg', 0.0),
                picture_path,
                picture_data,
                user_data.get('role', 'user'),
                True
            ))
            
            conn.commit()
            conn.close()
            
            return True, f"Benutzer '{user_data['username']}' erfolgreich erstellt!"
            
        except sqlite3.IntegrityError:
            conn.close()
            return False, "Benutzername bereits vergeben!"
        except Exception as e:
            conn.close()
            return False, f"Fehler beim Erstellen des Benutzers: {str(e)}"
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate a user
        
        Args:
            username (str): Username
            password (str): Password
            
        Returns:
            Optional[Dict]: User data if authentication successful, None otherwise
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE username = ? AND is_active = 1', (username,))
        user = cursor.fetchone()
        
        conn.close()
        
        if user and self._verify_password_simple(password, user['password']):
            return {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'full_name': user['full_name'],
                'firstname': user['firstname'],
                'lastname': user['lastname'],
                'role': user['role'],
                'picture_data': user['picture_data'],
                'date_of_birth': user['date_of_birth'],
                'gender': user['gender'],
                'height_cm': user['height_cm'],
                'weight_kg': user['weight_kg']
            }
        
        return None
    
    def get_all_users_for_auth(self) -> Dict[str, Dict]:
        """
        Get all users in format required by streamlit-authenticator
        
        Returns:
            Dict: Users data in authenticator format
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT username, password, full_name, email, role FROM users WHERE is_active = 1')
        users = cursor.fetchall()
        
        conn.close()
        
        credentials = {
            'usernames': {}
        }
        
        for user in users:
            credentials['usernames'][user['username']] = {
                'password': user['password'],
                'name': user['full_name'],
                'email': user['email'],
                'role': user['role']
            }
        
        return credentials
    
    def get_user_by_username(self, username: str) -> Optional[sqlite3.Row]:
        """
        Get user data by username
        
        Args:
            username (str): Username to look up
            
        Returns:
            Optional[sqlite3.Row]: User data if found
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        
        conn.close()
        return user
    
    def update_last_login(self, username: str):
        """
        Update the last login timestamp for a user
        
        Args:
            username (str): Username to update
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            'UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE username = ?',
            (username,)
        )
        
        conn.commit()
        conn.close()
    
    def get_users_for_admin(self) -> pd.DataFrame:
        """
        Get all users data for admin management
        
        Returns:
            pd.DataFrame: Users data
        """
        conn = self.get_db_connection()
        
        query = '''
            SELECT 
                id,
                username,
                email,
                full_name,
                firstname,
                lastname,
                date_of_birth,
                gender,
                height_cm,
                weight_kg,
                role,
                is_active,
                created_at,
                last_login,
                picture_data,
                picture_path
            FROM users
            ORDER BY created_at DESC
        '''
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    
    def get_user_stats(self) -> Dict[str, Any]:
        """
        Get user statistics for admin dashboard
        
        Returns:
            Dict: User statistics
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # Total users
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
        total_users = cursor.fetchone()[0]
        
        # Users by role
        cursor.execute("SELECT role, COUNT(*) as count FROM users WHERE is_active = 1 GROUP BY role")
        roles = cursor.fetchall()
        by_role = {role['role']: role['count'] for role in roles}
        
        # Recent logins (last 7 days)
        cursor.execute('''
            SELECT COUNT(*) FROM users 
            WHERE last_login >= datetime('now', '-7 days') AND is_active = 1
        ''')
        recent_logins = cursor.fetchone()[0]
        
        # Users with pictures
        cursor.execute("SELECT COUNT(*) FROM users WHERE picture_data IS NOT NULL AND is_active = 1")
        users_with_pictures = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_users': total_users,
            'by_role': by_role,
            'recent_logins': recent_logins,
            'users_with_pictures': users_with_pictures
        }
    
    def deactivate_user(self, username: str) -> Tuple[bool, str]:
        """
        Deactivate a user (soft delete)
        
        Args:
            username (str): Username to deactivate
            
        Returns:
            Tuple[bool, str]: Success status and message
        """
        if username == 'admin':
            return False, "Admin-Benutzer kann nicht deaktiviert werden!"
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("UPDATE users SET is_active = 0 WHERE username = ?", (username,))
            
            if cursor.rowcount > 0:
                conn.commit()
                conn.close()
                return True, f"Benutzer '{username}' wurde deaktiviert."
            else:
                conn.close()
                return False, "Benutzer nicht gefunden!"
                
        except sqlite3.Error as e:
            conn.close()
            return False, f"Fehler beim Deaktivieren: {str(e)}"
    
    def activate_user(self, username: str) -> Tuple[bool, str]:
        """
        Activate a user
        
        Args:
            username (str): Username to activate
            
        Returns:
            Tuple[bool, str]: Success status and message
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("UPDATE users SET is_active = 1 WHERE username = ?", (username,))
            
            if cursor.rowcount > 0:
                conn.commit()
                conn.close()
                return True, f"Benutzer '{username}' wurde aktiviert."
            else:
                conn.close()
                return False, "Benutzer nicht gefunden!"
                
        except sqlite3.Error as e:
            conn.close()
            return False, f"Fehler beim Aktivieren: {str(e)}"
    
    def change_user_role(self, username: str, new_role: str) -> Tuple[bool, str]:
        """
        Change a user's role
        
        Args:
            username (str): Username
            new_role (str): New role (user/admin)
            
        Returns:
            Tuple[bool, str]: Success status and message
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("UPDATE users SET role = ? WHERE username = ?", (new_role, username))
            
            if cursor.rowcount > 0:
                conn.commit()
                conn.close()
                return True, f"Rolle für '{username}' wurde zu '{new_role}' geändert."
            else:
                conn.close()
                return False, "Benutzer nicht gefunden!"
                
        except sqlite3.Error as e:
            conn.close()
            return False, f"Fehler beim Ändern der Rolle: {str(e)}"
    
    def update_user_profile(self, username: str, profile_data: Dict[str, Any], 
                           picture_file=None) -> Tuple[bool, str]:
        """
        Update user profile information
        
        Args:
            username (str): Username to update
            profile_data (Dict): New profile data
            picture_file: New picture file (optional)
            
        Returns:
            Tuple[bool, str]: Success status and message
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Handle picture upload if provided
            picture_path = None
            picture_data = None
            
            if picture_file is not None:
                pictures_dir = "user_pictures"
                os.makedirs(pictures_dir, exist_ok=True)
                
                picture_filename = f"{username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                picture_path = os.path.join(pictures_dir, picture_filename)
                
                image = Image.open(picture_file)
                image.thumbnail((300, 300), Image.Resampling.LANCZOS)
                image.save(picture_path, "JPEG")
                
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='JPEG')
                picture_data = img_byte_arr.getvalue()
            
            # Build update query
            update_fields = []
            params = []
            
            for field, value in profile_data.items():
                if field != 'username':  # Don't update username
                    update_fields.append(f"{field} = ?")
                    params.append(value)
            
            if picture_path:
                update_fields.extend(["picture_path = ?", "picture_data = ?"])
                params.extend([picture_path, picture_data])
            
            if update_fields:
                params.append(username)
                query = f"UPDATE users SET {', '.join(update_fields)} WHERE username = ?"
                cursor.execute(query, params)
                
                conn.commit()
                conn.close()
                return True, "Profil erfolgreich aktualisiert!"
            else:
                conn.close()
                return False, "Keine Änderungen vorgenommen."
                
        except Exception as e:
            conn.close()
            return False, f"Fehler beim Aktualisieren des Profils: {str(e)}"
    
    def get_database_info(self) -> Dict[str, Any]:
        """
        Get database information for admin dashboard
        
        Returns:
            Dict: Database information
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # Get table structure
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        
        # Get database file size
        db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
        
        # Get recent activity
        cursor.execute('''
            SELECT username, full_name, created_at, last_login 
            FROM users 
            ORDER BY created_at DESC 
            LIMIT 10
        ''')
        recent_activity = cursor.fetchall()
        
        conn.close()
        
        return {
            'columns': [dict(col) for col in columns],
            'db_size_mb': round(db_size / (1024 * 1024), 2),
            'recent_activity': [dict(row) for row in recent_activity],
            'db_path': self.db_path
        }
    
    def change_password(self, username: str, old_password: str, new_password: str) -> Tuple[bool, str]:
        """
        Change user password
        
        Args:
            username (str): Username
            old_password (str): Current password
            new_password (str): New password
            
        Returns:
            Tuple[bool, str]: Success status and message
        """
        # First verify old password
        user = self.authenticate_user(username, old_password)
        if not user:
            return False, "Aktuelles Passwort ist falsch!"
        
        # Update password
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            new_password_hash = self._hash_password_simple(new_password)
            cursor.execute("UPDATE users SET password = ? WHERE username = ?", 
                         (new_password_hash, username))
            
            conn.commit()
            conn.close()
            return True, "Passwort erfolgreich geändert!"
            
        except Exception as e:
            conn.close()
            return False, f"Fehler beim Ändern des Passworts: {str(e)}"