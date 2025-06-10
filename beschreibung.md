# Grundaufgaben

## ✅ **Pflichtaufgaben mit Umsetzungshinweisen**

| Aufgabe                                                                              | Punkte | Umsetzungs-Hinweis                                                                              |
| ------------------------------------------------------------------------------------ | ------ | ----------------------------------------------------------------------------------------------- |
| 🔹 Geburtsjahr, Name und Bild der Personen wird angezeigt                            | 2      | Bereits vorhanden – mit `person["date_of_birth"]`, `["firstname"]`, `["picture_path"]` anzeigen |
| 🔹 Auswahlmöglichkeit für Tests, sofern mehr als ein Test vorhanden ist              | 4      | Per `st.selectbox()` mit allen `ekg_tests` einer Person                                         |
| 🔹 Anzeigen des Testdatums und der Gesamtlänge der Zeitreihe in Minuten              | 4      | Testdatum: `ekg_obj.date`; Dauer: `(last_time - first_time) / 60000` in Minuten                 |
| 🔹 EKG-Daten effizient einlesen (z. B. Downsampling, Cache, kein mehrfaches Rechnen) | 2      | z. B. `@st.cache_data`, `.iloc[::5]` Downsampling, nur einmalige Peak-Erkennung                 |
| 🔹 Sinnvolle Berechnung der Herzrate über den gesamten Zeitraum                      | 2      | Zählen der Peaks → HR = (Anzahl Peaks / Dauer in Minuten)                                       |
| 🔹 Zeitbereich für Plot ist auswählbar, nutzerfreundlich                             | 2      | z. B. über `st.slider()` mit Sekundenbereich (0–Gesamtdauer)                                    |
| 🔹 Stil: Namenskonventionen, saubere Modulstruktur, keine unnötigen Altlasten        | 4      | z. B. Snake-Case für Funktionen, OOP nur wenn sinnvoll, keine überladenen Klassen               |
| 🔹 Docstrings für Klassen, Methoden und Funktionen                                   | 2      | Format z. B. per PEP257 / Google Style: `"""Beschreibung..."""`                                 |
| 🔹 Design für Desktop optimiert & optisch ansprechend                                | 2      | Streamlit-Layout: `st.set_page_config(...)`, gezielte Verwendung von Columns                    |
| 🔹 Deployment auf Heroku oder Streamlit Cloud inkl. `requirements.txt`               | 4      | Verwende `pip freeze > requirements.txt` + `streamlit` auf Streamlit Cloud                      |
| 🔹 Neue Personen und Tests können hinzugefügt werden                                 | 4      | Formular mit `st.text_input()` + Datei-Upload + JSON-Erweiterung                                |
| 🔹 Bestehende Personen können editiert werden (Name, Geburtsjahr, Bild etc.)         | 4      | Auswahlbox → Felder vorausfüllen → Änderungen speichern                                         |

---

## 🧠 Empfehlung zur Umsetzung

1. **Pflichtteile zuerst fertigstellen & testen**
2. **Entwicklung modular halten:** `person_handler.py`, `ekg_data.py`, `ui_helpers.py` usw.
3. **Deployment früh testen**, nicht ganz am Schluss
4. **Mit `@st.cache_data` oder `@st.experimental_memo`** Performance optimieren

---

# freie Aufgaben
## 🔐 **Login mit verschiedenen Niveaus**

* **Ziele:**

  * Admin (zb. Sportmediziner) & Benutzer (Kunde) mit unterschiedlichen Rechten
  * Admin kann benutzer löschen, alle Benutzer anschauen, einzelne Trainings bzw. EKGs löschen
  * Benutzerbasierte Datenfilterung
