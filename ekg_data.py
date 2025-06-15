import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import numpy as np
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
    def find_peaks(series, sampling_rate=500, threshold_factor=0.6, window_size=None, 
                min_rr_interval=0.3, max_rr_interval=2.0, adaptive_threshold=True):
        """
        Find robust R-peaks in ECG signal using improved window-based local maximum strategy.

        Parameters:
        - series: EKG-Signal (pandas Series oder Array)
        - sampling_rate: Abtastrate in Hz (default: 500)
        - threshold_factor: Faktor für adaptiven Threshold (0.0-1.0, default: 0.6)
        - window_size: Fenstergröße für lokale Maxima (auto wenn None)
        - min_rr_interval: Minimaler RR-Abstand in Sekunden (default: 0.3s = 200 bpm max)
        - max_rr_interval: Maximaler RR-Abstand in Sekunden (default: 2.0s = 30 bpm min)
        - adaptive_threshold: Ob adaptiver Threshold verwendet werden soll
        """
        peaks = []
        
        # Konvertierung zu numpy array
        if isinstance(series, pd.Series):
            values = series.values
            indices = series.index.values
        else:
            values = np.array(series)
            indices = np.arange(len(series))
        
        # Automatische Parameter-Berechnung basierend auf Abtastrate
        if window_size is None:
            window_size = max(5, int(sampling_rate * 0.02))  # 20ms Fenster
        
        min_peak_distance = int(min_rr_interval * sampling_rate)
        max_peak_distance = int(max_rr_interval * sampling_rate)
        
        # Adaptiver oder fester Threshold
        if adaptive_threshold:
            signal_max = np.max(values)
            signal_mean = np.mean(values)
            threshold = signal_mean + (signal_max - signal_mean) * threshold_factor
        else:
            threshold = threshold_factor  # Wenn adaptive_threshold=False, ist threshold_factor der absolute Wert
        
        print(f"Verwendete Parameter:")
        print(f"- Abtastrate: {sampling_rate} Hz")
        print(f"- Fenstergröße: {window_size} Samples")
        print(f"- Min. Peak-Abstand: {min_peak_distance} Samples ({min_rr_interval}s)")
        print(f"- Max. Peak-Abstand: {max_peak_distance} Samples ({max_rr_interval}s)")
        print(f"- Threshold: {threshold:.2f}")
        
        last_index = -min_peak_distance
        
        # Peak-Detektion
        for i in range(window_size, len(values) - window_size):
            window = values[i - window_size: i + window_size + 1]
            center_value = values[i]
            center_index = indices[i]
            
            # Ist der Mittelpunkt das Maximum im Fenster und über Threshold?
            if center_value == np.max(window) and center_value > threshold:
                current_distance = center_index - last_index
                
                # Prüfe Mindest- und Maximalabstand
                if current_distance >= min_peak_distance:
                    # Wenn der Abstand zu groß ist, könnte ein Peak fehlen
                    if current_distance > max_peak_distance and len(peaks) > 0:
                        print(f"Warnung: Großer RR-Abstand bei Index {center_index}: {current_distance/sampling_rate:.2f}s")
                    
                    peaks.append((center_index, center_value))
                    last_index = center_index
        
        # Erstelle DataFrame mit zusätzlichen Informationen
        if len(peaks) > 0:
            peaks_df = pd.DataFrame(peaks, columns=["index", "value"])
            
            # Berechne RR-Intervalle
            if len(peaks_df) > 1:
                rr_intervals = np.diff(peaks_df["index"].values) / sampling_rate
                peaks_df["rr_interval"] = [np.nan] + list(rr_intervals)
                
                # Statistiken
                print(f"\nGefundene Peaks: {len(peaks_df)}")
                if len(rr_intervals) > 0:
                    mean_hr = 60 / np.mean(rr_intervals)
                    print(f"Durchschnittliche Herzfrequenz: {mean_hr:.1f} bpm")
                    print(f"RR-Intervall Bereich: {np.min(rr_intervals):.3f}s - {np.max(rr_intervals):.3f}s")
            
            return peaks_df
        else:
            print("Keine Peaks gefunden! Überprüfe Threshold und Signalqualität.")
            return pd.DataFrame(columns=["index", "value", "rr_interval"])


        # Beispiel für die Verwendung:
        # peaks = find_peaks(ecg_signal, sampling_rate=500, threshold_factor=0.6)

        # Für manuelle Threshold-Kontrolle:
        # peaks = find_peaks(ecg_signal, sampling_rate=500, threshold_factor=360, adaptive_threshold=False)
   
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

    def plot_time_series(self, range_start=None, range_end=None, 
                        sampling_rate=500, threshold_factor=0.6, 
                        min_rr_interval=0.3, max_rr_interval=2.0, 
                        adaptive_threshold=True, window_size=None,
                        # Backward compatibility - alte Parameter
                        threshold=None, min_peak_distance=None):
        """
        Erstellt einen Plotly-Plot der EKG-Zeitreihe mit Peak-Detection
        
        Parameters:
        - range_start: Startzeit in Sekunden
        - range_end: Endzeit in Sekunden
        - sampling_rate: Abtastrate in Hz (default: 500)
        - threshold_factor: Faktor für adaptiven Threshold (0.0-1.0, default: 0.6)
        - min_rr_interval: Minimaler RR-Abstand in Sekunden (default: 0.3s)
        - max_rr_interval: Maximaler RR-Abstand in Sekunden (default: 2.0s)
        - adaptive_threshold: Ob adaptiver Threshold verwendet werden soll
        - window_size: Fenstergröße für Peak-Detection (auto wenn None)
        
        Backward compatibility:
        - threshold: Alter absoluter Schwellenwert (überschreibt adaptive_threshold)
        - min_peak_distance: Alter Mindestabstand in Samples
        """
        
        # Zeit in Sekunden normalisieren (ab 0 startend)
        time_seconds = (self.df["time in ms"] - self.df["time in ms"].min()) / 1000
        
        # Bereich filtern falls angegeben
        if range_start is not None and range_end is not None:
            mask = (time_seconds >= range_start) & (time_seconds <= range_end)
            filtered_time = time_seconds[mask]
            filtered_data = self.df["Messwerte in mV"][mask]
            filtered_indices = self.df.index[mask]
        else:
            filtered_time = time_seconds
            filtered_data = self.df["Messwerte in mV"]
            filtered_indices = self.df.index
        
        # Peak-Detection durchführen
        try:
            # Backward compatibility: Wenn alte Parameter übergeben werden
            if threshold is not None or min_peak_distance is not None:
                # Verwende alte find_peaks Methode
                if threshold is None:
                    threshold = 360
                if min_peak_distance is None:
                    min_peak_distance = 200
                
                peaks_df = self.find_peaks(
                    filtered_data, 
                    threshold=threshold, 
                    min_peak_distance=min_peak_distance
                )
                
                # Konvertiere Indizes zu Zeiten für alte Methode
                if len(peaks_df) > 0:
                    peak_times = []
                    peak_values = []
                    for _, peak in peaks_df.iterrows():
                        # Finde entsprechende Zeit
                        peak_idx = peak['index']
                        if peak_idx in filtered_indices:
                            idx_pos = list(filtered_indices).index(peak_idx)
                            peak_times.append(filtered_time.iloc[idx_pos])
                            peak_values.append(peak['value'])
            else:
                # Verwende neue find_peaks Methode
                peaks_df = self.find_peaks(
                    filtered_data,
                    sampling_rate=sampling_rate,
                    threshold_factor=threshold_factor,
                    window_size=window_size,
                    min_rr_interval=min_rr_interval,
                    max_rr_interval=max_rr_interval,
                    adaptive_threshold=adaptive_threshold
                )
                
                # Konvertiere Indizes zu Zeiten für neue Methode
                if len(peaks_df) > 0:
                    peak_times = []
                    peak_values = []
                    for _, peak in peaks_df.iterrows():
                        # Index ist hier relativ zu filtered_data
                        peak_idx = int(peak['index'])
                        if peak_idx < len(filtered_time):
                            peak_times.append(filtered_time.iloc[peak_idx])
                            peak_values.append(peak['value'])
            
        except Exception as e:
            print(f"Fehler bei Peak-Detection: {e}")
            peak_times = []
            peak_values = []
        
        # Plot erstellen
        fig = go.Figure()
        
        # EKG-Signal
        
        # EKG-Signal
        fig.add_trace(go.Scatter(
            x=filtered_time,
            y=filtered_data,
            mode='lines',
            name='EKG Signal',
            line=dict(color='blue', width=1),
            hovertemplate='Zeit: %{x:.2f}s<br>Amplitude: %{y:.2f}mV<extra></extra>'
        ))
        
        # R-Peaks hinzufügen
        if len(peak_times) > 0:
            fig.add_trace(go.Scatter(
                x=peak_times,
                y=peak_values,
                mode='markers',
                name=f'R-Peaks ({len(peak_times)})',
                marker=dict(
                    color='red',
                    size=8,
                    symbol='triangle-up'
                ),
                hovertemplate='R-Peak<br>Zeit: %{x:.2f}s<br>Amplitude: %{y:.2f}mV<extra></extra>'
            ))
            
            # Herzfrequenz berechnen und anzeigen
            if len(peak_times) > 1:
                rr_intervals = []
                for i in range(1, len(peak_times)):
                    rr_intervals.append(peak_times[i] - peak_times[i-1])
                
                if rr_intervals:
                    avg_rr = sum(rr_intervals) / len(rr_intervals)
                    avg_hr = 60 / avg_rr if avg_rr > 0 else 0
                    
                    # Titel mit Herzfrequenz
                    title_text = f'EKG Zeitreihe - ∅ Herzfrequenz: {avg_hr:.1f} bpm'
                else:
                    title_text = 'EKG Zeitreihe'
            else:
                title_text = 'EKG Zeitreihe - Keine ausreichenden R-Peaks für Herzfrequenz'
        else:
            title_text = 'EKG Zeitreihe - Keine R-Peaks erkannt'
        
        # Layout anpassen
        fig.update_layout(
            title=title_text,
            xaxis_title='Zeit (Sekunden)',
            yaxis_title='Amplitude (mV)',
            hovermode='x unified',
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01
            ),
            # Responsive Design
            autosize=True,
            margin=dict(l=50, r=50, t=80, b=50)
        )
        
        # Grid und Styling
        fig.update_xaxes(
            showgrid=True, 
            gridwidth=1, 
            gridcolor='lightgray',
            zeroline=True
        )
        fig.update_yaxes(
            showgrid=True, 
            gridwidth=1, 
            gridcolor='lightgray',
            zeroline=True
        )
        
        
        return fig
            
    def calculate_average_heart_rate(self, range_start=None, range_end=None,
                                sampling_rate=500, threshold_factor=0.6,
                                min_rr_interval=0.3, max_rr_interval=2.0,
                                adaptive_threshold=True, window_size=None,
                                outlier_threshold=0.3, min_peaks_required=3):
        """
        Berechnet die durchschnittliche Herzfrequenz mit robuster Ausreißererkennung
        
        Parameters:
        - range_start: Startzeit in Sekunden
        - range_end: Endzeit in Sekunden
        - sampling_rate: Abtastrate in Hz (default: 500)
        - threshold_factor: Faktor für adaptiven Threshold (0.0-1.0, default: 0.6)
        - min_rr_interval: Minimaler RR-Abstand in Sekunden (default: 0.3s)
        - max_rr_interval: Maximaler RR-Abstand in Sekunden (default: 2.0s)
        - adaptive_threshold: Ob adaptiver Threshold verwendet werden soll
        - window_size: Fenstergröße für Peak-Detection (auto wenn None)
        - outlier_threshold: Schwelle für Ausreißererkennung (default: 0.3 = 30%)
        - min_peaks_required: Mindestanzahl R-Peaks für zuverlässige Berechnung
        
        Returns:
        - float: Durchschnittliche Herzfrequenz in bpm, oder None bei Fehler
        """
        
        # Zeit in Sekunden normalisieren
        time_seconds = (self.df["time in ms"] - self.df["time in ms"].min()) / 1000
        
        # Bereich filtern falls angegeben
        if range_start is not None and range_end is not None:
            mask = (time_seconds >= range_start) & (time_seconds <= range_end)
            filtered_data = self.df["Messwerte in mV"][mask]
        else:
            filtered_data = self.df["Messwerte in mV"]
        
        try:
            # Peak-Detection durchführen (nutzt die bereits vorhandene find_peaks Methode)
            peaks_df = self.find_peaks(
                filtered_data,
                sampling_rate=sampling_rate,
                threshold_factor=threshold_factor,
                window_size=window_size,
                min_rr_interval=min_rr_interval,
                max_rr_interval=max_rr_interval,
                adaptive_threshold=adaptive_threshold
            )
            
            # Mindestanzahl Peaks prüfen
            if len(peaks_df) < min_peaks_required:
                print(f'Nicht genügend R-Peaks erkannt ({len(peaks_df)} < {min_peaks_required})')
                return None
            
            # RR-Intervalle aus der peaks_df extrahieren (falls bereits berechnet)
            if 'rr_interval' in peaks_df.columns:
                rr_intervals = peaks_df['rr_interval'].dropna().values
            else:
                # RR-Intervalle aus Peak-Indizes berechnen
                peak_indices = peaks_df['index'].values
                
                # Konvertiere Indizes zu Zeiten
                if range_start is not None and range_end is not None:
                    time_per_sample = 1.0 / sampling_rate
                    peak_times = peak_indices * time_per_sample
                else:
                    peak_times = []
                    for idx in peak_indices:
                        if idx < len(time_seconds):
                            peak_times.append(time_seconds.iloc[idx])
                    peak_times = np.array(peak_times)
                
                # RR-Intervalle berechnen
                if len(peak_times) > 1:
                    rr_intervals = np.diff(peak_times)
                else:
                    print('Nur ein R-Peak gefunden. Herzfrequenz kann nicht berechnet werden.')
                    return None
            
            # Ausreißer-Filterung
            if len(rr_intervals) > 2:
                # Statistischer Ausreißer-Filter
                median_rr = np.median(rr_intervals)
                outlier_bound = outlier_threshold * median_rr
                valid_mask = np.abs(rr_intervals - median_rr) <= outlier_bound
                
                # Physiologische Grenzen
                physiological_mask = (rr_intervals >= min_rr_interval) & (rr_intervals <= max_rr_interval)
                
                # Kombiniere beide Filter
                final_mask = valid_mask & physiological_mask
                valid_rr_intervals = rr_intervals[final_mask]
            else:
                valid_rr_intervals = rr_intervals
            
            # Durchschnittliche Herzfrequenz berechnen
            if len(valid_rr_intervals) > 0:
                heart_rates = 60.0 / valid_rr_intervals
                avg_heart_rate = float(np.mean(heart_rates))
                return avg_heart_rate
            else:
                print('Alle RR-Intervalle wurden als Ausreißer klassifiziert.')
                return None
        
        except Exception as e:
            print(f'Fehler bei der Herzfrequenz-Berechnung: {str(e)}')
            return None

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