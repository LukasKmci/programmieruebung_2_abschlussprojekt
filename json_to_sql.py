import json
import sqlite3

with open("data/person_db.json", "r", encoding="utf-8") as f:
    person_data = json.load(f)

conn = sqlite3.connect("personen.db")
cursor = conn.cursor()

# Tabelle erstellen
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    firstname TEXT,
    lastname TEXT,
    date_of_birth INTEGER,
    gender TEXT,
    picture_path TEXT
)
""")

# EKG-Tabelle
cursor.execute("""
CREATE TABLE IF NOT EXISTS ekg_tests (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    date TEXT,
    result_link TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
)
""")

conn.commit()


for person in person_data:
    # Person einfügen
    cursor.execute("""
    INSERT OR REPLACE INTO users (id, firstname, lastname, date_of_birth, gender, picture_path)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        person["id"],
        person["firstname"],
        person["lastname"],
        person["date_of_birth"],
        person["gender"],
        person["picture_path"]
    ))

    # EKG-Tests einfügen
    for test in person.get("ekg_tests", []):
        cursor.execute("""
        INSERT OR REPLACE INTO ekg_tests (id, user_id, date, result_link)
        VALUES (?, ?, ?, ?)
        """, (
            test["id"],
            person["id"],
            test["date"],
            test["result_link"]
        ))

conn.commit()
conn.close()
