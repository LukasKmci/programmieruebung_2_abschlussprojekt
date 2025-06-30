# sport_data.py
import numpy as np
import datetime
import os
import glob
from fitparse import FitFile

def load_sports_data():
    """Lädt alle .fit Dateien aus dem data/sports_data Ordner"""
    sports_data_path = "data/sports_data"
    all_data = {}
    
    if not os.path.exists(sports_data_path):
        print(f"Ordner {sports_data_path} existiert nicht!")
        return all_data
    
    # Suche nach .fit Dateien
    fit_files = glob.glob(os.path.join(sports_data_path, "*.fit"))
    
    for fit_file in fit_files:
        try:
            filename = os.path.basename(fit_file)
            print(f"Lade {filename}...")
            
            # Lade die .fit Datei
            fitfile = FitFile(fit_file)
            
            # Initialisiere Datenlisten
            data = {
                'file_name': filename,
                'time': [],
                'velocity': [],
                'heartrate': [],
                'distance': [],
                'cadence': [],
                'power': [],
                'altitude': [],
                'temperature': []
            }
            
            # Extrahiere Daten aus der .fit Datei
            for record in fitfile.get_messages('record'):
                record_data = {}
                
                # Sammle alle Feldwerte
                field_map = {
                    "timestamp": "timestamp",
                    "heart_rate": "heartrate",
                    "speed": "velocity",
                    "distance": "distance",
                    "cadence": "cadence",
                    "power": "power",
                    "altitude": "altitude",
                    "temperature": "temperature"
}
                for field in record:
                    if field.name in field_map:
                        mapped_name = field_map[field.name]
                        record_data[mapped_name] = field.value
                
                # Füge Timestamp hinzu (erforderlich)
                if 'timestamp' in record_data:
                    # Konvertiere timestamp zu Unix-Zeit
                    if hasattr(record_data['timestamp'], 'timestamp'):
                        data['time'].append(record_data['timestamp'].timestamp())
                    else:
                        # Falls es bereits ein Unix-Timestamp ist
                        data['time'].append(float(record_data['timestamp']))
                    
                    # Füge andere Werte hinzu (mit Standardwerten falls nicht vorhanden)
                    for key in ['velocity', 'heartrate', 'distance', 'cadence', 'power', 'altitude', 'temperature']:
                        data[key].append(record_data.get(key, 0))

            
            # Konvertiere Listen zu NumPy Arrays für bessere Performance
            for key in data.keys():
                if key != 'file_name' and isinstance(data[key], list):
                    data[key] = np.array(data[key])
            
            # Entferne leere Datensätze (nur wenn Zeit vorhanden ist)
            if len(data['time']) > 0:
                all_data[filename] = data
                print(f"✓ {filename} erfolgreich geladen ({len(data['time'])} Datenpunkte)")
            else:
                print(f"✗ {filename} enthält keine gültigen Zeitdaten")
                
        except Exception as e:
            all_data[os.path.basename(fit_file)] = None  # sichtbar machen im Debug
            import traceback
            traceback.print_exc()
            continue
    
    print(f"Insgesamt {len(all_data)} .fit Dateien geladen")
    return all_data


def filter_data_by_time_range(data, start_percent, end_percent):
    """Filtert die Daten basierend auf dem Zeitbereich (in Prozent)"""
    if len(data['time']) == 0:
        return data
    
    total_time = data['time'][-1] - data['time'][0]
    start_time = data['time'][0] + (total_time * start_percent / 100)
    end_time = data['time'][0] + (total_time * end_percent / 100)
    
    # Finde Indizes für den gewählten Zeitbereich
    time_mask = (data['time'] >= start_time) & (data['time'] <= end_time)
    
    filtered_data = {}
    for key, values in data.items():
        if key == 'file_name':
            filtered_data[key] = values
        elif isinstance(values, (np.ndarray, list)) and len(values) > 0:
            # Stelle sicher, dass die Daten die gleiche Länge wie time haben
            if len(values) == len(data['time']):
                filtered_data[key] = values[time_mask]
            else:
                # Falls die Daten nicht die gleiche Länge haben, behalte sie unverändert
                filtered_data[key] = values
        else:
            filtered_data[key] = values
    
    return filtered_data

def format_duration(seconds):
    """Formatiert Sekunden zu Stunden, Minuten und Sekunden"""
    if seconds == 0:
        return "0 min"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    remaining_seconds = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}h {minutes}min {remaining_seconds}s"
    elif minutes > 0:
        return f"{minutes}min {remaining_seconds}s"
    else:
        return f"{remaining_seconds}s"

