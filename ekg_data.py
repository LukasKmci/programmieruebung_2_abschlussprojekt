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
        """Load EKG data by ID from a patient data list"""
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

    def plot_time_series(self, threshold=360, window_size=5, min_peak_distance=200,
                        range_start=None, range_end=None):
        """
        Plot EKG data with detected peaks.
        Time is shown in seconds, starting from 0s relative to first data point.
        """

        # Originaldaten
        time_ms = self.df["time in ms"]
        signal = self.df["Messwerte in mV"]

        # Bereichsfilterung
        mask = pd.Series([True] * len(time_ms))
        if range_start is not None:
            mask &= time_ms >= range_start
        if range_end is not None:
            mask &= time_ms < range_end

        time_ms = time_ms[mask].reset_index(drop=True)
        signal = signal[mask].reset_index(drop=True)

        # 🛡 Schutz: Wenn nach dem Filtern keine Daten mehr vorhanden sind
        if time_ms.empty or signal.empty:
            return go.Figure().update_layout(
                title="⚠️ Keine Daten im gewählten Zeitbereich",
                xaxis_title="Zeit (s)",
                yaxis_title="Spannung (mV)"
            )
        # Zeit auf 0 normieren (und in Sekunden umrechnen)
        time_sec = (time_ms - time_ms.iloc[0]) / 1000.0

        # Peaks berechnen im gefilterten Bereich
        peaks_df = self.find_peaks(signal, threshold=threshold,
                                    window_size=window_size,
                                    min_peak_distance=min_peak_distance)
        peaks_df["time"] = peaks_df["index"].apply(lambda i: time_sec.iloc[i])

        # Plot erstellen
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=time_sec, y=signal,
            mode="lines",
            name="EKG",
            line=dict(color="blue")
        ))

        fig.add_trace(go.Scatter(
            x=peaks_df["time"],
            y=peaks_df["value"],
            mode="markers",
            name="Peaks",
            marker=dict(color="red", size=6, symbol="x"),
            hovertemplate="Zeit: %{x:.2f} s<br>mV: %{y}<extra></extra>"
        ))

        fig.update_layout(
            title=f"EKG mit Peaks (ID {self.id})",
            xaxis_title="Zeit (s)",
            yaxis_title="Spannung (mV)"
        )

        return fig
        


if __name__ == "__main__":
    #try:
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
    #print("❌ Fehler beim Testen:", e)