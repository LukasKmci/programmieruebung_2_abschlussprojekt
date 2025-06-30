from pathlib import Path

# Ziel: Erstellen der SQL-Erweiterung zur Speicherung von FIT-Dateien pro Benutzer
sports_sessions_sql = """
CREATE TABLE IF NOT EXISTS sports_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    file_name TEXT,
    timestamp TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
"""

# Datei json_to_sql erweitern
sql_file_path = Path("/mnt/data/json_to_sql_extended.py")
with sql_file_path.open("w", encoding="utf-8") as f:
    f.write("""import json
import sqlite3

with open("data/person_db.json", "r", encoding="utf-8") as f:
    person_data = json.load(f)

conn = sqlite3.connect("personen.db")
cursor = conn.cursor()

# Bestehende Tabellen
cursor.execute(\"\"\"
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    firstname TEXT,
    lastname TEXT,
    date_of_birth INTEGER,
    gender TEXT,
    picture_path TEXT
)
\"\"\")

cursor.execute(\"\"\"
CREATE TABLE IF NOT EXISTS ekg_tests (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    date TEXT,
    result_link TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
)
\"\"\")

# NEU: Sport-Sessions
cursor.execute(\"\"\"
""" + sports_sessions_sql.strip() + """
\"\"\")

conn.commit()

for person in person_data:
    cursor.execute(\"\"\"
    INSERT OR REPLACE INTO users (id, firstname, lastname, date_of_birth, gender, picture_path)
    VALUES (?, ?, ?, ?, ?, ?)
    \"\"\", (
        person["id"],
        person["firstname"],
        person["lastname"],
        person["date_of_birth"],
        person["gender"],
        person["picture_path"]
    ))

    for test in person.get("ekg_tests", []):
        cursor.execute(\"\"\"
        INSERT OR REPLACE INTO ekg_tests (id, user_id, date, result_link)
        VALUES (?, ?, ?, ?)
        \"\"\", (
            test["id"],
            person["id"],
            test["date"],
            test["result_link"]
        ))

conn.commit()
conn.close()
""")

sql_file_path.name  # Rückgabe des neuen Dateinamens zur Referenz für den Nutzer

