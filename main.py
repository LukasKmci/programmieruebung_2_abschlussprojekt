# main.py
import streamlit as st
import sqlite3
import uuid
import time
import pandas as pd
from person import Person
from ekg_data import EKG_data
from datetime import datetime
import plotly.graph_objects as go
import numpy as np
import os
from PIL import Image, ExifTags
from sport_data import load_sports_data, filter_data_by_time_range, calculate_filtered_stats, format_duration, load_sports_data

st.set_page_config(
    page_title="EKG & Sports Analyse Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🫀🏃‍♂️"
)

# sidebar for main navigation
with st.sidebar:
    st.sidebar.header("Navigation")
    selected_page = st.selectbox("Wähle eine Seite", ["EKG Analyse", "Trainings", "👤 Benutzer anlegen", "📥 FIT-Import", "📂 FIT-Dateien anzeigen"])

    # Personen laden
    persons_data = Person.load_person_data_from_db()
    person_names = Person.get_person_list(persons_data)

    # Auswahl der Versuchsperson
    selected_name = st.selectbox("Versuchsperson auswählen", person_names)

if selected_page == "EKG Analyse":
        st.title("🫀 EKG Analyse")
        st.markdown("---")

        if selected_name:
            person = Person.find_person_data_by_name_from_db(selected_name)

    
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
                ekg_obj = EKG_data.load_by_id_from_db(int(selected_ekg_id))

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

# main.py
# Seite der Trainings
elif selected_page == "Trainings":
    st.title("🏋️‍♂️ Trainingsübersicht")
    st.markdown("---")

    # Lade Benutzer aus SQLite
    person = Person.find_person_data_by_name_from_db(selected_name)
    if person is None:
        st.error("❌ Benutzer nicht gefunden!")
        st.stop()

    # Personeninformationen anzeigen
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

    # Lade zugeordnete .fit-Dateien aus SQLite
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

    # Lade und analysiere Datei
    from sport_data import load_sports_data, filter_data_by_time_range, calculate_filtered_stats, format_duration, get_time_range_info

    all_data = load_sports_data()

    # Debug-Ausgabe
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

    # Analysebereich
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

    # 📈 Plotly-Visualisierung für Sportdaten
    st.markdown("---")
    st.header("📈 Trainingsverlauf im gewählten Zeitraum")

    t0 = filtered["time"][0]
    time_minutes = (filtered["time"] - t0) / 60
    mask = (time_minutes >= time_range[0]) & (time_minutes <= time_range[1])

    fig = go.Figure()

    # Herzfrequenz
    if "heartrate" in filtered:
        fig.add_trace(go.Scatter(
            x=time_minutes[mask],
            y=filtered["heartrate"][mask],
            mode="lines",
            name="Herzfrequenz (bpm)",
            line=dict(color="red")
        ))

    # Geschwindigkeit
    if "velocity" in filtered:
        fig.add_trace(go.Scatter(
            x=time_minutes[mask],
            y=filtered["velocity"][mask] * 3.6,
            mode="lines",
            name="Geschwindigkeit (km/h)",
            line=dict(color="blue")
        ))

    # Leistung
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

   
    # Neue Seite zur Benutzererstellung
