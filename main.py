# main.py
import streamlit as st
import pandas as pd
from person import Person
from ekg_data import EKG_data
import os

st.set_page_config(
    page_title="EKG & Sports Analyse Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🫀🏃‍♂️"
)

# Titel
st.title("🫀🏃‍♂️ EKG & Sports Analyse Dashboard")
st.markdown("---")

# sidebar for main navigation
with st.sidebar:
    st.sidebar.header("Navigation")
    st.selectbox("Wähle eine Seite", ["EKG Analyse", "Trainings"])

    # Personen laden
    persons_data = Person.load_person_data()
    person_names = Person.get_person_list(persons_data)

    # Auswahl der Versuchsperson
    selected_name = st.selectbox("Versuchsperson auswählen", person_names)

if selected_name:
    person = Person.find_person_data_by_name(selected_name)

   
    # Personeninformationen anzeigen
    st.header("👤 Personeninformationen")
    
    col1, col2 = st.columns([2, 2])
    
    # Bild anzeigen
    with col1:
        picture_path = person["picture_path"]
        if os.path.exists(picture_path):
            st.image(picture_path, caption=selected_name, width=150)
        else:
            st.warning("Kein Bild gefunden.")

    with col2:
        st.header("📝 Persönliche Daten")
        st.write(f"**Name:** {selected_name}")
        st.write(f"**Geburtsjahr:** {person['date_of_birth']}")
        st.write(f"**Geschlecht:** {person['gender']}")
        st.write(f"**Verfügbare EKG-Tests:** {len(person.get('ekg_tests', []))}")
        
        
    # Anzeige der EKG-Daten-Auswahl
    st.markdown("---")
    ekg_tests = person.get("ekg_tests", [])
    if ekg_tests:
        ekg_ids = [str(test["id"]) for test in ekg_tests]
        selected_ekg_id = st.selectbox("📊EKG-Datensatz wählen", ekg_ids)

        if selected_ekg_id:
            ekg_obj = EKG_data.load_by_id(int(selected_ekg_id), persons_data)

            # Max. Herzfrequenz und durchschnittliche Herzfrequenz berechnen
            hr_info = ekg_obj.calc_max_heart_rate(ekg_obj.birth_year, ekg_obj.gender)
            
            # Durchschnittliche Herzfrequenz berechnen
            avg_hr = EKG_data.average_hr(
                ekg_obj.df["Messwerte in mV"], 
                sampling_rate=1000,
                threshold=360, 
                window_size=5, 
                min_peak_distance=200
            )
            
            st.header("📊 EKG-Kennzahlen")
            
            # Metriken in Spalten anzeigen
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric("🫀Max HR", f"{hr_info['max_hr']} bpm")
            
            with col2:
                if avg_hr and not pd.isna(avg_hr):
                    st.metric("💓 Ø Herzfrequenz", f"{avg_hr:.1f} bpm")
                    
                    # HR-Bereich Bewertung
                    hr_percentage = (avg_hr / hr_info['max_hr']) * 100
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
                    st.metric("Durchschnittliche HR", "Nicht berechenbar")
                    hr_percentage = 0
                    hr_zone = "Unbekannt"
                    zone_color = "⚪"
            
            with col3:
                if avg_hr and not pd.isna(avg_hr):
                    st.metric("HR-Zone", f"{zone_color} {hr_zone}")
                    st.write(f"({hr_percentage:.1f}% der Max HR)")
                else:
                    st.metric("HR-Zone", "⚪ Unbekannt")
            
            with col4:
                st.metric(f"📅 Testdatum", ekg_obj.date)
            
            with col5:
                # Dauer des EKGs berechnen und auf ganze Sekunden runden
                ekg_duration_ms = ekg_obj.df["time in ms"].max() - ekg_obj.df["time in ms"].min()
                ekg_duration_seconds = round(ekg_duration_ms / 1000)  # Auf ganze Sekunden
                st.metric("⏱️ Dauer des EKGs", f"{ekg_duration_seconds/60:.0f} Minuten")

            # Zeitbereich-Auswahl mit Slider
            st.markdown("---")
            st.subheader("Zeitbereich auswählen")

            # Spalten für die Zeitbereichsauswahl
            col1, col2 = st.columns([3,1])
            
            with col1:
                # Zeitdaten in Sekunden umrechnen für bessere UX
                time_data_seconds = (ekg_obj.df["time in ms"] - ekg_obj.df["time in ms"].min()) / 1000
                max_duration = time_data_seconds.max()

                # Dual-Range Slider in Sekunden
                time_range = st.slider(
                    "Zeitbereich (Sekunden)",
                    min_value=0.0,
                    max_value=max_duration,
                    value=(0.0, min(10.0, max_duration)),
                    step=0.1,
                    format="%.1f s"
                )
            # Anzeige des gewählten Zeitbereichs
                st.write(f"Gewählter Bereich: {time_range[0]:.1f} - {time_range[1]:.1f} Sekunden")

            with col2:
                # Durchschnittliche Herzfrequenz im gewählten Zeitbereich berechnen
                if time_range[0] != 0.0 or time_range[1] != max_duration:
                    try:
                        # Zeitdaten in Sekunden berechnen
                        time_seconds = (ekg_obj.df["time in ms"] - ekg_obj.df["time in ms"].min()) / 1000
                        # Maske für den gewählten Bereich
                        mask = (time_seconds >= time_range[0]) & (time_seconds <= time_range[1])
                        filtered_data = ekg_obj.df["Messwerte in mV"][mask]

                        if len(filtered_data) > 0:
                            # Die gleichen Parameter wie oben verwenden
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

            # Plot anzeigen
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
                st.error(f"Fehler beim Erstellen des Plots: {e}")

# Footer
st.markdown("---")
st.caption("EKG & Sports Analyse Dashboard | Version 2.1 | Lukas Köhler | Simon Krainer")                