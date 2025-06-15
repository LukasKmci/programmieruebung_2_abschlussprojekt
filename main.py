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
            st.error("Keine EKG-Daten verfügbar")

    # EKG-Analyse-Sektion
    if ekg_tests and selected_ekg_id:
        st.markdown("---")
        st.header("📈 EKG-Analyse")
        
        ekg_obj = EKG_data.load_by_id(int(selected_ekg_id), persons_data)
        
        # Kennzahlen in Spalten - jetzt mit 5 Spalten für die durchschnittliche Herzfrequenz
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
            # Durchschnittliche Herzfrequenz berechnen und anzeigen
            try:
                # Debug: Prüfe ob die Methode existiert
                if hasattr(ekg_obj, 'calculate_average_heart_rate'):
                    # Berechne die durchschnittliche Herzfrequenz für die gesamten EKG-Daten
                    avg_hr = ekg_obj.calculate_average_heart_rate()
                    
                    if avg_hr is not None:
                        st.metric("💓 Ø Herzfrequenz", f"{avg_hr:.1f} bpm")
                        st.markdown(f"<div style='text-align: center; color: #28a745; font-size: 12px;'>●</div>", 
                                  unsafe_allow_html=True)
                    else:
                        st.metric("💓 Ø Herzfrequenz", "Fehler")
                        st.caption("🔍 Nicht genügend gültige Peaks gefunden")
                        
                        # Debug-Info in Expander
                        with st.expander("🔧 Debug-Info"):
                            st.write("Die Herzfrequenz-Berechnung konnte nicht durchgeführt werden.")
                            st.write("Mögliche Ursachen:")
                            st.write("- Zu wenige R-Peaks erkannt")
                            st.write("- Schlechte Signalqualität")
                            st.write("- Parameter müssen angepasst werden")
                else:
                    # Fallback: Versuche eine einfachere Herzfrequenz-Berechnung
                    st.metric("💓 Ø Herzfrequenz", "N/A")
                    st.caption("⚠️ Methode nicht verfügbar")
                        
            except Exception as e:
                st.metric("💓 Ø Herzfrequenz", "N/A")
                st.caption(f"❌ Error: {str(e)[:30]}...")
                
                # Debug-Expander für Entwicklung
                with st.expander("🐛 Fehler-Details"):
                    st.error(f"**Vollständiger Fehler:** {str(e)}")
                    st.write("**EKG-Objekt Methoden:**")
                    methods = [method for method in dir(ekg_obj) if not method.startswith('_')]
                    st.write(methods)

        # Plot-Einstellungen
        st.markdown("---")
        st.header("⚙️ Plot-Einstellungen")
        
        # Spalten für Einstellungen
        col1, col2, col3 = st.columns([2,1,1])
        
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

        with col2:    
            st.metric("📍 Gewählter Bereich:", f"{time_range[0]:.1f} - {time_range[1]:.1f} Sekunden")

        with col3:   
            # Zusätzliche Info: Herzfrequenz für gewählten Zeitbereich
            if time_range[0] != 0.0 or time_range[1] != max_duration:
                try:
                    if hasattr(ekg_obj, 'calculate_average_heart_rate'):
                        range_hr = ekg_obj.calculate_average_heart_rate(
                            range_start=time_range[0], 
                            range_end=time_range[1]
                        )
                        if range_hr is not None:
                            st.metric("💓 Herzfrequenz im Bereich:", f"{range_hr:.1f} bpm")
                        else:
                            st.warning("⚠️ Herzfrequenz für Bereich nicht berechenbar")
                except Exception as e:
                    st.metric("🔍 Bereichs-HR:", f"{str(e)[:50]}")

        # Parameter mit Standardwerten definieren
        sampling_rate = 500
        threshold_factor = 0.6
        min_rr_interval = 0.3
        max_rr_interval = 2.0
        use_adaptive = True
        
        # EKG-Plot
        st.markdown("---")
        st.header("📊 EKG-Visualisierung")
        
        try:
            with st.spinner("🔄 Lade EKG-Daten..."):
                # Plot erstellen
                fig = ekg_obj.plot_time_series(
                    range_start=time_range[0],
                    range_end=time_range[1],
                    sampling_rate=sampling_rate,
                    threshold_factor=threshold_factor,
                    min_rr_interval=min_rr_interval,
                    max_rr_interval=max_rr_interval,
                    adaptive_threshold=use_adaptive
                )
                
                st.plotly_chart(fig, use_container_width=True, key=f"plot_{selected_ekg_id}")
                
        except Exception as e:
            st.error(f"❌ Fehler beim Erstellen des Plots: {e}")
            st.info("💡 Versuchen Sie einen anderen Zeitbereich")

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
        st.write("💓 Durchschnittliche Herzfrequenz anzeigen")
        st.write("📊 EKG-Daten visualisieren") 
        st.write("⏱️ Flexible Zeitbereich-Auswahl")
        st.write("📈 Interaktive Plots")
        st.write("🔍 Anpassbare Peak-Detection")

# Footer
st.markdown("---")
st.caption("EKG Analyse Dashboard | Version 1.0 | Lukas Köhler | Simon Krainer")