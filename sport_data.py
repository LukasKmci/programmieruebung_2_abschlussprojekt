# sport_data.py

from fitparse import FitFile
import numpy as np
import datetime



def get_field_value(record, field_name):

    # FIT-Datei einlesen
    fitfile = FitFile('{field_name}.fit')
    # Arrays für die Daten vorbereiten
    time = []
    velocity = []
    heartrate = []
    distance = []
    cadence = []
    power = []

    # Daten aus den Messages extrahieren
    for record in fitfile.get_messages('record'):
        # Einzelne Daten extrahieren    
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

    # Ergebnisse in NumPy-Arrays umwandeln
    velocity = np.array(velocity)
    heartrate = np.array(heartrate)
    distance = np.array(distance)
    cadence = np.array(cadence)
    power = np.array(power)
    #Zeitstempel in Zeit startend von 0s
    epoch = datetime.datetime(1970, 1, 1)
    time = np.array([(t - epoch).total_seconds() for t in time])