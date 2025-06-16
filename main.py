# main.py - Mit SQLite Login-Integration
import streamlit as st
import streamlit_authenticator as stauth
from person import Person
from ekg_data import EKG_data
import os
from database_auth import DatabaseAuth  # Neue Import
import re

# =============================================================================
# SEITENKONFIGURATION
# =============================================================================

st.set_page_config(
    page_title="EKG Analyse Dashboard", 
    layout="wide", 
    initial_sidebar_state="expanded",
    page_icon="🫀"
)

# =============================================================================
# DATENBANK-AUTHENTICATION SETUP
# =============================================================================

# Datenbank-Auth initialisieren
@st.cache_resource
def init_auth():
    return DatabaseAuth("ekg_users.db")  # Deine SQLite-Datei

db_auth = init_auth()

# User-Daten aus Datenbank laden
credentials = db_auth.get_all_users()

# Cookie-Konfiguration
cookie_config = {
    'expiry_days': 30,
    'key': 'ekg_dashboard_secret_key_2024',  # Ändere das!
    'name': 'ekg_login_cookie'
}

# Authenticator erstellen
authenticator = stauth.Authenticate(
    credentials,
    cookie_config['name'],
    cookie_config['key'],
    cookie_config['expiry_days']
)

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def validate_email(email):
    """E-Mail Validierung"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Passwort-Stärke prüfen"""
    if len(password) < 6:
        return False, "Passwort muss mindestens 6 Zeichen haben"
    if not re.search(r'[A-Za-z]', password):
        return False, "Passwort muss mindestens einen Buchstaben enthalten"
    if not re.search(r'\d', password):
        return False, "Passwort muss mindestens eine Zahl enthalten"
    return True, "Passwort ist stark genug"

# =============================================================================
# REGISTRIERUNGS-FORMULAR
# =============================================================================

