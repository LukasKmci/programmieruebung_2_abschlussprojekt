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
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.widgets import RangeSlider
from scipy.signal import find_peaks


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

def streamlit_heart_rate_calculation(ekg_data, time_data_raw, sampling_rate=500):
    """
    Improved heart rate calculation for EKG data sampled at 500 Hz
    
    Args:
        ekg_data: numpy array of EKG values in mV
        time_data_raw: numpy array of raw time values (samples or ms)
        sampling_rate: sampling frequency in Hz (default 500)
    
    Returns:
        tuple: (average_heart_rate, message) or (None, error_message)
    """
    try:
        from scipy.signal import find_peaks
        import numpy as np
        
        # Input validation
        if len(ekg_data) < sampling_rate:  # Less than 1 second of data
            return None, "Insufficient data: need at least 1 second of EKG data"
        
        # Convert time data to seconds if needed
        if time_data_raw.max() > 100000:  # Likely sample indices
            time_data = time_data_raw / sampling_rate
        elif time_data_raw.max() > 1000:  # Likely milliseconds
            time_data = time_data_raw / 1000.0
        else:  # Already in seconds
            time_data = time_data_raw
        
        # Ensure time data starts from 0 and is monotonic
        time_data = time_data - time_data.min()
        total_duration = time_data.max()
        
        if total_duration < 2.0:  # Need at least 2 seconds for reliable HR
            return None, f"Recording too short: {total_duration:.1f}s (need ≥2s)"
        
        # Preprocess EKG signal
        # Remove DC offset
        ekg_filtered = ekg_data - np.mean(ekg_data)
        
        # Simple high-pass filter to remove baseline wander
        if len(ekg_filtered) > 100:
            # Remove slow baseline drift using moving average
            window_size = min(len(ekg_filtered) // 10, sampling_rate // 2)  # 0.5s window max
            if window_size > 5:
                moving_avg = np.convolve(ekg_filtered, np.ones(window_size)/window_size, mode='same')
                ekg_filtered = ekg_filtered - moving_avg
        
        # Calculate adaptive threshold for R-peak detection
        signal_abs = np.abs(ekg_filtered)
        signal_std = np.std(signal_abs)
        signal_mean = np.mean(signal_abs)
        
        # Lower threshold - more sensitive to catch more R-peaks
        # Use percentile-based approach
        threshold_base = np.percentile(signal_abs, 85)  # 85th percentile
        threshold = max(threshold_base, signal_mean + 1.5 * signal_std)
        
        # Minimum distance between peaks (300ms for 500Hz = 150 samples)
        # This prevents detecting noise as separate beats
        min_distance_samples = int(0.3 * sampling_rate)  # 300ms minimum
        
        # Find peaks with relaxed parameters
        peaks, peak_properties = find_peaks(
            ekg_filtered,
            height=threshold * 0.7,  # Reduce threshold by 30%
            distance=min_distance_samples,
            prominence=signal_std * 0.3,  # Lower prominence requirement
            width=1  # Minimum width in samples
        )
        
        # Validate peaks - remove obvious noise
        if len(peaks) > 0:
            peak_heights = ekg_filtered[peaks]
            peak_times = time_data[peaks]
            
            # Remove peaks that are too close to start/end
            valid_indices = (peak_times > 0.5) & (peak_times < total_duration - 0.5)
            peaks = peaks[valid_indices]
            peak_heights = peak_heights[valid_indices]
            peak_times = peak_times[valid_indices]
            
            # Remove outlier peaks (height-based filtering)
            if len(peaks) > 3:
                height_median = np.median(peak_heights)
                height_std = np.std(peak_heights)
                height_threshold = 3 * height_std  # 3-sigma rule
                
                valid_height_mask = np.abs(peak_heights - height_median) < height_threshold
                peaks = peaks[valid_height_mask]
                peak_times = peak_times[valid_height_mask]
        
        # Check if we found enough peaks
        if len(peaks) < 2:
            # Try with even lower threshold
            threshold_low = signal_mean + 0.5 * signal_std
            peaks_low, _ = find_peaks(
                ekg_filtered,
                height=threshold_low,
                distance=min_distance_samples,
                prominence=signal_std * 0.1
            )
            
            if len(peaks_low) >= 2:
                peaks = peaks_low
                peak_times = time_data[peaks]
                # Re-filter for valid time range
                valid_indices = (peak_times > 0.5) & (peak_times < total_duration - 0.5)
                peaks = peaks[valid_indices]
                peak_times = peak_times[valid_indices]
            
            if len(peaks) < 2:
                return None, f"Insufficient R-peaks detected: {len(peaks)} (threshold: {threshold:.3f}mV, signal range: {ekg_filtered.min():.3f} to {ekg_filtered.max():.3f}mV)"
        
        # Calculate heart rate from R-R intervals
        peak_times_sorted = np.sort(peak_times)
        rr_intervals = np.diff(peak_times_sorted)  # Time between consecutive R-peaks
        
        # Filter out unrealistic RR intervals
        # Normal RR intervals: 0.4s to 2.0s (150-30 bpm)
        valid_rr_mask = (rr_intervals >= 0.4) & (rr_intervals <= 2.0)
        
        if np.sum(valid_rr_mask) < 1:
            return None, f"No valid RR intervals found (all intervals outside 0.4-2.0s range)"
        
        valid_rr_intervals = rr_intervals[valid_rr_mask]
        
        # Calculate average heart rate
        avg_rr_interval = np.mean(valid_rr_intervals)
        avg_heart_rate = 60.0 / avg_rr_interval  # Convert to BPM
        
        # Additional validation - check if HR is in reasonable range
        if avg_heart_rate < 30 or avg_heart_rate > 200:
            return None, f"Calculated HR outside normal range: {avg_heart_rate:.1f} bpm"
        
        # Create detailed message
        message = (f"Found {len(peaks)} R-peaks over {total_duration:.1f}s, "
                  f"avg RR-interval: {avg_rr_interval:.3f}s, "
                  f"valid intervals: {len(valid_rr_intervals)}/{len(rr_intervals)}")
        
        return avg_heart_rate, message
        
    except ImportError:
        return None, "scipy.signal not available for peak detection"
    except Exception as e:
        return None, f"Error in heart rate calculation: {str(e)}"


# Also update the peak detection code for visualization
def extract_peaks_for_visualization(ekg_data, time_data, sampling_rate=500):
    """
    Extract R-peaks for visualization purposes
    Returns peak indices that can be used for plotting
    """
    try:
        from scipy.signal import find_peaks
        import numpy as np
        
        # Same preprocessing as in heart rate calculation
        ekg_filtered = ekg_data - np.mean(ekg_data)
        
        # Remove baseline drift
        if len(ekg_filtered) > 100:
            window_size = min(len(ekg_filtered) // 10, sampling_rate // 2)
            if window_size > 5:
                moving_avg = np.convolve(ekg_filtered, np.ones(window_size)/window_size, mode='same')
                ekg_filtered = ekg_filtered - moving_avg
        
        # Calculate threshold
        signal_abs = np.abs(ekg_filtered)
        signal_std = np.std(signal_abs)
        signal_mean = np.mean(signal_abs)
        threshold = max(np.percentile(signal_abs, 85), signal_mean + 1.5 * signal_std)
        
        # Find peaks
        min_distance_samples = int(0.3 * sampling_rate)
        peaks, _ = find_peaks(
            ekg_filtered,
            height=threshold * 0.7,
            distance=min_distance_samples,
            prominence=signal_std * 0.3,
            width=1
        )
        
        return peaks
        
    except Exception:
        return None
    
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
            try:
                # ROLE-BASED ACCESS CONTROL
                if current_user_role == 'admin':
                    # ADMIN: Can access all users' EKG data
                    st.info("🔧 **Administrator-Modus**: Sie können EKG-Daten aller Benutzer einsehen")
                    
                    # Load users with EKG data from database
                    try:
                        users_with_ekg = get_user_with_ekg_data()
                        
                        if not users_with_ekg:
                            st.warning("⚠️ Keine EKG-Daten in der Datenbank verfügbar")
                            
                            # Show option to import EKG data (ADMIN ONLY)
                            with st.expander("📥 EKG-Daten importieren"):
                                st.info("Hier können Sie EKG-Daten zu Benutzern hinzufügen:")
                                
                                # Get all users for selection
                                conn = None
                                try:
                                    conn = sqlite3.connect('personen.db')
                                    cursor = conn.cursor()
                                    cursor.execute('SELECT id, firstname, lastname, username FROM users WHERE 1=1')
                                    all_users = cursor.fetchall()
                                except Exception as db_error:
                                    st.error(f"Datenbankfehler beim Laden der Benutzer: {db_error}")
                                    all_users = []
                                finally:
                                    if conn:
                                        conn.close()
                                
                                if all_users:
                                    user_options = {f"{u[1]} {u[2]} (@{u[3]})": u[0] for u in all_users}
                                    selected_user = st.selectbox("👤 Benutzer auswählen", list(user_options.keys()))
                                    
                                    with st.form("ekg_import_form"):
                                        test_date = st.date_input("📅 Testdatum", value=date.today())
                                        ekg_file = st.file_uploader("📁 EKG-Datei hochladen", type=['csv', 'txt', 'json'])
                                        
                                        if st.form_submit_button("📤 EKG-Test hinzufügen"):
                                            if ekg_file is not None:
                                                try:
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
                                                except Exception as upload_error:
                                                    st.error(f"Fehler beim Hochladen der EKG-Datei: {upload_error}")
                            st.stop()
                            
                        # Create user selection options (ADMIN ONLY)
                        user_options = {}
                        for user in users_with_ekg:
                            display_name = f"{user[5]} {user[6]}" if user[5] and user[6] else user[1]  # firstname lastname or username
                            user_options[display_name] = user[0]  # user_id
                            
                        # Person selection in sidebar (ADMIN ONLY)
                        with st.sidebar:
                            st.markdown("---")
                            st.header("📋 EKG-Analyse (Admin)")
                            st.markdown("**🔧 Benutzer-Auswahl**")
                            selected_user_name = st.selectbox(
                                "👤 Person auswählen", 
                                list(user_options.keys()), 
                                key="person_select",
                                help="Als Admin können Sie jeden Benutzer auswählen"
                            )
                            selected_user_id = user_options[selected_user_name]
                            
                    except Exception as e:
                        st.error(f"Fehler beim Laden der EKG-Daten: {e}")
                        st.stop()
                        
                else:
                    # USER: Can only access their own EKG data
                    st.info("👤 **Benutzer-Modus**: Sie sehen nur Ihre eigenen EKG-Daten")
                    
                    # Get current user's ID
                    try:
                        current_user_data = get_user_from_personen_db(username)
                        if not current_user_data:
                            st.error("❌ Benutzerdaten nicht gefunden!")
                            st.stop()
                            
                        current_user_id = current_user_data[0]  # user ID
                        selected_user_id = current_user_id  # User can only access their own data
                        selected_user_name = f"{current_user_data[5]} {current_user_data[6]}" if current_user_data[5] and current_user_data[6] else current_user_data[1]
                        
                    except Exception as user_error:
                        st.error(f"Fehler beim Laden der Benutzerdaten: {user_error}")
                        st.stop()
                    
                    # Check if user has EKG data
                    conn = None
                    try:
                        conn = sqlite3.connect('personen.db')
                        cursor = conn.cursor()
                        cursor.execute('SELECT COUNT(*) FROM ekg_tests WHERE user_id = ?', (current_user_id,))
                        ekg_count = cursor.fetchone()[0]
                        
                        if ekg_count == 0:
                            st.warning("⚠️ Sie haben noch keine EKG-Daten")
                            st.info("💡 **Tipp**: Verwenden Sie den '📥 FIT-Import' Bereich, um Ihre EKG-Daten hochzuladen")
                            st.stop()
                            
                    except Exception as e:
                        st.error(f"Fehler beim Prüfen der EKG-Daten: {e}")
                        st.stop()
                    finally:
                        if conn:
                            conn.close()
                    
                    # Show user info in sidebar
                    with st.sidebar:
                        st.markdown("---")
                        st.header("📋 Ihre EKG-Analyse")
                        st.markdown(f"**👤 Analysiert:** {selected_user_name}")
                        st.markdown(f"**📊 EKG-Tests:** {ekg_count}")
                
        

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
                            
                            # Display image - FIXED VERSION
                            with col1:
                                image_displayed = False
                                
                                # First try to load from picture_data (BLOB) - index 12
                                if len(user_data) > 12 and user_data[12]:
                                    try:
                                        image = Image.open(io.BytesIO(user_data[12]))
                                        st.image(image, caption=selected_user_name, width=150)
                                        image_displayed = True
                                    except Exception as e:
                                        st.warning(f"📷 Fehler beim Laden des BLOB-Bildes: {e}")
                                
                                # If BLOB failed, try picture_path - index 11
                                if not image_displayed and len(user_data) > 11 and user_data[11]:
                                    picture_path = user_data[11]
                                    if os.path.exists(picture_path):
                                        try:
                                            st.image(picture_path, caption=selected_user_name, width=150)
                                            image_displayed = True
                                        except Exception as e:
                                            st.warning(f"📷 Fehler beim Laden der Bilddatei: {e}")
                                    else:
                                        st.warning(f"📷 Bilddatei nicht gefunden: {picture_path}")
                                
                                # If no image could be displayed
                                if not image_displayed:
                                    st.info("📷 Kein Profilbild verfügbar")
                                    # Debug information
                                    if len(user_data) > 11:
                                        st.caption(f"Debug: picture_path = {user_data[11]}")
                                        st.caption(f"Debug: picture_data exists = {bool(user_data[12]) if len(user_data) > 12 else False}")

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
                                        
                                        # DEBUG: Show file information
                                        with st.expander("🔍 Debug Information"):
                                            st.write(f"**Test ID:** {test_id}")
                                            st.write(f"**File Path:** {result_link}")
                                            
                                            # Resolve file path
                                            if result_link and not os.path.isabs(result_link):
                                                result_link = os.path.abspath(result_link)
                                            
                                            st.write(f"**Absolute Path:** {result_link}")
                                            st.write(f"**File exists:** {os.path.exists(result_link) if result_link else 'No path'}")
                                            if result_link and os.path.exists(result_link):
                                                st.write(f"**File size:** {os.path.getsize(result_link)} bytes")
                                        
                                        # Initialize variables
                                        ekg_data = None
                                        time_data = None
                                        sampling_rate = 500  # Default sampling rate
                                        ekg_obj = None
                                        use_ekg_class = False
                                        avg_hr = None
                                        max_hr = None
                                    
                                        # Fallback: Direct file loading with Plotly visualization
                                        if result_link and os.path.exists(result_link):
                                            try:
                                                
                                                # Determine file format and load accordingly
                                                if result_link.endswith('.csv'):
                                                    df = pd.read_csv(result_link)
                                                elif result_link.endswith('.txt'):
                                                    # Try different separators for text files
                                                    separators = ['\t', ';', ',', ' ']
                                                    df = None
                                                    for sep in separators:
                                                        try:
                                                            df = pd.read_csv(result_link, sep=sep, header=None)  # No header assumption
                                                            if df.shape[1] >= 2:  # Successfully parsed multiple columns
                                                                break
                                                        except:
                                                            continue
                                                    
                                                    if df is None or df.shape[1] < 2:
                                                        # Try reading as space-separated
                                                        df = pd.read_csv(result_link, delim_whitespace=True, header=None)
                                                else:
                                                    df = pd.read_csv(result_link, header=None)
                                    
                                                
                                                # Debug: Show first few rows
                                                with st.expander("🔍 Data Preview"):
                                                    st.write("First 10 rows of loaded data:")
                                                    st.dataframe(df.head(10))
                                                    st.write(f"Data shape: {df.shape}")
                                                    st.write(f"Columns: {list(df.columns)}")
                                                
                                                # Auto-detect EKG and time columns
                                                if df.shape[1] >= 2:
                                                    # For EKG data: Column 0 = EKG values (mV), Column 1 = Time
                                                    ekg_column = df.columns[0]  # EKG values
                                                    time_column = df.columns[1]  # Time values
                                                    
                                                    # Extract data
                                                    ekg_data = df[ekg_column].values.astype(float)
                                                    time_data_raw = df[time_column].values.astype(float)
                                                    
                                                    # Fix time data conversion - data is sampled at 500 Hz
                                                    sampling_rate = 500
                                                    
                                                    # Check if time data looks like sample indices or actual time
                                                    if time_data_raw.max() > 100000:  # Likely sample indices or large time values
                                                        # Convert to seconds - use correct 500 Hz sampling rate
                                                        time_data = (time_data_raw - time_data_raw.min()) / sampling_rate
                                                    elif time_data_raw.max() > 1000:  # Likely milliseconds
                                                        time_data = (time_data_raw - time_data_raw.min()) / 1000.0
                                                    else:  # Already in seconds or very short recording
                                                        time_data = time_data_raw - time_data_raw.min()
                                                        
                                                    # Ensure time data is monotonically increasing
                                                    if len(time_data) > 1 and time_data[1] < time_data[0]:
                                                        time_data = np.arange(len(ekg_data)) / sampling_rate
                                                    
                                                    # Ensure time data is monotonically increasing
                                                    if len(time_data) > 1 and time_data[1] < time_data[0]:
                                                        time_data = np.arange(len(ekg_data)) / sampling_rate
                                                    

                                                    
                                                    # Calculate metrics using improved peak detection
                                                    birth_year = int(user_data[7][:4]) if len(user_data) > 7 and user_data[7] and user_data[7] != 'N/A' else 1990
                                                    age = 2025 - birth_year
                                                    max_hr = 220 - age  # Simple formula

                                                    
                                                    # Improved heart rate calculation with proper time handling
                                                    hr_result, hr_message = streamlit_heart_rate_calculation(
                                                        ekg_data, 
                                                        time_data_raw,  # Use raw time data - function will handle conversion
                                                        sampling_rate=500
                                                    )

                                                    # Store peaks for visualization - IMPROVED VERSION
                                                    peaks = None
                                                    if hr_result is not None:
                                                        avg_hr = hr_result

                                                        
                                                        # Extract peaks for visualization using the same algorithm
                                                        peaks = extract_peaks_for_visualization(ekg_data, time_data, sampling_rate=500)
                                                        
                                                        if peaks is not None and len(peaks) > 0:
                                                            st.info(f"🎯 Found {len(peaks)} peaks for visualization")
                                                        else:
                                                            st.warning("⚠️ Could not extract peaks for visualization")
                                                                
                                                        # Show diagnostic information
                                                        with st.expander("🔍 Heart Rate Calculation Details"):
                                                            st.write(f"**Calculated HR:** {avg_hr:.1f} bpm")
                                                            st.write(f"**Calculation details:** {hr_message}")
                                                            st.write(f"**Age:** {age} years (estimated)")
                                                            st.write(f"**Max HR (220-age):** {max_hr} bpm")
                                                            st.write(f"**HR as % of max:** {(avg_hr/max_hr)*100:.1f}%")
                                                            st.write(f"**Time range:** {time_data.min():.2f} to {time_data.max():.2f} seconds")
                                                            st.write(f"**EKG signal range:** {ekg_data.min():.2f} to {ekg_data.max():.2f} mV")
                                                            st.write(f"**Signal duration:** {(time_data.max() - time_data.min()):.2f} seconds")
                                                            st.write(f"**Sampling rate:** 500 Hz")
                                                            st.write(f"**Total samples:** {len(ekg_data)}")
                                                            
                                                            if peaks is not None and len(peaks) > 0:
                                                                st.write(f"**Peaks found:** {len(peaks)}")
                                                                # Show first few peak times
                                                                if len(peaks) > 0:
                                                                    peak_times_sample = time_data[peaks[:min(5, len(peaks))]]
                                                                    st.write(f"**First few peak times:** {[f'{t:.2f}s' for t in peak_times_sample]}")
                                                                    
                                                                    # Calculate and show RR intervals
                                                                    if len(peaks) > 1:
                                                                        peak_times_all = time_data[peaks]
                                                                        rr_intervals = np.diff(peak_times_all)
                                                                        st.write(f"**RR intervals (first 5):** {[f'{rr:.3f}s' for rr in rr_intervals[:5]]}")
                                                                        st.write(f"**Avg RR interval:** {np.mean(rr_intervals):.3f}s")
                                                                        st.write(f"**HR from RR:** {60/np.mean(rr_intervals):.1f} bpm")
                                                    else:
                                                        avg_hr = None
                                                        peaks = None
                                                        st.error(f"❌ Heart rate calculation failed: {hr_message}")
                                                        
                                                        # Enhanced debugging information
                                                        with st.expander("🔧 Enhanced Debugging Information"):
                                                            st.write(f"**Error:** {hr_message}")
                                                            st.write(f"**Data shape:** {len(ekg_data)} samples")
                                                            st.write(f"**Time range:** {time_data_raw.min():.0f} to {time_data_raw.max():.0f}")
                                                            st.write(f"**EKG range:** {np.min(ekg_data):.3f} to {np.max(ekg_data):.3f} mV")
                                                            st.write(f"**EKG std:** {np.std(ekg_data):.3f} mV")
                                                            st.write(f"**EKG mean:** {np.mean(ekg_data):.3f} mV")
                                                            
                                                            # Show signal statistics
                                                            ekg_filtered = ekg_data - np.mean(ekg_data)
                                                            st.write(f"**Filtered EKG range:** {np.min(ekg_filtered):.3f} to {np.max(ekg_filtered):.3f} mV")
                                                            st.write(f"**Filtered EKG std:** {np.std(ekg_filtered):.3f} mV")
                                                            
                                                            # Show a simple signal preview
                                                            st.write("**Signal Preview (first 1000 samples):**")
                                                            try:
                                                                import matplotlib.pyplot as plt
                                                                fig, ax = plt.subplots(figsize=(12, 4))
                                                                sample_size = min(1000, len(ekg_data))
                                                                sample_time = time_data[:sample_size] if len(time_data) >= sample_size else time_data
                                                                sample_ekg = ekg_data[:sample_size]
                                                                
                                                                ax.plot(sample_time, sample_ekg, 'b-', linewidth=0.8)
                                                                ax.set_xlabel('Time (s)')
                                                                ax.set_ylabel('Amplitude (mV)')
                                                                ax.set_title('EKG Signal Preview')
                                                                ax.grid(True, alpha=0.3)
                                                                
                                                                # Add threshold line for reference
                                                                signal_abs = np.abs(ekg_filtered[:sample_size])
                                                                threshold = np.percentile(signal_abs, 85)
                                                                ax.axhline(y=threshold, color='r', linestyle='--', alpha=0.7, label=f'Threshold: {threshold:.3f}mV')
                                                                ax.axhline(y=-threshold, color='r', linestyle='--', alpha=0.7)
                                                                ax.legend()
                                                                
                                                                plt.tight_layout()
                                                                st.pyplot(fig)
                                                            except Exception as plot_error:
                                                                st.write(f"Could not generate debug plot: {plot_error}")
                                                    

                                                else:
                                                    st.error("❌ Need at least 2 columns for EKG analysis")
                                                    ekg_data = None
                                                    time_data = None
                                                    avg_hr = None
                                                    max_hr = None
                                                    
                                            except Exception as e:
                                                st.error(f"❌ Error loading file directly: {e}")
                                                import traceback
                                                with st.expander("🔧 Error Details"):
                                                    st.code(traceback.format_exc())
                                                max_hr = None
                                                avg_hr = None
                                                ekg_data = None
                                                time_data = None
                                    
                                        # Display metrics
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

                                        # EKG Visualization using only Plotly
                                        st.markdown("---")
                                        
                                        # Time range selection
                                        st.subheader("⏱️ Zeitbereich auswählen")
                                        col1, col2 = st.columns([3, 1])
                                        
                                        with col1:
                                            if time_data is not None and len(time_data) > 0:
                                                max_duration = float(time_data[-1] - time_data[0])
                                                if max_duration > 0:
                                                    time_range = st.slider(
                                                        "Zeitbereich (Sekunden)",
                                                        min_value=0.0,
                                                        max_value=max_duration,
                                                        value=(0.0, min(10.0, max_duration)),
                                                        step=0.1,
                                                        format="%.1f s"
                                                    )
                                                    st.write(f"Gewählter Bereich: {time_range[0]:.1f} - {time_range[1]:.1f} Sekunden")
                                                else:
                                                    st.error("❌ Invalid time data range")
                                                    time_range = (0.0, 1.0)
                                            else:
                                                time_range = (0.0, 10.0)
                                                st.warning("⚠️ Keine Zeitdaten verfügbar")

                                        with col2:
                                            # Calculate average heart rate in selected time range
                                            if time_data is not None and ekg_data is not None and time_range[0] != time_range[1]:
                                                try:
                                                    mask = (time_data >= time_range[0]) & (time_data <= time_range[1])
                                                    range_ekg_data = ekg_data[mask]
                                                    range_time_data = time_data[mask]
                                                    
                                                    if len(range_ekg_data) > 0:
                                                        if use_ekg_class:
                                                            # Use original method for range calculation
                                                            range_hr = EKG_data.average_hr(
                                                                pd.Series(range_ekg_data),
                                                                sampling_rate=500,
                                                                threshold=360,
                                                                window_size=5,
                                                                min_peak_distance=200
                                                            )
                                                        else:
                                                            # Use fallback method
                                                            range_peaks, _ = find_peaks(range_ekg_data, 
                                                                                    height=np.percentile(range_ekg_data, 75),
                                                                                    distance=int(0.6 * sampling_rate))
                                                            if len(range_peaks) > 1:
                                                                range_duration = range_time_data[-1] - range_time_data[0]
                                                                range_hr = (len(range_peaks) / range_duration) * 60
                                                            else:
                                                                range_hr = None
                                                        
                                                        if range_hr and not pd.isna(range_hr):
                                                            st.metric("💓 Bereichs-HR", f"{range_hr:.1f} bpm")
                                                        else:
                                                            st.warning("⚠️ HR nicht berechenbar")
                                                    else:
                                                        st.warning("⚠️ Keine Daten im Bereich")
                                                except Exception as e:
                                                    st.warning(f"⚠️ Fehler bei Bereichs-HR: {str(e)[:30]}...")


                                        # Display plot - Priority: Original plotly method
                                        st.header("📈 EKG Zeitreihe")
                                        plot_displayed = False  # Initialize the variable here!


                                        # Fallback: matplotlib visualization
                                        if not plot_displayed and ekg_data is not None and time_data is not None and len(time_data) > 0:
                                            try:
                                                # Create matplotlib figure
                                                fig, ax = plt.subplots(figsize=(12, 6))
                                                
                                                # Filter data for selected time range
                                                mask = (time_data >= time_range[0]) & (time_data <= time_range[1])
                                                plot_time = time_data[mask]
                                                plot_ekg = ekg_data[mask]
                                                
                                                # Check if we have data in the selected range
                                                if len(plot_time) > 0 and len(plot_ekg) > 0:
                                                    # Plot EKG signal
                                                    ax.plot(plot_time, plot_ekg, 'b-', linewidth=0.8, label='EKG Signal')
                                                    
                                                    # Plot peaks if they exist
                                                    if peaks is not None and len(peaks) > 0:
                                                        # Find peaks within the time range
                                                        peak_indices_in_range = peaks[(peaks < len(time_data)) & 
                                                                                    (time_data[peaks] >= time_range[0]) & 
                                                                                    (time_data[peaks] <= time_range[1])]
                                                        
                                                        if len(peak_indices_in_range) > 0:
                                                            peak_times = time_data[peak_indices_in_range]
                                                            peak_values = ekg_data[peak_indices_in_range]
                                                            ax.plot(peak_times, peak_values, 'ro', markersize=8, 
                                                                label=f'R-Peaks ({len(peak_indices_in_range)})', alpha=0.8)
                                                            
                                                            # Add heart rate annotation
                                                            if len(peak_indices_in_range) > 1:
                                                                # Calculate HR in this time range
                                                                rr_intervals_range = np.diff(peak_times)
                                                                if len(rr_intervals_range) > 0:
                                                                    avg_rr_range = np.mean(rr_intervals_range)
                                                                    hr_range = 60 / avg_rr_range
                                                                    ax.text(0.02, 0.90, f'Range HR: {hr_range:.1f} bpm', 
                                                                        transform=ax.transAxes, 
                                                                        verticalalignment='top',
                                                                        bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
                                                                                                    
                                                    # Formatting
                                                    ax.set_xlabel('Zeit (s)')
                                                    ax.set_ylabel('Amplitude (mV)')
                                                    ax.set_title(f'EKG Signal - {selected_user_name} - {test_date}')
                                                    ax.grid(True, alpha=0.3)
                                                    ax.legend()
                                                    
                                                    # Add heart rate info to plot
                                                    if avg_hr and not pd.isna(avg_hr):
                                                        ax.text(0.02, 0.98, f'Ø HR: {avg_hr:.1f} bpm', 
                                                            transform=ax.transAxes, 
                                                            verticalalignment='top',
                                                            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
                                                    
                                                    # Tight layout and display
                                                    plt.tight_layout()
                                                    st.pyplot(fig)
                                                    plot_displayed = True
                                                else:
                                                    st.warning(f"⚠️ No data in selected time range {time_range[0]:.1f} - {time_range[1]:.1f} seconds")
                                                    st.info(f"Available time range: {time_data.min():.1f} - {time_data.max():.1f} seconds")
                                                    
                                            except Exception as e:
                                                st.error(f"❌ Matplotlib visualization failed: {e}")
                                                import traceback
                                                with st.expander("🔧 Visualization Error Details"):
                                                    st.code(traceback.format_exc())

                                        if not plot_displayed:
                                            st.error("❌ EKG-Visualisierung nicht verfügbar")
                                            st.info("💡 Überprüfen Sie, ob die EKG-Datei korrekt gespeichert wurde.")
                                        
                                        # Enhanced analysis section
                                        if ekg_data is not None and time_data is not None:
                                            with st.expander("📊 Erweiterte Analyse"):
                                                col1, col2 = st.columns(2)
                                                
                                                # Filter data for current time range
                                                mask = (time_data >= time_range[0]) & (time_data <= time_range[1])
                                                plot_ekg = ekg_data[mask]
                                                plot_time = time_data[mask]
                                                
                                                with col1:
                                                    st.write("**Signal Statistiken:**")
                                                    st.write(f"- Min: {plot_ekg.min():.2f} mV")
                                                    st.write(f"- Max: {plot_ekg.max():.2f} mV")
                                                    st.write(f"- Mittelwert: {plot_ekg.mean():.2f} mV")
                                                    st.write(f"- Standardabweichung: {plot_ekg.std():.2f} mV")
                                                    st.write(f"- Samples: {len(plot_ekg)}")
                                                
                                                with col2:
                                                    if not use_ekg_class and 'peaks' in locals() and peaks is not None:
                                                        # Calculate RR intervals for matplotlib version
                                                        peak_indices_in_range = peaks[(time_data[peaks] >= time_range[0]) & 
                                                                                    (time_data[peaks] <= time_range[1])]
                                                        if len(peak_indices_in_range) > 1:
                                                            rr_intervals = np.diff(time_data[peak_indices_in_range])
                                                            st.write("**Herzrhythmus Analyse:**")
                                                            st.write(f"- RR-Intervall Ø: {rr_intervals.mean():.3f} s")
                                                            st.write(f"- RR-Intervall Std: {rr_intervals.std():.3f} s")
                                                            st.write(f"- HRV (RMSSD): {np.sqrt(np.mean(np.diff(rr_intervals)**2)):.3f} s")
                                                            st.write(f"- Peaks gefunden: {len(peak_indices_in_range)}")
                                                        else:
                                                            st.write("**Herzrhythmus Analyse:**")
                                                            st.write("- Zu wenige Peaks für Analyse")
                                                    elif use_ekg_class:
                                                        st.write("**Herzrhythmus Analyse:**")
                                                        st.write("- Verfügbar über EKG_data Klasse")
                                                        st.write(f"- Durchschnittliche HR: {avg_hr:.1f} bpm" if avg_hr else "- HR nicht verfügbar")
                                                    else:
                                                        st.write("**Herzrhythmus Analyse:**")
                                                        st.write("- Nicht verfügbar")
                                                        
                                    except Exception as e:
                                        st.error(f"❌ Fehler beim Laden des EKG-Tests: {e}")
                                        st.info("💡 Überprüfen Sie, ob die EKG-Datei korrekt gespeichert wurde.")
                                        
                                        # Show traceback in debug mode
                                        with st.expander("🔧 Debug Details"):
                                            import traceback
                                            st.code(traceback.format_exc())
                                            
                            else:
                                st.warning("📭 Keine EKG-Tests für diesen Benutzer verfügbar.")
                                
                                # Option to add EKG test
                                with st.expander("➕ EKG-Test hinzufügen"):
                                    with st.form(f"add_ekg_{selected_user_id}"):
                                        test_date = st.date_input("📅 Testdatum", value=date.today())
                                        ekg_file = st.file_uploader("📁 EKG-Datei hochladen", type=['csv', 'txt', 'dat', 'tsv'])
                                        
                                        if st.form_submit_button("📤 EKG-Test hinzufügen"):
                                            if ekg_file is not None:
                                                # Validate file extension
                                                allowed_extensions = ['.csv', '.txt', '.dat', '.tsv']
                                                uploaded_file_extension = os.path.splitext(ekg_file.name)[1].lower()
                                                
                                                if uploaded_file_extension not in allowed_extensions:
                                                    st.error(f"❌ Unsupported file type: {uploaded_file_extension}")
                                                    st.info("Supported formats: .csv, .txt, .dat, .tsv")
                                                else:
                                                    try:
                                                        # Create EKG data directory
                                                        ekg_dir = "data/ekg_data"
                                                        os.makedirs(ekg_dir, exist_ok=True)
                                                        
                                                        # Save file with proper extension handling
                                                        timestamp = int(time.time())
                                                        # Clean filename to avoid issues
                                                        clean_filename = "".join(c for c in ekg_file.name if c.isalnum() or c in '._-')
                                                        filename = f"ekg_{selected_user_id}_{timestamp}_{clean_filename}"
                                                        file_path = os.path.join(ekg_dir, filename)
                                                        
                                                        # Save the uploaded file
                                                        with open(file_path, "wb") as f:
                                                            f.write(ekg_file.getbuffer())
                                                        
                                                        # Verify file was saved and has content
                                                        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
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
                                                            st.info(f"📁 Datei gespeichert: {filename}")
                                                            st.rerun()
                                                        else:
                                                            st.error("❌ Fehler beim Speichern der Datei")
                                                            
                                                    except Exception as e:
                                                        st.error(f"❌ Fehler beim Hinzufügen des EKG-Tests: {e}")
                                                        # Clean up file if it was partially created
                                                        if 'file_path' in locals() and os.path.exists(file_path):
                                                            try:
                                                                os.remove(file_path)
                                                            except:
                                                                pass
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
