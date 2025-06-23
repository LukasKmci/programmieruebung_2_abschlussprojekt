# sport_data.py

from fitparse import FitFile
import numpy as np
import datetime



class SportsDataLoader:
    def __init__(self, folder_path='activities/sports_data'):
        self.folder_path = folder_path

    def load_sports_data(self, file_name):
        fitfile = FitFile(f'{self.folder_path}/{file_name}.fit')
        time = []
        velocity = []
        heartrate = []
        distance = []
        cadence = []
        power = []

        for record in fitfile.get_messages('record'):
            record_data = {field.name: field.value for field in record}
            if 'timestamp' in record_data:
                time.append(record_data['timestamp'])
            if 'speed' in record_data:
                velocity.append(record_data['speed'])
            if 'heart_rate' in record_data:
                heartrate.append(record_data['heart_rate'])
            if 'distance' in record_data:
                distance.append(record_data['distance'])
            if 'cadence' in record_data:
                cadence.append(record_data['cadence'])
            if 'power' in record_data:
                power.append(record_data['power'])

        velocity = np.array(velocity)
        heartrate = np.array(heartrate)
        distance = np.array(distance)
        cadence = np.array(cadence)
        power = np.array(power)
        epoch = datetime.datetime(1970, 1, 1)
        time = np.array([(t - epoch).total_seconds() for t in time])

        return {
            'time': time,
            'velocity': velocity,
            'heartrate': heartrate,
            'distance': distance,
            'cadence': cadence,
            'power': power
        }

class calculate_sports_data:

    def calculate_calories():

    
    

if __name__ == "__main__":
    loader = SportsDataLoader()
    # Beispiel: Ersetze 'example_file' durch den Namen deiner .fit Datei (ohne .fit)
    data = loader.load_sports_data('example_file')
    print("Geladene Daten:")
    for key, value in data.items():
        print(f"{key}: {value[:5]}")  # Zeige die ersten 5 Werte jeder Kategorie

