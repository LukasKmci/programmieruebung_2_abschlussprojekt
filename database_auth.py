# database_auth.py - Enhanced version with Person integration
import sqlite3
import streamlit_authenticator as stauth
import pandas as pd
from datetime import datetime
import hashlib
import os

class DatabaseAuth:
    def __init__(self, db_path="ekg_users.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Erstellt die User-Tabelle mit Person-Attributen"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Enhanced Users Tabelle mit Person-Attributen
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                
                -- Person-spezifische Felder
                firstname TEXT,
                lastname TEXT,
                date_of_birth DATE,
                gender TEXT CHECK(gender IN ('male', 'female', 'other')),
                picture_path TEXT,
                
                -- Medizinische/Sportliche Zusatzdaten (optional)
                height_cm INTEGER,
                weight_kg REAL,
                medical_notes TEXT,
                emergency_contact TEXT,
                
                -- System-Felder
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                
                -- Person-ID für Verknüpfung mit EKG-Daten
                person_data_id TEXT UNIQUE
            )
        ''')
        
        # EKG-Tests Tabelle für bessere Datenverknüpfung
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ekg_tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                test_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                test_name TEXT,
                file_path TEXT,
                result_data TEXT,  -- JSON string mit Analyseergebnissen
                notes TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Admin-User erstellen falls nicht vorhanden
        admin_exists = cursor.execute(
            "SELECT COUNT(*) FROM users WHERE username = 'admin'"
        ).fetchone()[0]
        
        if admin_exists == 0:
            admin_password = stauth.Hasher(['admin123']).generate()[0]
            cursor.execute('''
                INSERT INTO users (
                    username, password, email, full_name, role,
                    firstname, lastname, date_of_birth, gender,
                    person_data_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                'admin', admin_password, 'admin@sportmedizin.de', 
                'Dr. Admin Sportmediziner', 'admin',
                'Admin', 'Sportmediziner', '1980-01-01', 'other',
                'admin_person_id'
            ))
        
        conn.commit()
        conn.close()
    
    def get_all_users(self):
        """Holt alle User aus der Datenbank für streamlit-authenticator"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT username, password, email, full_name, role 
            FROM users 
            WHERE is_active = TRUE
        '''
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # Format für streamlit-authenticator
        credentials = {'usernames': {}}
        
        for _, row in df.iterrows():
            credentials['usernames'][row['username']] = {
                'password': row['password'],
                'email': row['email'],
                'name': row['full_name'],
                'role': row['role']
            }
        
        return credentials
    
    def create_user(self, username, password, email, full_name, role='user', 
                   firstname=None, lastname=None, date_of_birth=None, 
                   gender=None, height_cm=None, weight_kg=None):
        """Neuen User mit Person-Daten erstellen"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Passwort hashen
            hashed_password = stauth.Hasher([password]).generate()[0]
            
            # Person-ID generieren (eindeutig für EKG-Daten-Verknüpfung)
            person_data_id = f"{username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Namen aufteilen falls nicht separat angegeben
            if not firstname and not lastname and full_name:
                name_parts = full_name.strip().split()
                firstname = name_parts[0] if len(name_parts) > 0 else ""
                lastname = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
            
            cursor.execute('''
                INSERT INTO users (
                    username, password, email, full_name, role,
                    firstname, lastname, date_of_birth, gender,
                    height_cm, weight_kg, person_data_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                username, hashed_password, email, full_name, role,
                firstname, lastname, date_of_birth, gender,
                height_cm, weight_kg, person_data_id
            ))
            
            conn.commit()
            return True, "Benutzer erfolgreich erstellt!"
            
        except sqlite3.IntegrityError as e:
            if "username" in str(e):
                return False, "Benutzername bereits vergeben!"
            elif "email" in str(e):
                return False, "E-Mail bereits registriert!"
            else:
                return False, f"Fehler: {str(e)}"
        except Exception as e:
            return False, f"Unbekannter Fehler: {str(e)}"
        finally:
            conn.close()
    
    def get_person_data_by_username(self, username):
        """Holt Person-Daten für einen User (für EKG-Integration)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                firstname, lastname, full_name, date_of_birth, 
                gender, picture_path, height_cm, weight_kg,
                person_data_id, email
            FROM users 
            WHERE username = ? AND is_active = TRUE
        ''', (username,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'firstname': result[0],
                'lastname': result[1], 
                'full_name': result[2],
                'date_of_birth': result[3],
                'gender': result[4],
                'picture_path': result[5] or 'data/pictures/default.jpg',
                'height_cm': result[6],
                'weight_kg': result[7],
                'person_data_id': result[8],
                'email': result[9]
            }
        return None
    
    def get_users_person_list(self, current_user_role, current_username):
        """Gibt Person-Liste basierend auf Benutzerrolle zurück"""
        conn = sqlite3.connect(self.db_path)
        
        if current_user_role == 'admin':
            # Admin sieht alle Personen
            query = '''
                SELECT full_name, username, person_data_id 
                FROM users 
                WHERE is_active = TRUE 
                ORDER BY full_name
            '''
            df = pd.read_sql_query(query, conn)
        else:
            # User sieht nur eigene Daten
            query = '''
                SELECT full_name, username, person_data_id 
                FROM users 
                WHERE username = ? AND is_active = TRUE
            '''
            df = pd.read_sql_query(query, conn, params=[current_username])
        
        conn.close()
        return df['full_name'].tolist()
    
    def update_user_picture(self, username, picture_path):
        """Profilbild-Pfad aktualisieren"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users 
            SET picture_path = ? 
            WHERE username = ?
        ''', (picture_path, username))
        
        conn.commit()
        conn.close()
    
    def add_ekg_test(self, username, test_name, file_path, result_data=None, notes=None):
        """EKG-Test zu User hinzufügen"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # User-ID holen
        user_id = cursor.execute(
            "SELECT id FROM users WHERE username = ?", (username,)
        ).fetchone()[0]
        
        cursor.execute('''
            INSERT INTO ekg_tests (user_id, test_name, file_path, result_data, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, test_name, file_path, result_data, notes))
        
        conn.commit()
        conn.close()
    
    def get_user_ekg_tests(self, username):
        """Alle EKG-Tests eines Users"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT e.id, e.test_date, e.test_name, e.file_path, e.notes
            FROM ekg_tests e
            JOIN users u ON e.user_id = u.id
            WHERE u.username = ? AND u.is_active = TRUE
            ORDER BY e.test_date DESC
        '''
        
        df = pd.read_sql_query(query, conn, params=[username])
        conn.close()
        return df
    
    def update_last_login(self, username):
        """Letzten Login aktualisieren"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users 
            SET last_login = CURRENT_TIMESTAMP 
            WHERE username = ?
        ''', (username,))
        
        conn.commit()
        conn.close()
    
    def delete_user(self, username):
        """User löschen (soft delete)"""
        if username == 'admin':
            return False, "Admin kann nicht gelöscht werden!"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users 
            SET is_active = FALSE 
            WHERE username = ?
        ''', (username,))
        
        conn.commit()
        conn.close()
        return True, f"Benutzer {username} wurde gelöscht!"
    
    def get_user_stats(self):
        """User-Statistiken für Admin-Dashboard"""
        conn = sqlite3.connect(self.db_path)
        
        stats = {}
        cursor = conn.cursor()
        
        # Gesamtanzahl aktive User
        stats['total_users'] = cursor.execute(
            "SELECT COUNT(*) FROM users WHERE is_active = TRUE"
        ).fetchone()[0]
        
        # User nach Rolle
        role_stats = cursor.execute('''
            SELECT role, COUNT(*) as count 
            FROM users 
            WHERE is_active = TRUE 
            GROUP BY role
        ''').fetchall()
        
        stats['by_role'] = dict(role_stats)
        
        # EKG-Tests Statistiken
        stats['total_ekg_tests'] = cursor.execute(
            "SELECT COUNT(*) FROM ekg_tests"
        ).fetchone()[0]
        
        # Kürzlich aktive User (letzte 7 Tage)
        stats['recent_logins'] = cursor.execute('''
            SELECT COUNT(*) FROM users 
            WHERE last_login >= datetime('now', '-7 days')
            AND is_active = TRUE
        ''').fetchone()[0]
        
        conn.close()
        return stats
    
    def get_users_for_admin(self):
        """Alle User-Details für Admin-Ansicht"""
        conn = sqlite3.connect(self.db_path)
        
        df = pd.read_sql_query('''
            SELECT 
                username, email, full_name, role, 
                firstname, lastname, date_of_birth, gender,
                created_at, last_login, is_active,
                (SELECT COUNT(*) FROM ekg_tests WHERE user_id = users.id) as ekg_count
            FROM users 
            ORDER BY created_at DESC
        ''', conn)
        
        conn.close()
        return df