# freie Aufgaben
## 🔐 **Login mit verschiedenen Niveaus**

* **Ziele:**

  * Admin (zb. Sportmediziner) & Benutzer (Kunde) mit unterschiedlichen Rechten
  * Admin kann benutzer löschen, alle Benutzer anschauen, einzelne Trainings bzw. EKGs löschen
  * Benutzerbasierte Datenfilterung
* **Empfohlenes Paket:** [`streamlit-authenticator`](https://github.com/mkhorasani/streamlit-authenticator)
* **Schwierigkeit:** 🟡 *mittel*
* **Hinweis:** Streamlit hat keinen eingebauten Login – `streamlit-authenticator` bietet passwortgeschützte Benutzer, Rollen, Sitzungsverwaltung.
* **Problem:** Streamlit 1.12 unterstütz das nicht, hierfür wird mindestens 1.18 benötigt.

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
| Login mit verschiedenen Niveaus           | 🟡 Mittel        |
| Benutzerkonto erstellen + speichern       | 🟢 Leicht        |
| SQLite-Anbindung                          | 🟢 Leicht        |
| Analyse Leistungsdaten + Plot             | 🟢 Leicht        |
| Neue `.fit` einlesen                      | 🟢 Leicht-Mittel |
| Import-Workflow für `.fit` Dateien mit Benutzerbindung       | 🟡 Mittel        |
| GPS-Heatmap mit Farben für Wiederholungen | 🔴 Anspruchsvoll |

