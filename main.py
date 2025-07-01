import streamlit as st
import streamlit_authenticator as stauth
import sqlite3
import uuid
import time
import pandas as pd
from person import Person
from ekg_data import EKG_data
from database_auth import DatabaseAuth
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import os
from datetime import datetime, date
import sqlite3
from PIL import Image
import io
import base64
import bcrypt

from PIL import Image, ExifTags
from sport_data import load_sports_data, filter_data_by_time_range, calculate_filtered_stats, format_duration, load_sports_data

st.set_page_config(
    page_title="EKG & Sports Analyse Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🫀🏃‍♂️"
)

# Database helper functions for personen.db
def init_personen_db():
    """Initialize personen.db with users table if it doesn't exist"""
    conn = sqlite3.connect('personen.db')
    cursor = conn.cursor()
    
    # Create users table if it doesn't exist
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
            last_login TIMESTAMP
        )
    ''')
    
    # Create sports_sessions table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sports_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            file_name TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def save_user_to_personen_db(user_data, picture_file=None):
    """Save user to personen.db"""
    try:
        conn = sqlite3.connect('personen.db')
        cursor = conn.cursor()
        
        picture_path = None
        picture_data = None
        
        # Handle picture upload
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
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(user_data['password'].encode('utf-8'), salt).decode('utf-8')
        
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
            user_data['firstname'],
            user_data['lastname'],
            user_data['date_of_birth'],
            user_data['gender'],
            user_data['height_cm'],
            user_data['weight_kg'],
            picture_path,
            picture_data,
            user_data.get('role', 'user'),
            True
        ))
        
        conn.commit()
        conn.close()
        return True, "Benutzer erfolgreich erstellt!"
        
    except sqlite3.IntegrityError:
        return False, "Benutzername bereits vergeben!"
    except Exception as e:
        return False, f"Fehler beim Erstellen des Benutzers: {str(e)}"

def get_user_from_personen_db(username):
    """Get user from personen.db"""
    conn = sqlite3.connect('personen.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    
    conn.close()
    return user

def get_all_users_from_personen_db():
    """Get all users from personen.db for authentication"""
    conn = sqlite3.connect('personen.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT username, password, full_name, email, role FROM users WHERE is_active = 1')
    users = cursor.fetchall()
    
    conn.close()
    
    # Format for streamlit_authenticator
    credentials = {
        'usernames': {}
    }
    
    for user in users:
        credentials['usernames'][user[0]] = {
            'password': user[1],
            'name': user[2],
            'email': user[3],
            'role': user[4]
        }
    
    return credentials

def update_last_login_personen_db(username):
    """Update last login timestamp"""
    conn = sqlite3.connect('personen.db')
    cursor = conn.cursor()
    
    cursor.execute(
        'UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE username = ?',
        (username,)
    )
    
    conn.commit()
    conn.close()

def init_ekg_tables():
    """Initialize EKG-related tables in personen.db"""
    conn = sqlite3.connect('personen.db')
    cursor = conn.cursor()
    
    # Create ekg_tests table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ekg_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            test_date TEXT NOT NULL,
            file_path TEXT NOT NULL,
            result_data TEXT,
            max_heart_rate INTEGER,
            avg_heart_rate REAL,
            duration_seconds REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def save_ekg_test_to_db(user_id, test_date, file_path, result_data=None, max_hr=None, avg_hr=None, duration=None):
    """Save EKG test to database"""
    conn = sqlite3.connect('personen.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO ekg_tests (user_id, test_date, file_path, result_data, max_heart_rate, avg_heart_rate, duration_seconds)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, test_date, file_path, result_data, max_hr, avg_hr, duration))
    
    conn.commit()
    test_id = cursor.lastrowid
    conn.close()
    return test_id

def get_ekg_tests_for_user(user_id):
    """Get all EKG tests for a specific user"""
    conn = sqlite3.connect('personen.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, test_date, file_path, result_data, max_heart_rate, avg_heart_rate, duration_seconds, created_at
        FROM ekg_tests 
        WHERE user_id = ? 
        ORDER BY test_date DESC
    ''', (user_id,))
    
    tests = cursor.fetchall()
    conn.close()
    return tests

