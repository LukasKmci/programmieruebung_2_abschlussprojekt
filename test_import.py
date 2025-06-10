import json
import sqlite3

# 1. JSON-Daten einlesen
with open("data/person_db.json", "r", encoding="utf-8") as f:
    json_data = json.load(f)

# 2. Verbindung zur Datenbank
conn = sqlite3.connect("personen.db")
cursor = conn.cursor()

# 3. Alle Personen aus der Datenbank abrufen
cursor.execute("SELECT id, firstname, lastname, date_of_birth, gender, picture_path FROM users")
db_persons = cursor.fetchall()

# 4. Vergleich: Anzahl Personen
if len(json_data) != len(db_persons):
    print(f"❌ Anzahl Personen unterschiedlich: JSON = {len(json_data)}, DB = {len(db_persons)}")
else:
    print(f"✅ Anzahl Personen stimmt überein: {len(db_persons)}")

# 5. Vergleich: jede Person einzeln prüfen
errors = 0
for person in json_data:
    cursor.execute("SELECT * FROM users WHERE id = ?", (person["id"],))
    result = cursor.fetchone()
    if not result:
        print(f"❌ Person mit ID {person['id']} nicht gefunden")
        errors += 1

# 6. EKG-Tests prüfen (optional)
cursor.execute("SELECT COUNT(*) FROM ekg_tests")
ekg_count_db = cursor.fetchone()[0]

ekg_count_json = sum(len(p.get("ekg_tests", [])) for p in json_data)

if ekg_count_db != ekg_count_json:
    print(f"❌ Anzahl EKG-Tests unterschiedlich: JSON = {ekg_count_json}, DB = {ekg_count_db}")
else:
    print(f"✅ Anzahl EKG-Tests stimmt überein: {ekg_count_db}")

conn.close()

if errors == 0:
    print("🎉 Alle Einträge korrekt importiert!")
else:
    print(f"⚠️ {errors} Fehler gefunden.")
