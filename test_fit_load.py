from sport_data import load_sports_data

print("Lade .fit-Dateien ...")
data = load_sports_data()
print(f"Geladen: {list(data.keys())}")