def get_user_with_ekg_data():
    """Get all users who have EKG data"""
    conn = sqlite3.connect('personen.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT DISTINCT u.* 
        FROM users u 
        INNER JOIN ekg_tests e ON u.id = e.user_id
    ''')
    users = cursor.fetchall()
    conn.close()
    return users

def init_ekg_tables():
    """Initialize EKG tables if they don't exist"""
    conn = sqlite3.connect('personen.db')
    cursor = conn.cursor()
    
    # Create ekg_tests table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ekg_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            result_link TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize personen.db
init_personen_db()

# Get credentials from personen.db
credentials = get_all_users_from_personen_db()

if credentials['usernames']:
    authenticator = stauth.Authenticate(
        credentials,
        'ekg_dashboard',
        'abcdef',  # Cookie key - in production this should be more secure
        cookie_expiry_days=7
    )
    
    # Login Widget
    try:
        authenticator.login()
    except Exception as e:
        st.error(f"Login error: {e}")
    
    # Get authentication status from session state
    authentication_status = st.session_state.get('authentication_status')
    name = st.session_state.get('name')
    username = st.session_state.get('username')
    
    if authentication_status == False:
        st.error('❌ Benutzername/Passwort ist falsch')
        
        # Registration form for new users
        with st.expander("🆕 Neuen Account erstellen"):
            st.subheader("Registrierung")
            with st.form("register_form"):
                new_username = st.text_input("Benutzername")
                new_password = st.text_input("Passwort", type="password")
                new_password_confirm = st.text_input("Passwort bestätigen", type="password")
                new_email = st.text_input("E-Mail")
                new_full_name = st.text_input("Vollständiger Name")
                
                # Additional personal data
                st.subheader("Persönliche Daten")
                col1, col2 = st.columns(2)
                with col1:
                    new_firstname = st.text_input("Vorname")
                    new_date_of_birth = st.date_input(
                        "Geburtsdatum",
                        value=date(1990, 1, 1),
                        min_value=date(1900, 1, 1),
                        max_value=date.today(),
                        help="Wählen Sie Ihr Geburtsdatum aus"
                    )
                    new_height = st.number_input("Größe (cm)", min_value=100, max_value=250, value=175)
                with col2:
                    new_lastname = st.text_input("Nachname")
                    new_gender = st.selectbox("Geschlecht", ["male", "female", "other"])
                    new_weight = st.number_input("Gewicht (kg)", min_value=30.0, max_value=200.0, value=70.0)
                
                # Picture upload
                st.subheader("📷 Profilbild")
                picture_file = st.file_uploader(
                    "Profilbild hochladen (optional)",
                    type=['png', 'jpg', 'jpeg'],
                    help="Unterstützte Formate: PNG, JPG, JPEG"
                )
                
                register_submit = st.form_submit_button("Registrieren")
                
                if register_submit:
                    if new_password != new_password_confirm:
                        st.error("❌ Passwörter stimmen nicht überein!")
                    elif len(new_password) < 6:
                        st.error("❌ Passwort muss mindestens 6 Zeichen lang sein!")
                    elif not new_username or not new_email or not new_full_name:
                        st.error("❌ Bitte alle Pflichtfelder ausfüllen!")
                    else:
                        user_data = {
                            'username': new_username,
                            'password': new_password,
                            'email': new_email,
                            'full_name': new_full_name,
                            'firstname': new_firstname,
                            'lastname': new_lastname,
                            'date_of_birth': str(new_date_of_birth),
                            'gender': new_gender,
                            'height_cm': new_height,
                            'weight_kg': new_weight
                        }
                        
                        success, message = save_user_to_personen_db(user_data, picture_file)
                        
                        if success:
                            st.success(f"✅ {message}")
                            st.info("🔄 Bitte laden Sie die Seite neu und loggen Sie sich ein.")
                        else:
                            st.error(f"❌ {message}")
        
    elif authentication_status == None:
        st.warning('👤 Bitte geben Sie Ihren Benutzername und Passwort ein')
        
    elif authentication_status:
        # Login successful - Update last login
        update_last_login_personen_db(username)
        
        # Get user info from personen.db
        user_data = get_user_from_personen_db(username)
        current_user_role = credentials['usernames'][username]['role']
        
        # Logout button
        authenticator.logout('Logout', 'sidebar')
        
        # Header with user info - DIFFERENT LAYOUTS FOR ADMIN VS USER
        if current_user_role == 'admin':
            # ADMIN LAYOUT
            st.title("🔧 EKG Analyse Dashboard - ADMINISTRATOR")
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.markdown(f"**Willkommen, {name}!**")
            with col2:
                st.markdown("🔒 **ADMIN PANEL**")
            with col3:
                st.markdown(f"👥 **{len(credentials['usernames'])} Benutzer**")
        else:
            # USER LAYOUT
            st.title("🫀 EKG Analyse Dashboard")
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**Willkommen, {name}!**")
                # Show user's profile picture if available
                if user_data and user_data[12]:  # picture_data column
                    try:
                        image = Image.open(io.BytesIO(user_data[12]))
                        st.image(image, width=100, caption="Ihr Profilbild")
                    except:
                        pass
            with col2:
                st.markdown("👤 **Benutzer**")
        
        st.markdown("---")
        
        # Sidebar Navigation - DIFFERENT FOR ADMIN VS USER
        with st.sidebar:
            if current_user_role == 'admin':
                # ADMIN SIDEBAR
                st.header(f"🔧 Admin: {name}")
                st.markdown("**🔒 Administrator-Bereich**")
                
                admin_tab = st.radio(
                    "Navigation",
                    ["📊 EKG-Analyse", "👥 Benutzerverwaltung", "📥 FIT-Import", "📂 FIT-Dateien", "🗃️ Datenbank-Info"]
                )
            else:
                # USER SIDEBAR
                st.header(f"👋 Hallo, {name}")
                st.markdown("**📊 Ihre EKG-Daten**")
                
                # Show user info
                if user_data:
                    st.markdown(f"**Name:** {user_data[5]} {user_data[6]}")  # firstname, lastname
                    if user_data[7]:  # date_of_birth
                        st.markdown(f"**Geburt:** {user_data[7]}")
                
                admin_tab = st.radio(
                    "Navigation",
                    ["📊 EKG-Analyse", "🏋️‍♂️ Trainings", "📥 FIT-Import"]
                )
        
        # ADMIN-BEREICH - User Management
        if current_user_role == 'admin' and admin_tab == "👥 Benutzerverwaltung":
            st.header("👥 Benutzerverwaltung")
            
            # Get all users from personen.db
            conn = sqlite3.connect('personen.db')
            users_df = pd.read_sql_query('SELECT * FROM users ORDER BY created_at DESC', conn)
            conn.close()
            
            # User statistics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("👥 Gesamt Benutzer", len(users_df))
            with col2:
                admin_count = len(users_df[users_df['role'] == 'admin'])
                st.metric("🩺 Admins", admin_count)
            with col3:
                user_count = len(users_df[users_df['role'] == 'user'])
                st.metric("👤 Benutzer", user_count)
            with col4:
                active_count = len(users_df[users_df['is_active'] == 1])
                st.metric("✅ Aktiv", active_count)
            
            st.markdown("---")
            
            # Show all users with pictures
            st.subheader("📋 Alle Benutzer")
            
            for index, user in users_df.iterrows():
                with st.expander(f"👤 {user['full_name']} (@{user['username']})"):
                    col1, col2, col3 = st.columns([1, 2, 1])
                    
                    with col1:
                        # Show profile picture if available
                        if user['picture_data']:
                            try:
                                image = Image.open(io.BytesIO(user['picture_data']))
                                st.image(image, width=150, caption="Profilbild")
                            except:
                                st.info("📷 Bild nicht ladbar")
                        else:
                            st.info("📷 Kein Bild")
                    
                    with col2:
                        st.write(f"**E-Mail:** {user['email']}")
                        st.write(f"**Rolle:** {user['role']}")
                        st.write(f"**Name:** {user['firstname']} {user['lastname']}")
                        st.write(f"**Geburtsdatum:** {user['date_of_birth'] or 'N/A'}")
                        st.write(f"**Geschlecht:** {user['gender'] or 'N/A'}")
                        st.write(f"**Größe:** {user['height_cm']} cm")
                        st.write(f"**Gewicht:** {user['weight_kg']} kg")
                    
                    with col3:
                        st.write(f"**Erstellt:** {user['created_at']}")
                        st.write(f"**Letzter Login:** {user['last_login'] or 'Nie'}")
                        st.write(f"**Status:** {'🟢 Aktiv' if user['is_active'] else '🔴 Inaktiv'}")
                        
                        # Admin actions
                        if user['username'] != 'admin' and user['is_active']:
                            if st.button(f"🗑️ Deaktivieren", key=f"deactivate_{user['username']}"):
                                conn = sqlite3.connect('personen.db')
                                cursor = conn.cursor()
                                cursor.execute('UPDATE users SET is_active = 0 WHERE username = ?', (user['username'],))
                                conn.commit()
                                conn.close()
                                st.success("Benutzer deaktiviert!")
                                st.rerun()
        
        elif current_user_role == 'admin' and admin_tab == "🗃️ Datenbank-Info":
            st.header("🗃️ Datenbank-Informationen")
            
            st.subheader("📊 Personen.db Status")
            
            # Show database structure
            conn = sqlite3.connect('personen.db')
            
            # Table info
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(users)")
            columns = cursor.fetchall()
            
            st.write("**Tabellen-Struktur (users):**")
            columns_df = pd.DataFrame(columns, columns=['ID', 'Name', 'Type', 'NotNull', 'Default', 'PK'])
            st.dataframe(columns_df)
            
            # Recent activity
            recent_users = pd.read_sql_query(
                'SELECT username, full_name, created_at, last_login FROM users ORDER BY created_at DESC LIMIT 10',
                conn
            )
            
            st.write("**Letzte Aktivitäten:**")
            st.dataframe(recent_users)
            
            conn.close()
        # EKG-ANALYSE-BEREICH
        elif admin_tab == "📊 EKG-Analyse":
            st.header("🫀 EKG Analyse")
            st.markdown("---")

            # Initialize EKG tables
            init_ekg_tables()

            # Load users with EKG data from database
            try:
                users_with_ekg = get_user_with_ekg_data()
                
                if not users_with_ekg:
                    st.warning("⚠️ Keine EKG-Daten in der Datenbank verfügbar")
                    
                    # Show option to import EKG data
                    with st.expander("📥 EKG-Daten importieren"):
                        st.info("Hier können Sie EKG-Daten zu Benutzern hinzufügen:")
                        
                        # Get all users for selection
                        conn = sqlite3.connect('personen.db')
                        cursor = conn.cursor()
                        cursor.execute('SELECT id, firstname, lastname, username FROM users WHERE 1=1')  # Removed is_active check
                        all_users = cursor.fetchall()
                        conn.close()
                        
                        if all_users:
                            user_options = {f"{u[1]} {u[2]} (@{u[3]})": u[0] for u in all_users}
                            selected_user = st.selectbox("👤 Benutzer auswählen", list(user_options.keys()))
                            
                            with st.form("ekg_import_form"):
                                test_date = st.date_input("📅 Testdatum", value=date.today())
                                ekg_file = st.file_uploader("📁 EKG-Datei hochladen", type=['csv', 'txt', 'json'])
                                
                                if st.form_submit_button("📤 EKG-Test hinzufügen"):
                                    if ekg_file is not None:
                                        # Create EKG data directory
                                        ekg_dir = "data/ekg_data"
                                        os.makedirs(ekg_dir, exist_ok=True)
                                        
                                        # Save file
                                        user_id = user_options[selected_user]
                                        timestamp = int(time.time())
                                        filename = f"ekg_{user_id}_{timestamp}_{ekg_file.name}"
                                        file_path = os.path.join(ekg_dir, filename)
                                        
                                        with open(file_path, "wb") as f:
                                            f.write(ekg_file.read())
                                        
                                        # Save to database with correct column names
                                        conn = sqlite3.connect('personen.db')
                                        cursor = conn.cursor()
                                        cursor.execute('''
                                            INSERT INTO ekg_tests (user_id, date, result_link)
                                            VALUES (?, ?, ?)
                                        ''', (user_id, str(test_date), file_path))
                                        test_id = cursor.lastrowid
                                        conn.commit()
                                        conn.close()
                                        
                                        st.success(f"✅ EKG-Test erfolgreich hinzugefügt (ID: {test_id})")
                                        st.rerun()
                    st.stop()
                    
                # Create user selection options
                user_options = {}
                for user in users_with_ekg:
                    display_name = f"{user[5]} {user[6]}" if user[5] and user[6] else user[1]  # firstname lastname or username
                    user_options[display_name] = user[0]  # user_id
                    
                # Person selection in sidebar
                with st.sidebar:
                    st.markdown("---")
                    st.header("📋 EKG-Analyse")
                    selected_user_name = st.selectbox("👤 Person auswählen", list(user_options.keys()), key="person_select")

                # Main EKG analysis content
                if selected_user_name:
                    try:
                        selected_user_id = user_options[selected_user_name]
                        
                        # Get user data from database with correct column names
                        conn = sqlite3.connect('personen.db')
                        cursor = conn.cursor()
                        cursor.execute('SELECT * FROM users WHERE id = ?', (selected_user_id,))
                        user_data = cursor.fetchone()
                        conn.close()
                        
                        if not user_data:
                            st.error(f"❌ Benutzer mit ID '{selected_user_id}' nicht gefunden")
                            st.stop()
                        
                        # Show different information based on user role
                        if current_user_role == 'admin':
                            st.success("🔒 Admin-Ansicht: Vollzugriff auf alle EKG-Daten")
                        else:
                            st.info("👤 Benutzer-Ansicht: Eingeschränkter Zugriff")
                        
                        # Person information display
                        st.header("👤 Personeninformationen")
                        
                        col1, col2 = st.columns([2, 2])
                        
                        # Display image
                        with col1:
                            # Assuming picture_path is around index 10-11 based on your structure
                            if len(user_data) > 10 and user_data[10] and os.path.exists(user_data[10]):
                                st.image(user_data[10], caption=selected_user_name, width=150)
                            else:
                                st.warning("📷 Kein Bild gefunden")

                        with col2:
                            st.header("📝 Persönliche Daten")
                            st.write(f"**Name:** {selected_user_name}")
                            st.write(f"**E-Mail:** {user_data[3] if len(user_data) > 3 else 'N/A'}")  # email
                            st.write(f"**Geburtsdatum:** {user_data[7] if len(user_data) > 7 and user_data[7] else 'N/A'}")  # date_of_birth
                            st.write(f"**Geschlecht:** {user_data[8] if len(user_data) > 8 and user_data[8] else 'N/A'}")  # gender
                            
                            # Get EKG test count
                            conn = sqlite3.connect('personen.db')
                            cursor = conn.cursor()
                            cursor.execute('SELECT * FROM ekg_tests WHERE user_id = ?', (selected_user_id,))
                            ekg_tests = cursor.fetchall()
                            conn.close()
                            
                            st.write(f"**Verfügbare EKG-Tests:** {len(ekg_tests)}")
                            
                        # EKG data selection and display
                        st.markdown("---")
                        
                        if ekg_tests:
                            # Create EKG selection options with correct column names
                            ekg_options = {}
                            for test in ekg_tests:
                                test_id, user_id, test_date, result_link = test  # Match your db structure
                                display_text = f"Test {test_id} - {test_date}"
                                ekg_options[display_text] = test_id
                            
                            selected_ekg_display = st.selectbox("📊 EKG-Datensatz wählen", list(ekg_options.keys()))
                            selected_ekg_id = ekg_options[selected_ekg_display]

                            if selected_ekg_id:
                                try:
                                    # Get selected EKG test data
                                    selected_test = next(test for test in ekg_tests if test[0] == selected_ekg_id)
                                    test_id, user_id, test_date, result_link = selected_test
                                    
                                    # Try to load EKG data using existing EKG_data class
                                    try:
                                        ekg_obj = EKG_data.load_by_id(int(selected_ekg_id))
                                        
                                        # Calculate metrics
                                        birth_year = int(user_data[7][:4]) if len(user_data) > 7 and user_data[7] else 1990
                                        gender = user_data[8] if len(user_data) > 8 and user_data[8] else 'male'
                                        hr_info = ekg_obj.calc_max_heart_rate(birth_year, gender)
                                        max_hr = hr_info['max_hr']
                                        
                                        # Calculate average heart rate
                                        avg_hr = EKG_data.average_hr(
                                            ekg_obj.df["Messwerte in mV"], 
                                            sampling_rate=1000,
                                            threshold=360, 
                                            window_size=5, 
                                            min_peak_distance=200
                                        )
                                        
                                    except Exception as e:
                                        st.error(f"❌ Fehler beim Laden mit EKG_data Klasse: {e}")
                                        # Fallback: try to load data directly from file
                                        if result_link and os.path.exists(result_link):
                                            st.info("💡 Versuche direkte Datei-Analyse...")
                                            max_hr = 180  # Default values
                                            avg_hr = 120
                                        else:
                                            st.error("❌ EKG-Datei nicht gefunden")
                                            max_hr = None
                                            avg_hr = None
                                    
                                    st.header("📊 EKG-Kennzahlen")
                                    
                                    # Display metrics in columns
                                    col1, col2, col3, col4 = st.columns(4)
                                    
                                    with col1:
                                        st.metric("🫀 Max HR", f"{max_hr} bpm" if max_hr else "N/A")
                                    
                                    with col2:
                                        if avg_hr and not pd.isna(avg_hr):
                                            st.metric("💓 Ø Herzfrequenz", f"{avg_hr:.1f} bpm")
                                            
                                            # HR zone evaluation
                                            if max_hr:
                                                hr_percentage = (avg_hr / max_hr) * 100
                                                if hr_percentage < 50:
                                                    hr_zone = "Ruhezone"
                                                    zone_color = "🟢"
                                                elif hr_percentage < 70:
                                                    hr_zone = "Aerobe Zone"
                                                    zone_color = "🟡"
                                                elif hr_percentage < 85:
                                                    hr_zone = "Anaerobe Zone"
                                                    zone_color = "🟠"
                                                else:
                                                    hr_zone = "Maximale Zone"
                                                    zone_color = "🔴"
                                            else:
                                                hr_percentage = 0
                                                hr_zone = "Unbekannt"
                                                zone_color = "⚪"
                                        else:
                                            st.metric("💓 Ø Herzfrequenz", "Nicht berechenbar")
                                            hr_percentage = 0
                                            hr_zone = "Unbekannt"
                                            zone_color = "⚪"
                                    
                                    with col3:
                                        if avg_hr and not pd.isna(avg_hr) and max_hr:
                                            st.metric("HR-Zone", f"{zone_color} {hr_zone}")
                                            st.write(f"({hr_percentage:.1f}% der Max HR)")
                                        else:
                                            st.metric("HR-Zone", "⚪ Unbekannt")
                                    
                                    with col4:
                                        st.metric("📅 Testdatum", test_date)

                                    # Try to display EKG plot if EKG object was loaded successfully
                                    if 'ekg_obj' in locals():
                                        # Time range selection with slider
                                        st.markdown("---")
                                        st.subheader("Zeitbereich auswählen")

                                        # Columns for time range selection
                                        col1, col2 = st.columns([3,1])
                                        
                                        with col1:
                                            # Convert time data to seconds for better UX
                                            time_data_seconds = (ekg_obj.df["time in ms"] - ekg_obj.df["time in ms"].min()) / 1000
                                            max_duration = time_data_seconds.max()

                                            # Dual-range slider in seconds
                                            time_range = st.slider(
                                                "Zeitbereich (Sekunden)",
                                                min_value=0.0,
                                                max_value=max_duration,
                                                value=(0.0, min(10.0, max_duration)),
                                                step=0.1,
                                                format="%.1f s"
                                            )
                                            # Display selected time range
                                            st.write(f"Gewählter Bereich: {time_range[0]:.1f} - {time_range[1]:.1f} Sekunden")

                                        with col2:
                                            # Calculate average heart rate in selected time range
                                            if time_range[0] != 0.0 or time_range[1] != max_duration:
                                                try:
                                                    # Calculate time data in seconds
                                                    time_seconds = (ekg_obj.df["time in ms"] - ekg_obj.df["time in ms"].min()) / 1000
                                                    # Mask for selected range
                                                    mask = (time_seconds >= time_range[0]) & (time_seconds <= time_range[1])
                                                    filtered_data = ekg_obj.df["Messwerte in mV"][mask]

                                                    if len(filtered_data) > 0:
                                                        # Use same parameters as above
                                                        range_hr = EKG_data.average_hr(
                                                            filtered_data,
                                                            sampling_rate=1000,
                                                            threshold=360,
                                                            window_size=5,
                                                            min_peak_distance=200
                                                        )
                                                        if not pd.isna(range_hr):
                                                            st.metric("💓 Bereichs-HR", f"{range_hr:.1f} bpm")
                                                        else:
                                                            st.warning("⚠️ HR nicht berechenbar")
                                                    else:
                                                        st.warning("⚠️ Keine Daten im Bereich")
                                                except Exception as e:
                                                    st.caption(f"❌ Fehler: {str(e)[:30]}...")

                                        # Display plot
                                        st.markdown("---")
                                        st.header("📈 EKG Zeitreihe")
                                        try:
                                            fig = ekg_obj.plot_time_series(
                                                threshold=360,
                                                min_peak_distance=200,
                                                range_start=time_range[0],
                                                range_end=time_range[1]
                                            )
                                            st.plotly_chart(fig, use_container_width=True, key=f"plot_{selected_ekg_id}")
                                        except Exception as e:
                                            st.error(f"❌ Fehler beim Erstellen des Plots: {e}")
                                    else:
                                        st.info("📊 EKG-Visualisierung nicht verfügbar - Datei konnte nicht geladen werden")
                                        st.markdown("**Gespeicherte Informationen:**")
                                        st.write(f"- Datei: {os.path.basename(result_link) if result_link else 'N/A'}")
                                        st.write(f"- Test-ID: {test_id}")
                                        st.write(f"- Datum: {test_date}")
                                    
                                except Exception as e:
                                    st.error(f"❌ Fehler beim Laden des EKG-Tests: {e}")
                                    st.info("💡 Überprüfen Sie, ob die EKG-Datei korrekt gespeichert wurde.")
                                    
                        else:
                            st.warning("📭 Keine EKG-Tests für diesen Benutzer verfügbar.")
                            
                            # Option to add EKG test
                            with st.expander("➕ EKG-Test hinzufügen"):
                                with st.form(f"add_ekg_{selected_user_id}"):
                                    test_date = st.date_input("📅 Testdatum", value=date.today())
                                    ekg_file = st.file_uploader("📁 EKG-Datei hochladen", type=['csv', 'txt', 'json'])
                                    
                                    if st.form_submit_button("📤 EKG-Test hinzufügen"):
                                        if ekg_file is not None:
                                            # Create EKG data directory
                                            ekg_dir = "data/ekg_data"
                                            os.makedirs(ekg_dir, exist_ok=True)
                                            
                                            # Save file
                                            timestamp = int(time.time())
                                            filename = f"ekg_{selected_user_id}_{timestamp}_{ekg_file.name}"
                                            file_path = os.path.join(ekg_dir, filename)
                                            
                                            with open(file_path, "wb") as f:
                                                f.write(ekg_file.read())
                                            
                                            # Save to database with correct column names
                                            conn = sqlite3.connect('personen.db')
                                            cursor = conn.cursor()
                                            cursor.execute('''
                                                INSERT INTO ekg_tests (user_id, date, result_link)
                                                VALUES (?, ?, ?)
                                            ''', (selected_user_id, str(test_date), file_path))
                                            test_id = cursor.lastrowid
                                            conn.commit()
                                            conn.close()
                                            
                                            st.success(f"✅ EKG-Test erfolgreich hinzugefügt (ID: {test_id})")
                                            st.rerun()
                                        else:
                                            st.error("❌ Bitte wählen Sie eine Datei aus")
                            
                    except Exception as e:
                        st.error(f"❌ Fehler beim Laden der Benutzerdaten: {e}")
                        st.info("💡 Überprüfen Sie, ob die Datenbank korrekt initialisiert wurde.")
                else:
                    # Welcome page with role-specific content
                    if current_user_role == 'admin':
                        st.header("🔧 Administrator Dashboard")
                        st.markdown("### Willkommen im Admin-Bereich!")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.info("🔒 **Vollzugriff:** Sie können alle EKG-Daten einsehen und Benutzer verwalten.")
                        with col2:
                            st.info("👥 **Verwaltung:** Nutzen Sie die Seitenleiste für Benutzerverwaltung.")
                    else:
                        st.header("🎯 Willkommen in Ihrem EKG-Dashboard!")
                        
                        col1, col2, col3 = st.columns([1, 2, 1])
                        with col2:
                            st.markdown("### Wählen Sie eine Person aus der Seitenleiste aus.")
                            st.info("👤 **Persönlicher Bereich:** Sie sehen nur verfügbare EKG-Daten.")
                            
            except Exception as e:
                st.error(f"❌ Fehler beim Laden der EKG-Daten: {e}")
                st.info("💡 Überprüfen Sie, ob alle erforderlichen Dateien vorhanden sind:")
                st.code("""
                - person.py
                - ekg_data.py  
                - personen.db Datenbank
                - EKG-Datendateien im data/ekg_data Verzeichnis
                """)

        # TRAINING-BEREICH
        elif admin_tab == "🏋️‍♂️ Trainings":
            st.title("🏋️‍♂️ Trainingsübersicht")
            st.markdown("---")

            # Load user from SQLite
            with st.sidebar:
                st.markdown("---")
                st.header("📋 Trainings-Analyse")
                
                # Load persons data from database for sports
                try:
                    conn = sqlite3.connect('personen.db')
                    cursor = conn.cursor()
                    cursor.execute('SELECT id, username, firstname, lastname FROM users WHERE is_active = 1')
                    users = cursor.fetchall()
                    conn.close()
                    
                    person_names = [f"{u[2]} {u[3]}" for u in users if u[2] and u[3]]
                    if not person_names:
                        person_names = [u[1] for u in users]  # Fallback to username
                        
                except Exception as e:
                    st.error(f"Error loading users: {e}")
                    person_names = []
                
                if not person_names:
                    st.warning("⚠️ Keine Personen verfügbar")
                    st.stop()
                    
                selected_name = st.selectbox("👤 Person auswählen", person_names, key="person_select")
            
            # Main sports analysis content
            if selected_name:
                # Find person from database
                try:
                    conn = sqlite3.connect('personen.db')
                    cursor = conn.cursor()
                    # Try to find by full name first
                    cursor.execute('SELECT * FROM users WHERE (firstname || " " || lastname) = ? OR username = ?', 
                                (selected_name, selected_name))
                    user_row = cursor.fetchone()
                    conn.close()
                    
                    if user_row:
                        person = {
                            'id': user_row[0],
                            'username': user_row[1],
                            'full_name': user_row[4],
                            'firstname': user_row[5],
                            'lastname': user_row[6],
                            'date_of_birth': user_row[7],
                            'gender': user_row[8],
                            'picture_path': user_row[11] if user_row[11] else "default_picture.jpg"
                        }
                    else:
                        person = None
                except Exception as e:
                    st.error(f"Error finding person: {e}")
                    person = None
                if person is None:
                    st.error("❌ Benutzer nicht gefunden!")
                    st.stop()

                # Display person information
                st.header("👤 Personeninformationen")
                col1, col2 = st.columns([2, 2])

                with col1:
                    if os.path.exists(person["picture_path"]):
                        st.image(person["picture_path"], caption=selected_name, width=150)
                    else:
                        st.warning("Kein Bild gefunden.")

                with col2:
                    st.write(f"**Name:** {selected_name}")
                    st.write(f"**Geburtsjahr:** {person['date_of_birth']}")
                    st.write(f"**Geschlecht:** {person['gender']}")

                st.markdown("---")

                # Load associated .fit files from SQLite
                conn = sqlite3.connect("personen.db")
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT file_name, timestamp FROM sports_sessions
                    WHERE user_id = ?
                    ORDER BY timestamp DESC
                """, (person["id"],))
                user_files = cursor.fetchall()
                conn.close()

                if not user_files:
                    st.warning("📭 Keine .fit-Dateien für diesen Benutzer.")
                    st.stop()

                file_labels = [f"{f[0]} – {f[1][:19]}" for f in user_files]
                selected_label = st.selectbox("📁 Wähle eine .fit-Datei", file_labels)
                selected_file = selected_label.split(" – ")[0].strip()
                full_path = os.path.join("data/sports_data", selected_file)

                # Load and analyze file
                from sport_data import get_time_range_info

                all_data = load_sports_data()

                # Debug output
                st.subheader("🧪 Debug: Verfügbare Dateien")
                st.write("📂 all_data.keys():", list(all_data.keys()))
                st.write("🟡 selected_file:", selected_file)
                if selected_file not in all_data:
                    st.error("❌ Datei konnte nicht geladen werden.")
                    st.stop()

                data = all_data[selected_file]
                if len(data['time']) == 0:
                    st.warning("⚠️ Keine Zeitdaten in dieser Datei.")
                    st.stop()

                # Analysis area
                total_duration = float(data['time'][-1] - data['time'][0])
                st.write(f"**Gesamte Trainingsdauer:** {format_duration(total_duration)}")

                time_range = st.slider(
                    "⏱️ Zeitraum wählen (min)",
                    min_value=0.0,
                    max_value=float(total_duration) / 60,
                    value=(0.0, float(total_duration) / 60),
                    step=0.5,
                    format="%.1f min"
                )

                start_percent = (time_range[0] * 60) / total_duration * 100
                end_percent = (time_range[1] * 60) / total_duration * 100

                filtered = filter_data_by_time_range(data, start_percent, end_percent)
                stats = calculate_filtered_stats(filtered)
                info = get_time_range_info(data, start_percent, end_percent)

                st.markdown("---")
                st.header("📊 Trainingsstatistiken")

                col1, col2, col3 = st.columns(3)
                col1.metric("⏱️ Dauer", format_duration(stats['duration_seconds']))
                col2.metric("📏 Distanz", f"{stats['total_distance_km']:.2f} km")
                col3.metric("🏃‍♂️ Ø Geschwindigkeit", f"{stats['avg_speed_kmh']:.1f} km/h")

                col4, col5, col6 = st.columns(3)
                col4.metric("🚀 Max. Geschwindigkeit", f"{stats['max_speed_kmh']:.1f} km/h")
                col5.metric("❤️ Ø Herzfrequenz", f"{stats['avg_heartrate']:.0f} bpm")
                col6.metric("❤️‍🔥 Max. Herzfrequenz", f"{stats['max_heartrate']:.0f} bpm")

                col7, col8, col9 = st.columns(3)
                col7.metric("⚙️ Ø Kadenz", f"{stats['avg_cadence']:.0f} rpm")
                col8.metric("⚙️ Max. Kadenz", f"{stats['max_cadence']:.0f} rpm")
                col9.metric("⚡ Ø Leistung", f"{stats['avg_power']:.0f} W")

                col10, col11, col12 = st.columns(3)
                col10.metric("⚡ Max. Leistung", f"{stats['max_power']:.0f} W")
                col11.metric("🌡️ Ø Temperatur", f"{stats['avg_temperature']:.1f} °C")
                col12.metric("🌡️ Max. Temperatur", f"{stats['max_temperature']:.1f} °C")

                col13, col14, col15 = st.columns(3)
                col13.metric("⛰️ Ø Höhe", f"{stats['avg_altitude']:.0f} m")
                col14.metric("⛰️ Max. Höhe", f"{stats['max_altitude']:.0f} m")
                col15.metric("⛰️ Min. Höhe", f"{stats['min_altitude']:.0f} m")

                # Plotly visualization for sports data
                st.markdown("---")
                st.header("📈 Trainingsverlauf im gewählten Zeitraum")

                t0 = filtered["time"][0]
                time_minutes = (filtered["time"] - t0) / 60
                mask = (time_minutes >= time_range[0]) & (time_minutes <= time_range[1])

                fig = go.Figure()

                # Heart rate
                if "heartrate" in filtered:
                    fig.add_trace(go.Scatter(
                        x=time_minutes[mask],
                        y=filtered["heartrate"][mask],
                        mode="lines",
                        name="Herzfrequenz (bpm)",
                        line=dict(color="red")
                    ))

                # Speed
                if "velocity" in filtered:
                    fig.add_trace(go.Scatter(
                        x=time_minutes[mask],
                        y=filtered["velocity"][mask] * 3.6,
                        mode="lines",
                        name="Geschwindigkeit (km/h)",
                        line=dict(color="blue")
                    ))

                # Power
                if "power" in filtered:
                    fig.add_trace(go.Scatter(
                        x=time_minutes[mask],
                        y=filtered["power"][mask],
                        mode="lines",
                        name="Leistung (W)",
                        line=dict(color="green")
                    ))

                fig.update_layout(
                    xaxis_title="Zeit (min)",
                    yaxis_title="Wert",
                    height=500,
                    legend=dict(x=0.01, y=0.99),
                    template="simple_white"
                )

                st.plotly_chart(fig, use_container_width=True)

        # FIT-IMPORT SECTION
        elif admin_tab == "📥 FIT-Import":
            st.title("📥 .fit-Datei hochladen & Benutzer zuweisen")
            st.markdown("---")

            # Load persons from database
            conn = sqlite3.connect("personen.db")
            cursor = conn.cursor()
            cursor.execute("SELECT id, firstname, lastname FROM users WHERE is_active = 1")
            users = cursor.fetchall()
            conn.close()

            if not users:
                st.error("⚠️ Keine aktiven Benutzer in der Datenbank!")
            else:
                user_dict = {f"{u[1]} {u[2]} (ID: {u[0]})": u[0] for u in users}
                selected_user_label = st.selectbox("👤 Benutzer auswählen", list(user_dict.keys()))
                selected_user_id = user_dict[selected_user_label]

                uploaded_file = st.file_uploader("📁 .fit-Datei auswählen", type=["fit"])

                if uploaded_file:
                    if st.button("📤 Datei hochladen"):
                        # Save file
                        save_dir = "data/sports_data"
                        os.makedirs(save_dir, exist_ok=True)

                        timestamp = int(time.time())
                        filename = f"{selected_user_id}_{timestamp}.fit"
                        save_path = os.path.join(save_dir, filename)

                        with open(save_path, "wb") as f:
                            f.write(uploaded_file.read())

                        # Save to database
                        conn = sqlite3.connect("personen.db")
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO sports_sessions (user_id, file_name, timestamp)
                            VALUES (?, ?, ?)
                        """, (selected_user_id, filename, datetime.fromtimestamp(timestamp).isoformat()))
                        conn.commit()
                        conn.close()

                        st.success(f"✅ Datei erfolgreich hochgeladen und Benutzer zugewiesen: {selected_user_label}")

        # FIT-FILES DISPLAY SECTION (Admin only)
        elif current_user_role == 'admin' and admin_tab == "📂 FIT-Dateien":
            st.title("📂 Zugeordnete .fit-Dateien anzeigen")
            st.markdown("---")

            # Load all users
            conn = sqlite3.connect("personen.db")
            cursor = conn.cursor()
            cursor.execute("SELECT id, firstname, lastname FROM users WHERE is_active = 1")
            users = cursor.fetchall()
            conn.close()

            if not users:
                st.warning("⚠️ Keine aktiven Benutzer gefunden.")
            else:
                user_map = {f"{u[1]} {u[2]} (ID: {u[0]})": u[0] for u in users}
                selected_user_label = st.selectbox("👤 Benutzer auswählen", list(user_map.keys()))
                selected_user_id = user_map[selected_user_label]

                # Get all associated .fit files
                conn = sqlite3.connect("personen.db")
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT file_name, timestamp FROM sports_sessions
                    WHERE user_id = ?
                    ORDER BY timestamp DESC
                """, (selected_user_id,))
                user_files = cursor.fetchall()
                conn.close()

                if not user_files:
                    st.info("📭 Dieser Benutzer hat noch keine .fit-Dateien.")
                else:
                    file_labels = [f"{f[0]} – {f[1][:19]}" for f in user_files]
                    selected_label = st.selectbox("📁 Datei auswählen", file_labels)
                    selected_file = selected_label.split(" – ")[0]

                    full_path = os.path.join("data/sports_data", selected_file)
                    if not os.path.exists(full_path):
                        st.error("❌ Datei nicht gefunden!")
                    else:
                        st.success(f"✅ Datei geladen: `{selected_file}`")

                        # Analyze with existing logic from sport_data
                        try:
                            from fitparse import FitFile

                            # Load only this file
                            data_dict = load_sports_data()
                            if selected_file not in data_dict:
                                st.error("❌ Fehler beim Einlesen der Datei!")
                            else:
                                data = data_dict[selected_file]
                                if len(data["time"]) == 0:
                                    st.warning("⚠️ Datei enthält keine Zeitdaten.")
                                else:
                                    total_duration = data["time"][-1] - data["time"][0]
                                    time_range = st.slider("Zeitauswahl (min)", 0.0, total_duration / 60, (0.0, total_duration / 60), step=0.5)

                                    start_percent = (time_range[0] * 60) / total_duration * 100
                                    end_percent = (time_range[1] * 60) / total_duration * 100

                                    filtered = filter_data_by_time_range(data, start_percent, end_percent)
                                    stats = calculate_filtered_stats(filtered)

                                    st.markdown("### 📊 Analyseergebnisse")
                                    col1, col2, col3, col4 = st.columns(4)
                                    col1.metric("Distanz", f"{stats['total_distance_km']:.2f} km")
                                    col2.metric("Ø Herzfrequenz", f"{stats['avg_heartrate']:.0f} bpm")
                                    col3.metric("Ø Geschwindigkeit", f"{stats['avg_speed_kmh']:.1f} km/h")
                                    col4.metric("Dauer", format_duration(stats['duration_seconds']))
                        except Exception as e:
                            st.error(f"❌ Fehler beim Analysieren der Datei: {e}")

else:
    st.error("❌ Keine Benutzer in der Datenbank gefunden. Bitte kontaktieren Sie den Administrator.")

# Footer
st.markdown("---")
if 'current_user_role' in locals() and current_user_role == 'admin':
    st.caption("EKG & Sports Analyse Dashboard - ADMINISTRATOR VERSION | Personen.db Integration")
else:
    st.caption("EKG & Sports Analyse Dashboard | Version 4.0")
st.caption("EKG & Sports Analyse Dashboard | Version 2.1 | Lukas Köhler | Simon Krainer")