* **Empfohlenes Paket:** [`streamlit-authenticator`](https://github.com/mkhorasani/streamlit-authenticator)
* **Schwierigkeit:** 🟡 *mittel*
* **Hinweis:** Streamlit hat keinen eingebauten Login – `streamlit-authenticator` bietet passwortgeschützte Benutzer, Rollen, Sitzungsverwaltung.

---

## 👤 **Benutzerkonto erstellen**

* Felder: Vorname, Nachname, Geburtsdatum, Geschlecht, Bild
* Speicherung in SQLite
* **Schwierigkeit:** 🟢 *leicht bis mittel*
* **Tools:** `sqlite3`, `sqlmodel` oder `sqlalchemy`
* **Hinweis:** Bild-Dateien (z. B. JPEG) kannst du im `data/pictures/`-Ordner speichern, im SQL nur den Pfad ablegen.

---

## 🧠 **Datenbank: SQLite**

* Benutzer- und EKG-Daten verwalten
* **Schwierigkeit:** 🟢 *leicht*
* **Tipp:** Nutze z. B. `sqlmodel` (einfacher als `sqlalchemy`) – sauber, typsicher, ORM-Features

---

## 📈 **EKG-Analyse – Erweiterungen**

### ➕ Zeiteingabe für X-Achse

* z. B. `st.slider` oder `st.number_input` für Start/Endzeit (in ms oder s)
* **Schwierigkeit:** 🟢 *leicht*

### ➕ Auswahl Plot: Peaks oder Durchschnitt

* Umschaltbar per `st.radio()`
* Durchschnitt berechnen mit z. B. `rolling().mean()`
* **Schwierigkeit:** 🟢 *leicht*

### ➕ Neue `.ekg.txt`-Files einlesen

* Automatisches Scannen neuer Dateien, z. B. aus `data/ekg_data/`
* Gleiches Format wie `.fit` vorbereiten
* **Schwierigkeit:** 🟢 *leicht bis mittel*

---

## 🏃‍♂️ **Sportanalyse – .fit-Dateien**

### 📥 .fit einlesen

* **Wichtige Datenfelder:**

  * HR, Zeitstempel, Geschwindigkeit, Distanz, Höhe, GPS, Leistung, Kadenz
* **Tool:** [`fitparse`](https://pypi.org/project/fitparse/)
* **Schwierigkeit:** 🟡 *mittel*
* **Tipp:** ggf. Wrapper-Klasse bauen für Fit-File-Import → DataFrame

---

## 🗺️ **GPS & Heatmap mit Karte**

* Darstellung per `pydeck` oder `folium`
* Farbcodierung für „Häufigkeit“ = Heatmap-Logik (Clustering nach Ort)
* Bereichslogik nötig (z. B. Rundung auf 4 Nachkommastellen)
* **Schwierigkeit:** 🔴 *anspruchsvoll*
* **Tipp:** Heatmaps mit `folium.plugins.HeatMapWithTime` möglich

---

## 📥 Automatischer Import: `.fit` → Benutzerzuordnung

* Beim Upload speichert App:

  * Dateiname
  * Pfad
  * Timestamp
  * Benutzer-ID
* **Schwierigkeit:** 🟡 *mittel*

---

## 🔚 **Zusammenfassung nach Aufwand**

| Feature                                   | Schwierigkeit    |
| ----------------------------------------- | ---------------- |
| Login mit Rollen                          | 🟡 Mittel        |
| Benutzerkonto erstellen + speichern       | 🟢 Leicht        |
| SQLite-Anbindung                          | 🟢 Leicht        |
| Zeitwahl im EKG-Plot                      | 🟢 Leicht        |
| Peak- / Durchschnittsanalyse wechseln     | 🟢 Leicht        |
| Neue EKG-Dateien einlesen                 | 🟢 Leicht-Mittel |
| `.fit`-Dateien parsen                     | 🟡 Mittel        |
| GPS-Heatmap mit Farben für Wiederholungen | 🔴 Anspruchsvoll |
| Import-Workflow mit Benutzerbindung       | 🟡 Mittel        |

---

## ✅ Empfehlung für den nächsten Schritt:

1. **Login & SQLite einbauen** → Grundlage für alles Weitere
2. **`.fit`-Importer schreiben & EKG-Dateien dynamisch laden**
3. **EKG-Datenbank verknüpfen mit Benutzerprofil**
4. **Karten & Heatmaps als Erweiterung**

---
## weitere Ideen
* Api connect mit Garmin
