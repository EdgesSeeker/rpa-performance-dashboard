# Projektstand – RPA Performance Monitoring System

**Kurzfassung:** Unabhängiges Performance-Dashboard für UiPath RPA Bots (z. B. Donald/Mickey). Zeigt Auslastung, Idle-Zeiten, Timeline, Quick Wins und Excel-Export für Management und Kapazitätsplanung.

---

## Aktueller Funktionsumfang (eine Seite)

| Bereich | Inhalt |
|--------|--------|
| **Übersicht** | KPIs: Ø Utilization %, Leerlaufstunden, Success Rate, Business Impact (Idle in €) |
| **Wochen-Vergleich** | Entwicklung der letzten Wochen (Auslastung, Idle-Reduktion, Impact €), Tabelle + Linienchart |
| **Utilization pro Robot** | Bar-Chart Auslastung pro Robot (24h-Basis) |
| **Timeline** | Gantt-ähnliche Ansicht: Jobs nach Robot (Plotly Timeline) |
| **Leerlauf pro Tag** | Pro Tag: Leerlauf Donald + Mickey, expandierbare Tabelle mit Jobs/Leerlauf-Zeiten |
| **Quick Wins** | Automatisch erkannte Optimierungen: Recurring Idle, unterlastete Zeitfenster, Potential h/Woche und €/Monat |
| **Excel-Export** | Executive Summary / Bericht als Excel-Download |
| **Prozess-Detail** | Prozess-Statistik (Läufe, Success Rate, Ø/Min/Max Dauer), Tabelle + 3 Plotly-Charts |

---

## Technik

- **Backend:** Python 3.11+, FastAPI nicht zwingend; Kern: SQLite, SQLAlchemy, UiPath API (httpx, OAuth 2.0)
- **Frontend:** Streamlit (eine Seite, Sidebar: Zeitraum, „Daten von UiPath laden“)
- **Daten:** SQLite (`data/rpa_performance.db`), Tabellen `jobs`, `daily_utilization`
- **UiPath:** Cloud Orchestrator, Jobs-API; Konfiguration über `.env` (Client-ID, Secret, Org, Tenant, Folder-ID)

---

## Lokal starten

1. **Umgebung**
   ```bash
   cd rpa-performance-system
   python -m venv venv
   venv\Scripts\activate   # Windows
   pip install -r requirements.txt
   ```
2. **Konfiguration**  
   `.env.example` nach `.env` kopieren und UiPath-Zugangsdaten eintragen.
3. **DB füllen**
   ```bash
   python -m backend.sync_jobs
   python -m backend.calculate_utilization
   ```
4. **Dashboard**
   ```bash
   streamlit run frontend/streamlit_app.py
   ```
   Browser: `http://localhost:8501`

---

## GitHub & Deploy (Streamlit Community Cloud)

- **Repo:** Projekt ist mit `.gitignore` vorbereitet (`.env`, `*.db`, `venv/`, `exports/` werden nicht committed). Repo anlegen, `git add` / `commit` / `remote` / `push`.
- **Streamlit Community Cloud:** [share.streamlit.io](https://share.streamlit.io) → mit GitHub anmelden → New app → Repository/Branch angeben, **Main file path:** `frontend/streamlit_app.py`.
- **Secrets:** In der App unter Settings → Secrets die UiPath-Variablen eintragen (`UIPATH_CLIENT_ID`, `UIPATH_CLIENT_SECRET`, `UIPATH_ORG_SLUG`, `UIPATH_TENANT_NAME`, `UIPATH_FOLDER_ID`).
- **„Daten laden“-Button:** In der Sidebar „Daten von UiPath laden“ klicken → Sync (30 Tage) + Utilization werden ausgeführt, Cache geleert, Seite zeigt danach die neuen Daten. Auf der Cloud ist das Dateisystem ephemeral; nach Neustart/Sleep einmalig erneut „Daten laden“ klicken (z. B. vor einer Präsentation).

---

## Nächste Schritte (optional)

- **Scheduler:** Täglicher Sync + Utilization (z. B. APScheduler oder Cron) für frische Daten ohne manuellen Klick.
- **Alerts:** Benachrichtigungen bei Auslastung unter Schwellwert oder Fehlern.
- **Spätere Erweiterungen:** Weitere Unterseiten, Filter nach Prozess/Robot, längere Historie.

---

*Stand: 2026-02-14*
