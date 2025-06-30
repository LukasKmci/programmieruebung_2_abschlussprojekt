import json
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
pio.renderers.default = "browser"
from datetime import datetime
import sqlite3


class EKG_data:

    def __init__(self, ekg_dict):
        """Initialize an EKG data object with a dictionary of person data"""
        self.id = ekg_dict["id"]
        self.date = ekg_dict["date"]
        self.data = ekg_dict["result_link"]
        self.birth_year = ekg_dict["date_of_birth"]
        self.gender = ekg_dict["gender"]
        self.df = pd.read_csv(self.data, sep="\t", header=None, names=["Messwerte in mV", "time in ms"])

    @staticmethod
    def load_by_id(ekg_id, patients_data):
        """Load EKG data by ID from a patient data list"""
        for person in patients_data:
            for ekg in person.get("ekg_tests", []):
                if ekg["id"] == ekg_id:
                    ekg["date_of_birth"] = person["date_of_birth"]
                    ekg["gender"] = person["gender"]
                    return EKG_data(ekg)
        raise ValueError(f"EKG with ID {ekg_id} not found.")
    
    @staticmethod
    def load_by_id_from_db(ekg_id):
        """Lädt EKG-Daten anhand der EKG-ID direkt aus der Datenbank."""
        conn = sqlite3.connect("personen.db")
        cursor = conn.cursor()

        # Hole EKG-Eintrag
        cursor.execute("SELECT id, user_id, date, result_link FROM ekg_tests WHERE id = ?", (ekg_id,))
        ekg_row = cursor.fetchone()

        if not ekg_row:
            raise ValueError(f"EKG mit ID {ekg_id} nicht gefunden.")

        # Hole Benutzerdaten (für Geburtsjahr und Geschlecht)
        user_id = ekg_row[1]
        cursor.execute("SELECT date_of_birth, gender FROM users WHERE id = ?", (user_id,))
        user_row = cursor.fetchone()

        conn.close()

        if not user_row:
            raise ValueError(f"Benutzer mit ID {user_id} nicht gefunden.")

        ekg_dict = {
            "id": ekg_row[0],
            "date": ekg_row[2],
            "result_link": ekg_row[3],
            "date_of_birth": user_row[0],
            "gender": user_row[1]
        }

        return EKG_data(ekg_dict)
       
    @staticmethod
    def find_peaks(series, threshold=360, window_size=5, min_peak_distance=200):
        """
        Find robust peaks using a window-based local maximum strategy.
        """
        peaks = []
        last_index = -min_peak_distance

        if isinstance(series, pd.Series):
            values = series.values
            indices = series.index
        else:
            values = series
            indices = range(len(series))


        for i in range(window_size, len(series) - window_size):
            window = values[i - window_size: i + window_size + 1]
            center_value = values[i]
            center_index = indices[i]

            # Ist der Mittelpunkt das Maximum im Fenster und über Threshold?
            if center_value == max(window) and center_value > threshold:
                if (center_index - last_index) >= min_peak_distance:
                    peaks.append((center_index, center_value))
                    last_index = center_index

        return pd.DataFrame(peaks, columns=["index", "value"])
   
    def calc_max_heart_rate(self, year_of_birth, gender):
        """Berechnet die maximale Herzfrequenz basierend auf Alter und Geschlecht."""
        age = datetime.now().year - year_of_birth

        if gender.lower() == "male":
            max_hr = 220 - age
        elif gender.lower() == "female":
            max_hr = 226 - age  # Alternative Formel für Frauen
        else:
            max_hr = 223 - age  # Neutraler Mittelwert, wenn Geschlecht unklar

        return {
            "age": age,
            "gender": gender,
            "max_hr": max_hr
        }

    def plot_time_series(self, threshold=360, min_peak_distance=200, range_start=None, range_end=None):
        """
        Erstellt einen Plotly-Plot der EKG-Zeitreihe
        
        Parameters:
        - threshold: Schwellenwert für Peak-Erkennung
        - min_peak_distance: Mindestabstand zwischen Peaks
        - range_start: Startzeit in Sekunden (nicht ms!)
        - range_end: Endzeit in Sekunden (nicht ms!)
        """
        
        # Zeit in Sekunden normalisieren (ab 0 startend)
        time_seconds = (self.df["time in ms"] - self.df["time in ms"].min()) / 1000
        
        # Bereich filtern falls angegeben
        if range_start is not None and range_end is not None:
            mask = (time_seconds >= range_start) & (time_seconds <= range_end)
            filtered_time = time_seconds[mask]
            filtered_data = self.df["Messwerte in mV"][mask]
        else:
            filtered_time = time_seconds
            filtered_data = self.df["Messwerte in mV"]
        
        # Plot erstellen
        fig = go.Figure()
        
        # EKG-Signal
        fig.add_trace(go.Scatter(
            x=filtered_time,
            y=filtered_data,
            mode='lines',
            name='EKG Signal',
            line=dict(color='blue', width=1)
        ))
        
        # Peak-Erkennung (falls gewünscht)
        if threshold and min_peak_distance:
            # Hier müssten Sie Ihre Peak-Erkennungslogik anpassen
            # um mit den gefilterten Daten zu arbeiten
            pass
        
        # Layout anpassen
        fig.update_layout(
            title='EKG Zeitreihe',
            xaxis_title='Zeit (Sekunden)',
            yaxis_title='Amplitude',
            hovermode='x unified'
        )
        
        return fig
        
    @staticmethod
    def average_hr(series, sampling_rate=1000, threshold=360, window_size=5, min_peak_distance=200):
            """
            Berechnet die durchschnittliche Herzfrequenz (in bpm) aus einem EKG-Signal.

            :param series: pd.Series mit EKG-Daten (Index = Zeit in ms oder Sample-Index)
            :param sampling_rate: Abtastrate in Hz (z. B. 1000 für 1 kHz)
            :param threshold: Amplitudenschwelle für Peak-Erkennung (z. B. 360 µV)
            :param window_size: Fenstergröße für lokale Maxima
            :param min_peak_distance: Mindestabstand zwischen Peaks (in ms)
            :return: durchschnittliche Herzfrequenz (float, bpm)
            """

            peaks_df = EKG_data.find_peaks(series, threshold=threshold,
                                            window_size=window_size,
                                            min_peak_distance=min_peak_distance)

            # Zeitachse berechnen (falls nötig)
            if isinstance(series.index, pd.DatetimeIndex):
                times_ms = peaks_df["index"].astype("int64") / 1e6  # ns → ms
            elif isinstance(series.index, pd.Index) and np.issubdtype(series.index.dtype, np.number):
                times_ms = peaks_df["index"].astype(float)  # Annahme: ms oder Samples
                if series.index[1] - series.index[0] != 1:
                    # Umrechnung von Sample-Index zu ms
                    times_ms = times_ms * (1000 / sampling_rate)
            else:
                raise ValueError("Zeitachse nicht interpretierbar.")

            # RR-Intervalle in ms
            rr_intervals = np.diff(times_ms)

            if len(rr_intervals) == 0:
                return np.nan  # Nicht genug Peaks gefunden

            # Durchschnittliches RR → HR = 60_000 / ØRR
            hr_avg = 60000 / np.mean(rr_intervals)
            return hr_avg