def show_registration_form():
    """Zeigt das Registrierungsformular"""
    st.header("👤 Neuen Account erstellen")
    
    with st.form("registration_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            new_username = st.text_input("Benutzername*", help="Eindeutiger Benutzername")
            new_email = st.text_input("E-Mail*", help="Gültige E-Mail-Adresse")
            new_password = st.text_input("Passwort*", type="password", help="Mind. 6 Zeichen, Buchstaben + Zahlen")
        
        with col2:
            new_full_name = st.text_input("Vollständiger Name*", help="Vor- und Nachname")
            confirm_password = st.text_input("Passwort bestätigen*", type="password")
            new_role = st.selectbox("Rolle", ["user", "admin"], help="user = Patient, admin = Arzt/Sportmediziner")
        
        submitted = st.form_submit_button("👤 Account erstellen")
        
        if submitted:
            # Validierung
            errors = []
            
            if not new_username or len(new_username) < 3:
                errors.append("Benutzername muss mindestens 3 Zeichen haben")
            
            if not new_email or not validate_email(new_email):
                errors.append("Gültige E-Mail-Adresse erforderlich")
            
            if not new_full_name or len(new_full_name) < 2:
                errors.append("Vollständiger Name erforderlich")
            
            password_valid, password_msg = validate_password(new_password)
            if not password_valid:
                errors.append(password_msg)
            
            if new_password != confirm_password:
                errors.append("Passwörter stimmen nicht überein")
            
            # Fehler anzeigen oder User erstellen
            if errors:
                for error in errors:
                    st.error(f"❌ {error}")
            else:
                success, message = db_auth.create_user(
                    new_username, new_password, new_email, new_full_name, new_role
                )
                
                if success:
                    st.success(f"✅ {message}")
                    st.info("🔄 Seite wird neu geladen...")
                    st.rerun()
                else:
                    st.error(f"❌ {message}")

# =============================================================================
# ADMIN USER MANAGEMENT
# =============================================================================

def show_user_management():
    """Admin User Management Interface"""
    st.header("👥 Benutzerverwaltung")
    
    # User-Statistiken
    stats = db_auth.get_user_stats()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("👤 Aktive Benutzer", stats['total_users'])
    with col2:
        st.metric("👨‍⚕️ Admins", stats['by_role'].get('admin', 0))
    with col3:
        st.metric("🧑‍💼 Patienten", stats['by_role'].get('user', 0))
    
    st.markdown("---")
    
    # Alle User anzeigen
    users_df = db_auth.get_users_for_admin()
    
    if not users_df.empty:
        st.subheader("📋 Alle registrierten Benutzer")
        
        # User-Tabelle mit Formatierung
        display_df = users_df.copy()
        display_df['created_at'] = pd.to_datetime(display_df['created_at']).dt.strftime('%d.%m.%Y %H:%M')
        display_df['last_login'] = pd.to_datetime(display_df['last_login']).dt.strftime('%d.%m.%Y %H:%M')
        display_df['Status'] = display_df['is_active'].apply(lambda x: '✅ Aktiv' if x else '❌ Inaktiv')
        
        # Spalten umbenennen
        display_df = display_df.rename(columns={
            'username': 'Benutzername',
            'email': 'E-Mail',
            'full_name': 'Name',
            'role': 'Rolle',
            'created_at': 'Erstellt am',
            'last_login': 'Letzter Login'
        })
        
        st.dataframe(
            display_df[['Benutzername', 'Name', 'E-Mail', 'Rolle', 'Status', 'Erstellt am', 'Letzter Login']],
            use_container_width=True
        )
        
        # User löschen
        st.markdown("---")
        st.subheader("🗑️ Benutzer löschen")
        
        active_users = users_df[users_df['is_active'] == True]['username'].tolist()
        if 'admin' in active_users:
            active_users.remove('admin')  # Admin kann sich nicht selbst löschen
        
        if active_users:
            user_to_delete = st.selectbox("Benutzer zum Löschen auswählen:", [''] + active_users)
            
            if user_to_delete and st.button(f"🗑️ {user_to_delete} löschen", type="secondary"):
                success, message = db_auth.delete_user(user_to_delete)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
        else:
            st.info("Keine Benutzer zum Löschen verfügbar")

    # Enhanced registration form - Add this to your main.py

def show_enhanced_registration_form():
    """Zeigt das erweiterte Registrierungsformular mit Person-Daten"""
    st.header("👤 Neuen Account erstellen")
    
    with st.form("registration_form"):
        st.subheader("🔐 Login-Daten")
        col1, col2 = st.columns(2)
        
        with col1:
            new_username = st.text_input("Benutzername*", help="Eindeutiger Benutzername")
            new_password = st.text_input("Passwort*", type="password", help="Mind. 6 Zeichen, Buchstaben + Zahlen")
            new_email = st.text_input("E-Mail*", help="Gültige E-Mail-Adresse")
        
        with col2:
            confirm_password = st.text_input("Passwort bestätigen*", type="password")
            new_role = st.selectbox("Rolle", ["user", "admin"], help="user = Patient, admin = Arzt/Sportmediziner")
        
        st.markdown("---")
        st.subheader("👤 Persönliche Daten")
        
        col3, col4 = st.columns(2)
        
        with col3:
            firstname = st.text_input("Vorname*")
            lastname = st.text_input("Nachname*") 
            date_of_birth = st.date_input(
                "Geburtsdatum*", 
                value=None,
                min_value=datetime(1900, 1, 1).date(),
                max_value=datetime.now().date(),
                help="Für Altersberechnung und medizinische Auswertung"
            )
        
        with col4:
            gender = st.selectbox(
                "Geschlecht*", 
                ["", "male", "female", "other"],
                format_func=lambda x: {"": "Bitte wählen", "male": "Männlich", "female": "Weiblich", "other": "Divers"}[x]
            )
            height_cm = st.number_input("Körpergröße (cm)", min_value=100, max_value=250, value=None, step=1)
            weight_kg = st.number_input("Gewicht (kg)", min_value=20.0, max_value=300.0, value=None, step=0.1)
        
        st.markdown("---")
        st.subheader("📷 Profilbild (optional)")
        
        uploaded_file = st.file_uploader(
            "Profilbild hochladen", 
            type=['png', 'jpg', 'jpeg'],
            help="Optional: Laden Sie ein Profilbild hoch"
        )
        
        # Zusätzliche Felder für medizinische Daten
        with st.expander("🏥 Zusätzliche medizinische Informationen (optional)"):
            medical_notes = st.text_area(
                "Medizinische Notizen",
                help="Allergien, Vorerkrankungen, Medikamente etc."
            )
            emergency_contact = st.text_input(
                "Notfallkontakt",
                help="Name und Telefonnummer"
            )
        
        submitted = st.form_submit_button("👤 Account erstellen", type="primary")
        
        if submitted:
            # Validierung
            errors = []
            
            # Login-Daten Validierung
            if not new_username or len(new_username) < 3:
                errors.append("Benutzername muss mindestens 3 Zeichen haben")
            
            if not new_email or not validate_email(new_email):
                errors.append("Gültige E-Mail-Adresse erforderlich")
            
            password_valid, password_msg = validate_password(new_password)
            if not password_valid:
                errors.append(password_msg)
            
            if new_password != confirm_password:
                errors.append("Passwörter stimmen nicht überein")
            
            # Person-Daten Validierung
            if not firstname or len(firstname) < 2:
                errors.append("Vorname ist erforderlich")
            
            if not lastname or len(lastname) < 2:
                errors.append("Nachname ist erforderlich")
            
            if not date_of_birth:
                errors.append("Geburtsdatum ist erforderlich")
            
            if not gender:
                errors.append("Geschlecht muss ausgewählt werden")
            
            # Alter prüfen (mindestens 12 Jahre)
            if date_of_birth:
                age = (datetime.now().date() - date_of_birth).days / 365.25
                if age < 12:
                    errors.append("Mindestalter: 12 Jahre")
                elif age > 120:
                    errors.append("Bitte prüfen Sie das Geburtsdatum")
            
            # Fehler anzeigen oder User erstellen
            if errors:
                for error in errors:
                    st.error(f"❌ {error}")
            else:
                # Profilbild speichern falls hochgeladen
                picture_path = None
                if uploaded_file is not None:
                    # Ordner erstellen falls nicht vorhanden
                    os.makedirs("data/pictures", exist_ok=True)
                    
                    # Dateiname generieren
                    file_extension = uploaded_file.name.split('.')[-1]
                    picture_filename = f"{new_username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file_extension}"
                    picture_path = f"data/pictures/{picture_filename}"
                    
                    # Datei speichern
                    with open(picture_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                
                # Full name zusammensetzen
                full_name = f"{firstname} {lastname}"
                
                # User in Datenbank erstellen
                success, message = db_auth.create_user(
                    username=new_username,
                    password=new_password,
                    email=new_email,
                    full_name=full_name,
                    role=new_role,
                    firstname=firstname,
                    lastname=lastname,
                    date_of_birth=date_of_birth.strftime('%Y-%m-%d'),
                    gender=gender,
                    height_cm=height_cm,
                    weight_kg=weight_kg
                )
                
                if success:
                    # Profilbild-Pfad aktualisieren falls vorhanden
                    if picture_path:
                        db_auth.update_user_picture(new_username, picture_path)
                    
                    st.success(f"✅ {message}")
                    st.balloons()
                    
                    # Erfolgreiche Registrierung Info
                    st.info("🎉 **Registrierung erfolgreich!**\n\nSie können sich jetzt mit Ihren Login-Daten anmelden.")
                    
                    # Optional: Zusätzliche medizinische Daten speichern
                    if medical_notes or emergency_contact:
                        # Hier könntest du eine separate Tabelle für medizinische Daten erstellen
                        pass
                    
                    st.info("🔄 Seite wird neu geladen...")
                    st.rerun()
                else:
                    st.error(f"❌ {message}")

def show_enhanced_user_management():
    """Erweiterte Admin User Management Interface"""
    st.header("👥 Erweiterte Benutzerverwaltung")
    
    # User-Statistiken
    stats = db_auth.get_user_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("👤 Aktive Benutzer", stats['total_users'])
    with col2:
        st.metric("👨‍⚕️ Admins", stats['by_role'].get('admin', 0))
    with col3:
        st.metric("🧑‍💼 Patienten", stats['by_role'].get('user', 0))
    with col4:
        st.metric("📊 EKG-Tests", stats.get('total_ekg_tests', 0))
    
    st.markdown("---")
    
    # Detaillierte User-Tabelle
    users_df = db_auth.get_users_for_admin()
    
    if not users_df.empty:
        st.subheader("📋 Alle registrierten Benutzer")
        
        # Formatierung der Anzeige
        display_df = users_df.copy()
        
        # Datum formatieren
        display_df['created_at'] = pd.to_datetime(display_df['created_at']).dt.strftime('%d.%m.%Y')
        display_df['last_login'] = pd.to_datetime(display_df['last_login']).dt.strftime('%d.%m.%Y %H:%M')
        
        # Status und Geschlecht formatieren
        display_df['Status'] = display_df['is_active'].apply(lambda x: '✅ Aktiv' if x else '❌ Inaktiv')
        display_df['Geschlecht'] = display_df['gender'].map({
            'male': '👨 Männlich', 
            'female': '👩 Weiblich', 
            'other': '🤷 Divers'
        }).fillna('❓ Unbekannt')
        
        # Alter berechnen
        def calculate_age(birth_date):
            if pd.isna(birth_date):
                return "❓"
            try:
                birth = pd.to_datetime(birth_date).date()
                today = datetime.now().date()
                age = int((today - birth).days / 365.25)
                return f"{age} Jahre"
            except:
                return "❓"
        
        display_df['Alter'] = display_df['date_of_birth'].apply(calculate_age)
        
        # Spalten umbenennen und auswählen
        display_df = display_df.rename(columns={
            'username': 'Benutzername',
            'full_name': 'Name',
            'email': 'E-Mail',
            'role': 'Rolle',
            'created_at': 'Registriert',
            'last_login': 'Letzter Login',
            'ekg_count': 'EKG-Tests'
        })
        
        # Anzeigen
        st.dataframe(
            display_df[[
                'Benutzername', 'Name', 'E-Mail', 'Rolle', 'Status', 
                'Geschlecht', 'Alter', 'EKG-Tests', 'Registriert', 'Letzter Login'
            ]],
            use_container_width=True
        )
        
        # User-Details anzeigen
        st.markdown("---")
        st.subheader("🔍 Benutzer-Details")
        
        selected_user = st.selectbox(
            "Benutzer für Details auswählen:",
            [''] + users_df['username'].tolist()
        )
        
        if selected_user:
            user_data = users_df[users_df['username'] == selected_user].iloc[0]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**👤 Name:** {user_data['full_name']}")
                st.write(f"**📧 E-Mail:** {user_data['email']}")
                st.write(f"**🎂 Geburtsdatum:** {user_data['date_of_birth'] or 'Nicht angegeben'}")
                st.write(f"**⚧ Geschlecht:** {user_data['gender'] or 'Nicht angegeben'}")
            
            with col2:
                st.write(f"**🏥 Rolle:** {user_data['role']}")
                st.write(f"**📊 EKG-Tests:** {user_data['ekg_count']}")
                st.write(f"**📅 Registriert:** {user_data['created_at']}")
                st.write(f"**🔄 Letzter Login:** {user_data['last_login'] or 'Nie'}")
        
        # User löschen
        st.markdown("---")
        st.subheader("🗑️ Benutzer löschen")
        
        active_users = users_df[users_df['is_active'] == True]['username'].tolist()
        if 'admin' in active_users:
            active_users.remove('admin')
        
        if active_users:
            user_to_delete = st.selectbox("Benutzer zum Löschen auswählen:", [''] + active_users)
            
            if user_to_delete:
                user_info = users_df[users_df['username'] == user_to_delete].iloc[0]
                st.warning(f"⚠️ **Achtung:** Benutzer '{user_info['full_name']}' und alle zugehörigen EKG-Daten werden gelöscht!")
                
                if st.button(f"🗑️ {user_to_delete} endgültig löschen", type="secondary"):
                    success, message = db_auth.delete_user(user_to_delete)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
        else:
            st.info("Keine Benutzer zum Löschen verfügbar")

# =============================================================================
# MAIN LOGIN LOGIC
# =============================================================================

# Login/Registration Tabs
if 'authentication_status' not in st.session_state:
    st.session_state['authentication_status'] = None

# Login-Widget anzeigen
name, authentication_status, username = authenticator.login('🔐 Anmelden', 'main')

# Tab-System für Login/Registrierung
if authentication_status == None:
    st.markdown("---")
    tab1, tab2 = st.tabs(["🔐 Anmelden", "👤 Registrieren"])
    
    with tab1:
        st.info("**Demo-Zugänge:**\n\n"
                "👨‍⚕️ **Admin:** admin / admin123\n\n"
                "🧑‍💼 **Patient:** (Erstelle einen neuen Account)")
    
    with tab2:
        show_registration_form()
    
    st.stop()

elif authentication_status == False:
    st.error('❌ Benutzername/Passwort ist falsch')
    st.stop()

# =============================================================================
# HAUPT-DASHBOARD (nach erfolgreichem Login)
# =============================================================================

# Letzten Login aktualisieren
db_auth.update_last_login(username)

# User-Daten neu laden (für frische Rolle etc.)
fresh_credentials = db_auth.get_all_users()
user_role = fresh_credentials['usernames'][username]['role']

# Header mit Logout
col1, col2 = st.columns([4, 1])
with col1:
    st.title("🫀 EKG Analyse Dashboard")
    role_emoji = "👨‍⚕️" if user_role == 'admin' else "🧑‍💼"
    st.success(f"✅ Eingeloggt als: **{name}** {role_emoji}")
with col2:
    if st.button("🚪 Logout"):
        authenticator.logout('Logout', 'main')

st.markdown("---")

# =============================================================================
# ADMIN-FUNKTIONEN
# =============================================================================

if user_role == 'admin':
    st.info("👨‍⚕️ **Admin-Bereich** - Sie haben Vollzugriff auf alle Patienten und Funktionen")
    
    with st.sidebar:
        st.header("🔧 Admin-Funktionen")
        
        admin_action = st.radio(
            "Admin-Bereiche:",
            ["📊 EKG-Analyse", "👥 Benutzerverwaltung", "🗑️ Daten-Management"],
            key="admin_nav"
        )
        
        st.markdown("---")

    if admin_action == "👥 Benutzerverwaltung":
        show_user_management()
        st.stop()
    
    elif admin_action == "🗑️ Daten-Management":
        st.header("🗑️ Daten-Management")
        st.warning("⚠️ Diese Funktionen würden echte Daten löschen!")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ EKG-Datensatz löschen"):
                st.error("Lösch-Funktion für EKG-Daten würde hier implementiert")
        with col2:
            if st.button("🗑️ Patient entfernen"):
                st.error("Patient-Lösch-Funktion würde hier implementiert")
        st.stop()

# =============================================================================
# EKG-ANALYSE BEREICH (Original Code mit Berechtigungen)
# =============================================================================

# Sidebar für Navigation
with st.sidebar:
    st.header("📋 Navigation")
    
    # Personen laden
    persons_data = Person.load_person_data()
    
    if user_role == 'admin':
        # Admin sieht alle Personen
        person_names = Person.get_person_list(persons_data)
        st.success("🔓 Admin: Alle Daten sichtbar")
    else:
        # User sieht nur eigene Daten
        person_names = Person.get_person_list(persons_data)
        st.info(f"🔒 Gefiltert für: {name}")
        # TODO: Hier würdest du die Filterung implementieren
        # person_names = filter_persons_by_user(person_names, username)
    
    # Auswahl der Versuchsperson
    selected_name = st.selectbox("👤 Versuchsperson auswählen", person_names, key="person_select")
    
    if selected_name:
        person = Person.find_person_data_by_name(selected_name)
        
        # EKG-Datensatz auswählen
        ekg_tests = person.get("ekg_tests", [])
        if ekg_tests:
            st.markdown("---")
            ekg_ids = [str(test["id"]) for test in ekg_tests]
            selected_ekg_id = st.selectbox("📊 EKG-Datensatz wählen", ekg_ids, key="ekg_select")

# =============================================================================
# HAUPT-EKG-ANALYSE (dein ursprünglicher Code)
# =============================================================================

# Der Rest ist identisch zu deinem ursprünglichen Code...
if selected_name:
    person = Person.find_person_data_by_name(selected_name)
    
    # Personeninfo-Sektion
    st.header("👤 Personeninformationen")
    
    col1, col2, col3 = st.columns([1, 2, 2])
    
    with col1:
        picture_path = person["picture_path"]
        if os.path.exists(picture_path):
            st.image(picture_path, caption=selected_name, width=200)
        else:
            st.warning("📷 Kein Bild verfügbar")
    
    with col2:
        st.subheader("📝 Persönliche Daten")
        st.write(f"**Name:** {selected_name}")
        st.write(f"**Geburtsjahr:** {person['date_of_birth']}")
        st.write(f"**Verfügbare EKG-Tests:** {len(ekg_tests)}")
    
    with col3:
        if ekg_tests:
            st.success(f"✅ {len(ekg_tests)} EKG-Datensatz(e) verfügbar")
        else:
            st.error("Keine EKG-Daten verfügbar")

    # EKG-Analyse (dein ursprünglicher Code bleibt hier...)
    if ekg_tests and selected_ekg_id:
        st.markdown("---")
        st.header("📈 EKG-Analyse")
        
        ekg_obj = EKG_data.load_by_id(int(selected_ekg_id), persons_data)
        
        # [Hier würde der Rest deines EKG-Analyse Codes stehen...]
        # Ich kürze das hier ab, aber du kopierst einfach den Rest von deinem ursprünglichen Code
        
        st.info("📊 EKG-Analyse läuft... (hier würde dein ursprünglicher Plot-Code stehen)")

else:
    # Willkommensseite
    st.header("🎯 Willkommen im EKG-Analyse Dashboard!")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### Wählen Sie in der Seitenleiste eine Versuchsperson aus, um zu beginnen.")
        
        st.info("**📋 Verfügbare Funktionen:**")
        if user_role == 'admin':
            st.write("👨‍⚕️ Vollzugriff auf alle Patienten")
            st.write("👥 Benutzerverwaltung")
            st.write("🗑️ Daten-Management")
        st.write("🫀 Maximale Herzfrequenz berechnen")
        st.write("💓 Durchschnittliche Herzfrequenz anzeigen")
        st.write("📊 EKG-Daten visualisieren")

# Footer
st.markdown("---")
st.caption("EKG Analyse Dashboard | Version 2.0 mit SQLite Login | Lukas Köhler | Simon Krainer")