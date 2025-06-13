import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
pio.renderers.default = "browser"
from datetime import datetime


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
        """Load EKG data by ID from a patient data list
        
        Parameters:
        - ekg_id: ID of the EKG test to load
        - patients_data: List of patient data dictionaries
        """

        for person in patients_data:
            for ekg in person.get("ekg_tests", []):
                if ekg["id"] == ekg_id:
                    ekg["date_of_birth"] = person["date_of_birth"]
                    ekg["gender"] = person["gender"]
                    return EKG_data(ekg)
        raise ValueError(f"EKG with ID {ekg_id} not found.")
       
    @staticmethod
    def find_peaks(series, threshold=360, window_size=5, min_peak_distance=200):
        """
        Find robust peaks using a window-based local maximum strategy.

        Parameters:
        - threshold: Schwellenwert für Peak-Erkennung
        - window_size: Größe des Fensters für lokale Maxima
        - min_peak_distance: Mindestabstand zwischen Peaks in Indizes
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
        """Berechnet die maximale Herzfrequenz basierend auf Alter und Geschlecht.
        
        Parameters:
        - year_of_birth: Geburtsjahr der Person
        - gender: Geschlecht der Person
        """
        age = datetime.now().year - year_of_birth

        if gender.lower() == "male":
            max_hr = 220 - age # Formel für Männer
        elif gender.lower() == "female":
            max_hr = 226 - age  # Formel für Frauen
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
        - range_start: Startzeit in Sekunden
        - range_end: Endzeit in Sekunden
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
        
        # Layout anpassen
        fig.update_layout(
            title='EKG Zeitreihe',
            xaxis_title='Zeit (Sekunden)',
            yaxis_title='Amplitude',
            hovermode='x unified'
        )
        
        return fig
        


if __name__ == "__main__":
    # Testen der EKG_data Klasse
    
    # JSON laden
    with open("data/person_db.json", "r", encoding="utf-8") as f:
        patients_data = json.load(f)

    print("\n--- Test: EKG laden ---")
    ekg = EKG_data.load_by_id(4, patients_data)
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


    #except Exception as e:
    #print("Fehler beim Testen:", e)