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

    st.write(f"**Der Name ist:** {person['lastname']} {person['firstname']}")

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
            st.subheader("Training Session Overview")
            st.write("Gib deine maximale Herzfrequenz (max HR) ein:")
            st.number_input("Max HR", value=hr_info["max_hr"], step=1, key="max_hr_input")

            # Plot anzeigen
            # Bereich automatisch setzen
            start_time = ekg_obj.df["time in ms"].min()
            end_time = ekg_obj.df["time in ms"].min() + 10000

            try:
                fig = ekg_obj.plot_time_series(
                    threshold=360,
                    min_peak_distance=200,
                    range_start=start_time,
                    range_end=end_time
                )
                st.plotly_chart(fig, use_container_width=True, key=f"plot_{selected_ekg_id}")
            except Exception as e:
                st.error(f"Fehler beim Erstellen des Plots: {e}")
