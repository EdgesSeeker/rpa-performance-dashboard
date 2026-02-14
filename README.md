# RPA Performance Monitoring System

Unabhängiges Performance-Monitoring für UiPath RPA Bots: Auslastung, Idle-Zeiten, Excel-Export.

## Setup

```bash
cd rpa-performance-system
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

Kopiere `.env.example` nach `.env` und trage deine UiPath-Credentials ein (falls noch nicht vorhanden).

**UiPath Konfiguration:**
- Token-URL: `https://cloud.uipath.com/{org}/identity_/connect/token`
- App: Confidential, Application scope(s): OR.Jobs (und OR.Folders falls mehrere Folders)
- Tenant: `DefaultTenant` (nicht defaultenet)
- Folder: `UIPATH_FOLDER_ID` in .env (z. B. 5719144 für Lackmann) – bei "A folder is required" nötig
- Optional: `ROBOT_NAME_MAP={"Unattended": "Donald"}` in .env für Anzeigenamen der Roboter

## Auf dem Firmenrechner (oder anderem PC) lokal ausführen

Du kannst das Projekt 1:1 auf deinen Arbeitslaptop kopieren und dort **lokal** starten – ohne Deploy, nur für dich zum Vorzeigen.

1. **Projekt kopieren**  
   Gesamten Ordner `rpa-performance-system` (inkl. `backend/`, `frontend/`, `data/`, `.env`, `requirements.txt`) auf den Firmenrechner kopieren (USB-Stick, Netzlaufwerk, Cloud, Git, …).

2. **Python & Abhängigkeiten**  
   Auf dem Firmenrechner:
   ```bash
   cd rpa-performance-system
   python -m venv venv
   venv\Scripts\activate    # Windows
   pip install -r requirements.txt
   ```

3. **`.env` prüfen**  
   Die `.env` muss die gleichen UiPath-Zugangsdaten enthalten (Client-ID, Secret, Folder-ID usw.). Ohne gültige `.env` funktioniert der Sync nicht.

4. **Einmalig: DB füllen**  
   ```bash
   python -m backend.sync_jobs
   python -m backend.calculate_utilization
   ```

5. **Dashboard starten**  
   ```bash
   streamlit run frontend/streamlit_app.py
   ```  
   Im Browser `http://localhost:8501` öffnen – die App läuft nur auf diesem Rechner. Später (mit Go der Chefs) kann man dieselbe App z.B. auf einem Server oder in der Cloud hosten und einen Link teilen.

---

## Erste Schritte

1. **Datenbank initialisieren**
   ```bash
   python init_db.py
   ```

2. **API testen**
   ```bash
   python test_api.py
   ```

3. **Jobs synchronisieren (letzte 7 Tage)**
   ```bash
   python -m backend.sync_jobs
   ```

4. **Utilization berechnen**
   ```bash
   python -m backend.calculate_utilization
   ```

5. **Dashboard starten**
   ```bash
   streamlit run frontend/streamlit_app.py
   ```

## Deploy auf Streamlit Community Cloud (kostenlos)

Die App kann **kostenlos** auf [Streamlit Community Cloud](https://share.streamlit.io) gehostet werden. Dann reicht am Präsentationsrechner die URL im Browser – keine Python-Installation, keine Admin-Rechte.

1. **Anmeldung:** [share.streamlit.io](https://share.streamlit.io) → mit GitHub anmelden.
2. **New app:**
   - **Repository:** `DEIN_USERNAME/DEIN_REPO_NAME`
   - **Branch:** `main`
   - **Main file path:** `frontend/streamlit_app.py`
   - **App URL:** z. B. `rpa-performance-dashboard` → z. B. `https://rpa-performance-dashboard.streamlit.app`
3. **Secrets:** In der App unter **Settings → Secrets** die UiPath-Zugangsdaten eintragen (Key-Value oder TOML). Die App liest sie als Umgebungsvariablen. Beispiel (Werte durch echte ersetzen):
   ```
   UIPATH_CLIENT_ID = "deine-client-id"
   UIPATH_CLIENT_SECRET = "dein-secret"
   UIPATH_ORG_SLUG = "dein-org-slug"
   UIPATH_TENANT_NAME = "DefaultTenant"
   UIPATH_FOLDER_ID = "5719144"
   ```
4. **Deploy:** Nach „Deploy“ baut Streamlit die App (1–2 Min.). Danach einmal **„Daten von UiPath laden“** in der Sidebar klicken, damit die DB gefüllt wird (auf der Cloud ist das Dateisystem ephemeral – nach Neustart/Sleep ist die DB wieder leer).

## Projektstruktur

- `backend/clients/uipath_client.py` – UiPath API (OAuth, Jobs)
- `backend/database.py` – SQLite, Models
- `backend/sync_jobs.py` – Job-Sync
- `backend/calculate_utilization.py` – Auslastungsberechnung
- `frontend/streamlit_app.py` – Dashboard
- `data/rpa_performance.db` – SQLite-Datenbank
- `exports/` – Excel-Exporte