def calculate_filtered_stats(filtered_data):
    """Berechnet die Statistiken für die gefilterten Daten"""

    def clean_data(array, min_val=None, max_val=None):
        """Hilfsfunktion zur Bereinigung von NaN, None und Grenzwerten"""
        if len(array) == 0:
            return np.array([])
        array = array[~np.isnan(array)]
        if min_val is not None:
            array = array[array >= min_val]
        if max_val is not None:
            array = array[array <= max_val]
        return array

    if len(filtered_data.get('time', [])) == 0:
        return {
            'duration_seconds': 0,
            'total_distance_km': 0,
            'avg_speed_kmh': 0,
            'max_speed_kmh': 0,
            'avg_heartrate': 0,
            'max_heartrate': 0,
            'avg_cadence': 0,
            'max_cadence': 0,
            'avg_power': 0,
            'max_power': 0,
            'avg_temperature': 0,
            'max_temperature': 0,
            'avg_altitude': 0,
            'max_altitude': 0,
            'min_altitude': 0,
        }

    duration_seconds = filtered_data['time'][-1] - filtered_data['time'][0]

    distance = clean_data(filtered_data.get('distance', []))
    total_distance_km = (distance[-1] - distance[0]) / 1000 if len(distance) > 1 else 0

    velocity = clean_data(filtered_data.get('velocity', []), min_val=0)
    avg_speed_kmh = np.mean(velocity) * 3.6 if len(velocity) > 0 else 0
    max_speed_kmh = np.max(velocity) * 3.6 if len(velocity) > 0 else 0

    heartrate = clean_data(filtered_data.get('heartrate', []), min_val=30, max_val=220)
    avg_heartrate = np.mean(heartrate) if len(heartrate) > 0 else 0
    max_heartrate = np.max(heartrate) if len(heartrate) > 0 else 0

    cadence = clean_data(filtered_data.get('cadence', []), min_val=0)
    avg_cadence = np.mean(cadence) if len(cadence) > 0 else 0
    max_cadence = np.max(cadence) if len(cadence) > 0 else 0

    power = clean_data(filtered_data.get('power', []), min_val=0)
    avg_power = np.mean(power) if len(power) > 0 else 0
    max_power = np.max(power) if len(power) > 0 else 0

    temperature = clean_data(filtered_data.get('temperature', []), min_val=-20, max_val=60)
    avg_temperature = np.mean(temperature) if len(temperature) > 0 else 0
    max_temperature = np.max(temperature) if len(temperature) > 0 else 0

    altitude = clean_data(filtered_data.get('altitude', []), min_val=-200)
    avg_altitude = np.mean(altitude) if len(altitude) > 0 else 0
    max_altitude = np.max(altitude) if len(altitude) > 0 else 0
    min_altitude = np.min(altitude) if len(altitude) > 0 else 0

    return {
        'duration_seconds': duration_seconds,
        'total_distance_km': total_distance_km,
        'avg_speed_kmh': avg_speed_kmh,
        'max_speed_kmh': max_speed_kmh,
        'avg_heartrate': avg_heartrate,
        'max_heartrate': max_heartrate,
        'avg_cadence': avg_cadence,
        'max_cadence': max_cadence,
        'avg_power': avg_power,
        'max_power': max_power,
        'avg_temperature': avg_temperature,
        'max_temperature': max_temperature,
        'avg_altitude': avg_altitude,
        'max_altitude': max_altitude,
        'min_altitude': min_altitude,
    }

def get_time_range_info(data, start_percent, end_percent):
    """Gibt Informationen über den ausgewählten Zeitbereich zurück"""
    if len(data['time']) == 0:
        return None
    
    total_time = data['time'][-1] - data['time'][0]
    start_time_offset = total_time * start_percent / 100
    end_time_offset = total_time * end_percent / 100
    
    start_timestamp = data['time'][0] + start_time_offset
    end_timestamp = data['time'][0] + end_time_offset
    
    return {
        'start_timestamp': start_timestamp,
        'end_timestamp': end_timestamp,
        'duration_seconds': end_timestamp - start_timestamp,
        'start_datetime': datetime.datetime.fromtimestamp(start_timestamp),
        'end_datetime': datetime.datetime.fromtimestamp(end_timestamp)
    }