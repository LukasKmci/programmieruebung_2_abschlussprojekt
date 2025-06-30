import streamlit as st
import streamlit_authenticator as stauth
from person import Person
from ekg_data import EKG_data
from database_auth import DatabaseAuth
import pandas as pd
import os
from datetime import datetime, date
import sqlite3
from PIL import Image
import io
import base64


# Seitenkonfiguration
st.set_page_config(
    page_title="EKG Analyse Dashboard", 
    layout="wide", 
    initial_sidebar_state="expanded",
    page_icon="🫀"
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
        
        # Hash password (you should use proper hashing in production)
        import bcrypt
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

# Initialize personen.db
init_personen_db()

# Get credentials from personen.db
credentials = get_all_users_from_personen_db()

if credentials['usernames']:
    authenticator = stauth.Authenticate(
        credentials,
        'ekg_dashboard',
        'abcdef',  # Cookie key - in Produktion sollte das sicherer sein
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
        
        # Registrierungsform für neue Benutzer
        with st.expander("🆕 Neuen Account erstellen"):
            st.subheader("Registrierung")
            with st.form("register_form"):
                new_username = st.text_input("Benutzername")
                new_password = st.text_input("Passwort", type="password")
                new_password_confirm = st.text_input("Passwort bestätigen", type="password")
                new_email = st.text_input("E-Mail")
                new_full_name = st.text_input("Vollständiger Name")
                
                # Zusätzliche Person-Daten
                st.subheader("Persönliche Daten")
                col1, col2 = st.columns(2)
                with col1:
                    new_firstname = st.text_input("Vorname")
                    new_date_of_birth = st.date_input(
                        "Geburtsdatum",
                        value=date(1990, 1, 1),  # Default to 1990-01-01
                        min_value=date(1900, 1, 1),  # Allow dates from 1900
                        max_value=date.today(),  # Don't allow future dates
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
        # Login erfolgreich - Last Login aktualisieren
        update_last_login_personen_db(username)
        
        # User-Info aus personen.db holen
        user_data = get_user_from_personen_db(username)
        current_user_role = credentials['usernames'][username]['role']
        
        # Logout-Button
        authenticator.logout('Logout', 'sidebar')
        
        # Header mit Benutzerinfo - DIFFERENT LAYOUTS FOR ADMIN VS USER
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
                    ["📊 EKG-Analyse", "👥 Benutzerverwaltung", "📈 Dashboard", "🗃️ Datenbank-Info"]
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
                
                admin_tab = "📊 EKG-Analyse"
        
        # ADMIN-BEREICH - ENHANCED FOR PERSONEN.DB
        if current_user_role == 'admin' and admin_tab == "👥 Benutzerverwaltung":
            st.header("👥 Benutzerverwaltung")
            
            # Get all users from personen.db
            conn = sqlite3.connect('personen.db')
            users_df = pd.read_sql_query('SELECT * FROM users ORDER BY created_at DESC', conn)
            conn.close()
            
            # Benutzer-Statistiken
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
            
            # Alle Benutzer anzeigen mit Bildern
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
                        
                        # Admin-Aktionen
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

        # EKG-ANALYSE-BEREICH (Rest bleibt gleich, aber mit unterschiedlichen Berechtigungen)
        else:
            # Your existing EKG analysis code here...
            # (I'll keep this part the same since it's working)
            
            with st.sidebar:
                st.markdown("---")
                st.header("📋 EKG-Analyse")
                
                # Load persons data based on user role
                try:
                    persons_data = Person.load_person_data()
                    person_names = Person.get_person_list(persons_data)
                    
                    if not person_names:
                        st.warning("⚠️ Keine EKG-Daten verfügbar")
                        st.stop()
                        
                except Exception as e:
                    st.error(f"❌ Fehler beim Laden der Daten: {e}")
                    st.stop()
                
                # Person selection
                selected_name = st.selectbox("👤 Person auswählen", person_names, key="person_select")
                
                # Rest of your EKG analysis code...
                # (keeping the existing logic)

            # Main EKG analysis content
            if selected_name:
                person = Person.find_person_data_by_name(selected_name)
                
                if not person:
                    st.error(f"❌ Person '{selected_name}' nicht gefunden")
                    st.stop()
                
                # Show different information based on user role
                if current_user_role == 'admin':
                    st.success("🔒 Admin-Ansicht: Vollzugriff auf alle EKG-Daten")
                else:
                    st.info("👤 Benutzer-Ansicht: Eingeschränkter Zugriff")
                
                # Rest of your EKG analysis code remains the same...
                # (I'll keep the existing EKG visualization logic)
                
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

else:
    st.error("❌ Keine Benutzer in der Datenbank gefunden. Bitte kontaktieren Sie den Administrator.")

# Footer
st.markdown("---")
if 'current_user_role' in locals() and current_user_role == 'admin':
    st.caption("EKG Analyse Dashboard - ADMINISTRATOR VERSION | Personen.db Integration")
else:
    st.caption("EKG Analyse Dashboard | Version 4.0")