elif selected_page == "👤 Benutzer anlegen":
    st.title("👤 Neuen Benutzer anlegen")
    st.markdown("---")

    with st.form("benutzer_formular"):
        col1, col2 = st.columns(2)
        with col1:
            firstname = st.text_input("Vorname")
            lastname = st.text_input("Nachname")
            date_of_birth = st.number_input("Geburtsjahr", min_value=1900, max_value=2100)
            gender = st.selectbox("Geschlecht", ["male", "female", "other"])
        with col2:
            uploaded_file = st.file_uploader("📷 Bild hochladen", type=["jpg", "jpeg", "png"])
        
        submitted = st.form_submit_button("Benutzer erstellen")

        if submitted:
            if not firstname or not lastname:
                st.error("Vor- und Nachname sind erforderlich!")
            else:
                # Benutzer-ID generieren
                new_id = int(uuid.uuid4().int % 1_000_000)

                # Bild speichern
                picture_path = "data/pictures"
                os.makedirs(picture_path, exist_ok=True)

                if uploaded_file is not None:
                    file_extension = os.path.splitext(uploaded_file.name)[1]
                    filename = f"{new_id}{file_extension}"
                    save_path = os.path.join(picture_path, filename)

                    # Bild korrekt laden und ggf. drehen
                    image = Image.open(uploaded_file)

                    try:
                        for orientation in ExifTags.TAGS.keys():
                            if ExifTags.TAGS[orientation] == "Orientation":
                                break

                        exif = image._getexif()

                        if exif is not None:
                            orientation_value = exif.get(orientation, None)

                            if orientation_value == 3:
                                image = image.rotate(180, expand=True)
                            elif orientation_value == 6:
                                image = image.rotate(270, expand=True)
                            elif orientation_value == 8:
                                image = image.rotate(90, expand=True)
                    except Exception as e:
                        print("EXIF-Rotation konnte nicht gelesen werden:", e)

                    image.save(save_path)
                    picture_file = save_path
                else:
                    picture_file = "data/pictures/default.jpg"

                # In Datenbank speichern
                conn = sqlite3.connect("personen.db")
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (id, firstname, lastname, date_of_birth, gender, picture_path)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (new_id, firstname, lastname, date_of_birth, gender, picture_file))
                conn.commit()
                conn.close()

                st.success(f"✅ Benutzer {firstname} {lastname} wurde erfolgreich angelegt.")

elif selected_page == "📥 FIT-Import":
    st.title("📥 .fit-Datei hochladen & Benutzer zuweisen")
    st.markdown("---")

    # Lade Personen aus Datenbank
    conn = sqlite3.connect("personen.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, firstname, lastname FROM users")
    users = cursor.fetchall()
    conn.close()

    if not users:
        st.error("⚠️ Keine Benutzer in der Datenbank!")
    else:
        user_dict = {f"{u[1]} {u[2]} (ID: {u[0]})": u[0] for u in users}
        selected_user_label = st.selectbox("👤 Benutzer auswählen", list(user_dict.keys()))
        selected_user_id = user_dict[selected_user_label]

        uploaded_file = st.file_uploader("📁 .fit-Datei auswählen", type=["fit"])

        if uploaded_file:
            if st.button("📤 Datei hochladen"):
                # Datei speichern
                save_dir = "data/sports_data"
                os.makedirs(save_dir, exist_ok=True)

                timestamp = int(time.time())
                filename = f"{selected_user_id}_{timestamp}.fit"
                save_path = os.path.join(save_dir, filename)

                with open(save_path, "wb") as f:
                    f.write(uploaded_file.read())

                # In Datenbank eintragen
                conn = sqlite3.connect("personen.db")
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO sports_sessions (user_id, file_name, timestamp)
                    VALUES (?, ?, ?)
                """, (selected_user_id, filename, datetime.fromtimestamp(timestamp).isoformat()))
                conn.commit()
                conn.close()

                st.success(f"✅ Datei erfolgreich hochgeladen und Benutzer zugewiesen: {selected_user_label}")

elif selected_page == "📂 FIT-Dateien anzeigen":
    st.title("📂 Zugeordnete .fit-Dateien anzeigen")
    st.markdown("---")

    # Lade alle Benutzer
    conn = sqlite3.connect("personen.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, firstname, lastname FROM users")
    users = cursor.fetchall()
    conn.close()

    if not users:
        st.warning("⚠️ Keine Benutzer gefunden.")
    else:
        user_map = {f"{u[1]} {u[2]} (ID: {u[0]})": u[0] for u in users}
        selected_user_label = st.selectbox("👤 Benutzer auswählen", list(user_map.keys()))
        selected_user_id = user_map[selected_user_label]

        # Hole alle zugeordneten .fit-Dateien
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

                # Mit vorhandener Logik aus sport_data analysieren
                from sport_data import load_sports_data, filter_data_by_time_range, calculate_filtered_stats, format_duration, get_time_range_info
                from fitparse import FitFile
                import numpy as np

                # Lade nur diese Datei
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
                        st.metric("Distanz", f"{stats['total_distance_km']:.2f} km")
                        st.metric("Ø Herzfrequenz", f"{stats['avg_heartrate']:.0f} bpm")
                        st.metric("Ø Geschwindigkeit", f"{stats['avg_speed_kmh']:.1f} km/h")
                        st.metric("Dauer", format_duration(stats['duration_seconds']))

# Footer
st.markdown("---")
st.caption("EKG & Sports Analyse Dashboard | Version 2.1 | Lukas Köhler | Simon Krainer")