if __name__ == "__main__":
        #try:
    # JSON laden
    with open("data/person_db.json", "r", encoding="utf-8") as f:
        patients_data = json.load(f)

    print("\n--- Test: EKG laden ---")
    ekg = EKG_data.load_by_id(3, patients_data)
    print("Daten geladen:", ekg.df.head())

    print("\n--- Test: Peaks finden ---")
    peaks = EKG_data.find_peaks(ekg.df["Messwerte in mV"])
    print(f"Gefundene Peaks: {len(peaks)} -> Indices: {peaks[:5]}")

    print("\n--- Test: Maximale Herzfrequenz ---")
    hr = ekg.calc_max_heart_rate(ekg.birth_year, ekg.gender)
    print("Geschätzte maximale Herzfrequenz:", hr)
    print(f"\n✅ Test abgeschlossen – verwendete EKG-Test-ID: {ekg.id}")

    print("\n--- Plot: EKG mit Peaks ---")
    ekg.plot_time_series(threshold=360, min_peak_distance=200, range_start=1000, range_end=20000)

    print("\n--- Test: Durchschnittliche Herzfrequenz berechnen ---")
    hr_avg = EKG_data.average_hr(ekg.df["Messwerte in mV"], sampling_rate=1000,
                                 threshold=360, window_size=5, min_peak_distance=200)
    print(f"Durchschnittliche Herzfrequenz: {hr_avg:.1f} bpm")


    #except Exception as e:
    #print("❌ Fehler beim Testen:", e)