# main.py
import streamlit as st
from person import Person
from ekg_data import EKG_data
import os

st.set_page_config(page_title="EKG APP", layout="centered")

# Titel
st.title("EKG APP")

# Personen laden
persons_data = Person.load_person_data()
person_names = Person.get_person_list(persons_data)

# Auswahl der Versuchsperson
selected_name = st.selectbox("Versuchsperson auswählen", person_names)

if selected_name:
    person = Person.find_person_data_by_name(selected_name)

    st.write(f"**Geburtsjahr:** {person['date_of_birth']}")

    # Bild anzeigen
    picture_path = person["picture_path"]
    if os.path.exists(picture_path):
        st.image(picture_path, caption=selected_name, width=150)
    else:
        st.warning("Kein Bild gefunden.")

    # Anzeige der EKG-Daten-Auswahl
    ekg_tests = person.get("ekg_tests", [])
    if ekg_tests:
        ekg_ids = [str(test["id"]) for test in ekg_tests]
        selected_ekg_id = st.selectbox("Wähle EKG-Datensatz", ekg_ids)

        if selected_ekg_id:
            ekg_obj = EKG_data.load_by_id(int(selected_ekg_id), persons_data)

            # Max. Herzfrequenz anzeigen
            hr_info = ekg_obj.calc_max_heart_rate(ekg_obj.birth_year, ekg_obj.gender)
            st.subheader("EKG-Daten overview")
            st.metric("Max HR", f"{hr_info['max_hr']} bpm")
            st.write(f"Testdatum: {ekg_obj.date}")
            
            # Dauer des EKGs berechnen und auf ganze Sekunden runden
            ekg_duration_ms = ekg_obj.df["time in ms"].max() - ekg_obj.df["time in ms"].min()
            ekg_duration_seconds = round(ekg_duration_ms / 1000)  # Auf ganze Sekunden
            st.write(f"Dauer des EKGs: {ekg_duration_seconds/60:.0f} Minuten")

            # Zeitbereich-Auswahl mit Slider
            st.subheader("Zeitbereich für Plot auswählen")
            
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

            st.write(f"Gewählter Bereich: {time_range[0]:.1f} - {time_range[1]:.1f} Sekunden")

            # Plot anzeigen
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