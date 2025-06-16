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
    try:
        persons_data = Person.load_person_data()
        person_names = Person.get_person_list(persons_data)
        
        if not person_names:
            st.warning("⚠️ Keine Personen in der Datenbank gefunden")
            st.stop()
            
    except Exception as e:
        st.error(f"❌ Fehler beim Laden der Personendaten: {e}")
        st.stop()
    
    # Auswahl der Versuchsperson
    selected_name = st.selectbox("👤 Versuchsperson auswählen", person_names, key="person_select")
    
    selected_ekg_id = None
    if selected_name:
        person = Person.find_person_data_by_name(selected_name)
        
        if person:
            # EKG-Datensatz auswählen
            ekg_tests = person.get("ekg_tests", [])
            if ekg_tests:
                st.markdown("---")
                ekg_options = [f"Test {test['id']} ({test['date']})" for test in ekg_tests]
                ekg_ids = [str(test["id"]) for test in ekg_tests]
                
                selected_index = st.selectbox(
                    "📊 EKG-Datensatz wählen", 
                    range(len(ekg_options)),
                    format_func=lambda x: ekg_options[x],
                    key="ekg_select"
                )
                selected_ekg_id = ekg_ids[selected_index]

# Hauptinhalt
if selected_name:
    person = Person.find_person_data_by_name(selected_name)
    
    if not person:
        st.error(f"❌ Person '{selected_name}' nicht gefunden")
        st.stop()
    
    # Personeninfo-Sektion
    st.header("👤 Personeninformationen")
    
    col1, col2 = st.columns([2, 2])
    
    with col1:
        # Bild anzeigen
        picture_path = person.get("picture_path", "")
        if picture_path and os.path.exists(picture_path):
            try:
                st.image(picture_path, caption=selected_name, width=200)
            except Exception as e:
                st.warning(f"📷 Fehler beim Laden des Bildes: {e}")
        else:
            st.info("📷 Kein Bild verfügbar")
    
    with col2:
        st.subheader("📝 Persönliche Daten")
        st.write(f"**Name:** {selected_name}")
        st.write(f"**Geburtsjahr:** {person.get('date_of_birth', 'Unbekannt')}")
        st.write(f"**Geschlecht:** {person.get('gender', 'Unbekannt')}")
        ekg_count = Person.get_available_ekg_count(person)
        st.write(f"**Verfügbare EKG-Tests:** {ekg_count}")


    # EKG-Analyse-Sektion
    if ekg_tests and selected_ekg_id:
        st.markdown("---")
        st.header("📊 EKG-Kennzahlen")
        
        try:
            with st.spinner("🔄 Lade EKG-Daten..."):
                ekg_obj = EKG_data.load_by_id(int(selected_ekg_id), persons_data)
        except Exception as e:
            st.error(f"❌ Fehler beim Laden der EKG-Daten: {e}")
            st.stop()
        
        # Kennzahlen in Spalten
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            try:
                hr_info = ekg_obj.calc_max_heart_rate(ekg_obj.birth_year, ekg_obj.gender)
                st.metric("🫀 Max HR", f"{hr_info['max_hr']} bpm")
            except Exception as e:
                st.metric("🫀 Max HR", "Fehler")
                st.caption(f"❌ {str(e)[:30]}...")
        
        with col2:
            st.metric("📅 Testdatum", ekg_obj.date)
        
        with col3:
            try:
                duration_ms = ekg_obj.df["time in ms"].max() - ekg_obj.df["time in ms"].min()
                duration_minutes = duration_ms / 1000 / 60
                st.metric("⏱️ Dauer", f"{duration_minutes:.1f} min")
            except Exception as e:
                st.metric("⏱️ Dauer", "Fehler")
                st.caption(f"❌ {str(e)[:30]}...")
        
        with col4:
            # Durchschnittliche Herzfrequenz berechnen und anzeigen
            try:
                avg_hr = ekg_obj.calculate_average_heart_rate()
                
                if avg_hr is not None:
                    st.metric("💓 Ø Herzfrequenz", f"{avg_hr:.1f} bpm")
                else:
                    st.metric("💓 Ø Herzfrequenz", "N/A")
                        
            except Exception as e:
                st.metric("💓 Ø Herzfrequenz", "Fehler")

        # Plot-Einstellungen
        st.markdown("---")
        st.header("⚙️ Plot-Einstellungen")
        
        # Spalten für Einstellungen
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Zeitbereich-Auswahl
            st.subheader("🕐 Zeitbereich auswählen")
            
            time_data_seconds = (ekg_obj.df["time in ms"] - ekg_obj.df["time in ms"].min()) / 1000
            max_duration = float(time_data_seconds.max())
            
            time_range = st.slider(
                "Zeitbereich (Sekunden)",
                min_value=0.0,
                max_value=max_duration,
                value=(0.0, min(10.0, max_duration)),
                step=0.1,
                format="%.1f s",
                help="Wählen Sie den Zeitbereich für die EKG-Darstellung"
            )

        with col2:    
            st.metric("📍 Zeitspanne", f"{time_range[1] - time_range[0]:.1f} s")
  
            # Herzfrequenz für gewählten Zeitbereich
            if time_range[0] != 0.0 or time_range[1] != max_duration:
                try:
                    range_hr = ekg_obj.calculate_average_heart_rate(
                        range_start=time_range[0], 
                        range_end=time_range[1]
                    )
                    if range_hr is not None:
                        st.metric("💓 Bereichs-HR", f"{range_hr:.1f} bpm")
                    else:
                        st.warning("⚠️ HR nicht berechenbar")
                except Exception as e:
                    st.caption(f"❌ Fehler: {str(e)[:30]}...")

        # EKG-Plot
        st.markdown("---")
        st.header("📈 EKG-Visualisierung")
        
        try:
            with st.spinner("🔄 Erstelle EKG-Plot..."):
                fig = ekg_obj.plot_time_series(
                    range_start=time_range[0],
                    range_end=time_range[1]
                )
                
                st.plotly_chart(
                    fig, 
                    use_container_width=True, 
                    key=f"plot_{selected_ekg_id}_{time_range[0]}_{time_range[1]}"
                )
                
        except Exception as e:
            st.error(f"❌ Fehler beim Erstellen des Plots: {e}")
            st.info("💡 Versuchen Sie einen anderen Zeitbereich oder kontaktieren Sie den Support")

    elif not ekg_tests:
        st.warning("⚠️ Für diese Person sind keine EKG-Daten verfügbar.")
    
else:
    # Willkommensseite
    st.header("🎯 Willkommen im EKG-Analyse Dashboard!")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### Wählen Sie in der Seitenleiste eine Versuchsperson aus, um zu beginnen.")
        
        st.info("**📋 Verfügbare Funktionen:**")
        features = [
            "🫀 Maximale Herzfrequenz berechnen",
            "💓 Durchschnittliche Herzfrequenz anzeigen", 
            "📊 EKG-Daten visualisieren",
            "⏱️ Flexible Zeitbereich-Auswahl",
            "📈 Interaktive Plots mit Peak-Detection",
            "🔍 Optimierte Performance durch Caching"
        ]
        
        for feature in features:
            st.write(feature)

# Footer
st.markdown("---")
st.caption("EKG Analyse Dashboard | Version 2.0 | Lukas Köhler | Simon Krainer")