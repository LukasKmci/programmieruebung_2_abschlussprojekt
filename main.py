# main.py
import streamlit as st
from person import Person
from ekg_data import EKG_data
import os

# Seitenkonfiguration
st.set_page_config(
    page_title="EKG Analyse Dashboard", 
    layout="wide", 
    initial_sidebar_state="expanded",
    page_icon="🫀"
)

# Header
st.title("🫀 EKG Analyse Dashboard")
st.markdown("---")

# Sidebar für Hauptnavigation
with st.sidebar:
    st.header("📋 Navigation")
    
    # Personen laden
    persons_data = Person.load_person_data()
    person_names = Person.get_person_list(persons_data)
    
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

# Hauptinhalt
if selected_name:
    person = Person.find_person_data_by_name(selected_name)
    
    # Personeninfo-Sektion
    st.header("👤 Personeninformationen")
    
    col1, col2, col3 = st.columns([1, 2, 2])
    
    with col1:
        # Bild anzeigen
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
            st.error("❌ Keine EKG-Daten verfügbar")

    # EKG-Analyse-Sektion
    if ekg_tests and selected_ekg_id:
        st.markdown("---")
        st.header("📈 EKG-Analyse")
        
        ekg_obj = EKG_data.load_by_id(int(selected_ekg_id), persons_data)
        
        # Kennzahlen in Spalten
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            hr_info = ekg_obj.calc_max_heart_rate(ekg_obj.birth_year, ekg_obj.gender)
            st.metric("🫀 Max HR", f"{hr_info['max_hr']} bpm")
        
        with col2:
            st.metric("📅 Testdatum", ekg_obj.date)
        
        with col3:
            ekg_duration_ms = ekg_obj.df["time in ms"].max() - ekg_obj.df["time in ms"].min()
            ekg_duration_seconds = round(ekg_duration_ms / 1000)
            st.metric("⏱️ Dauer", f"{ekg_duration_seconds/60:.0f} min")
        
        with col4:
            st.metric("📊 Datenpunkte", f"{len(ekg_obj.df):,}")

        # Plot-Einstellungen
        st.markdown("---")
        st.header("⚙️ Plot-Einstellungen")
        
        # Zwei Spalten für Einstellungen
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Zeitbereich-Auswahl
            st.subheader("🕐 Zeitbereich auswählen")
            
            time_data_seconds = (ekg_obj.df["time in ms"] - ekg_obj.df["time in ms"].min()) / 1000
            max_duration = time_data_seconds.max()
            
            time_range = st.slider(
                "Zeitbereich (Sekunden)",
                min_value=0.0,
                max_value=max_duration,
                value=(0.0, min(10.0, max_duration)),
                step=0.1,
                format="%.1f s",
                help="Wählen Sie den Zeitbereich für die EKG-Darstellung"
            )
            
            st.info(f"📍 Gewählter Bereich: {time_range[0]:.1f} - {time_range[1]:.1f} Sekunden")
        
        with col2:
            st.subheader("🔧 Erweiterte Einstellungen")
            
            # Zusätzliche Plot-Parameter
            threshold = st.number_input("Schwellenwert", value=360, min_value=0, max_value=1000)
            min_peak_distance = st.number_input("Min. Peak-Abstand", value=200, min_value=1, max_value=500)
            
            # Info über gewählten Bereich
            duration_selected = time_range[1] - time_range[0]
            st.metric("⏰ Ausgewählte Dauer", f"{duration_selected:.1f} s")

        # EKG-Plot
        st.markdown("---")
        st.header("📊 EKG-Visualisierung")
        
        try:
            with st.spinner("🔄 Lade EKG-Daten..."):
                fig = ekg_obj.plot_time_series(
                    threshold=threshold,
                    min_peak_distance=min_peak_distance,
                    range_start=time_range[0],
                    range_end=time_range[1]
                )
                st.plotly_chart(fig, use_container_width=True, key=f"plot_{selected_ekg_id}")
                
                # Erfolgsbestätigung
                st.success("✅ EKG erfolgreich dargestellt")
                
        except Exception as e:
            st.error(f"❌ Fehler beim Erstellen des Plots: {e}")
            st.info("💡 Versuchen Sie einen anderen Zeitbereich oder andere Parameter")

    elif not ekg_tests:
        st.warning("⚠️ Für diese Person sind keine EKG-Daten verfügbar.")
    
else:
    # Willkommensseite
    st.header("🎯 Willkommen im EKG-Analyse Dashboard!")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### Wählen Sie in der Seitenleiste eine Versuchsperson aus, um zu beginnen.")
        
        st.info("**📋 Verfügbare Funktionen:**")
        st.write("🫀 Maximale Herzfrequenz berechnen")
        st.write("📊 EKG-Daten visualisieren") 
        st.write("⏱️ Flexible Zeitbereich-Auswahl")
        st.write("📈 Interaktive Plots")

# Footer
st.markdown("---")
st.caption("EKG Analyse Dashboard | Version 1.0 | 🫀 Für medizinische Forschung")