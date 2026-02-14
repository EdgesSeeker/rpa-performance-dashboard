# RPA Performance System - Development Scratchpad

> **Purpose**: External memory for Claude across sessions. Update this constantly.

---

## 🎯 Current Sprint Goal
**Enhancement Phase** – MVP funktioniert! Jetzt: Quick Wins, Weekly Trends, Executive Summary

### MVP Status: ✅ KOMPLETT FERTIG
- [x] UiPath API connection working (OAuth, $expand=Robot)
- [x] Jobs synced to database (variable Zeiträume)
- [x] Utilization calculated (24/7 basis, nur abgeschlossene Tage)
- [x] Streamlit dashboard komplett:
  - [x] Filter (1 Tag / 7 Tage / 30 Tage / Eigener Bereich)
  - [x] Overview KPIs (Ø Utilization, Idle-Stunden, Success Rate, Business Impact)
  - [x] Bot Utilization Chart (Balken, Donald & Mickey)
  - [x] Timeline (Gantt Chart mit Tooltips)
  - [x] Leerlauf pro Tag (gemeinsamer Leerlauf beider Roboter, Dropdown pro Tag)
  - [x] Prozess-Statistik (Tabelle)
- [x] Excel export functional (Summary + Daily Breakdown)

### 🚀 Next Features (High Priority für Pitch)
- [ ] **Quick Wins Dashboard** - Automatische Optimierungs-Empfehlungen
- [ ] **Weekly Trends** - 4-Wochen-Vergleich mit Verbesserungs-Rate
- [ ] **Executive Summary** - Management-ready Excel-Sheet

---

## 📋 Current Task: Feature Enhancement (Quick Wins + Trends + Export)

### What We're Building
Drei High-Impact Features für Management-Pitch:
1. Quick Wins: Findet recurring idle patterns, empfiehlt Optimierungen
2. Weekly Trends: Zeigt Verbesserung über 4 Wochen
3. Executive Summary: 1-Page Management-Report im Excel

### Why This Matters
- MVP zeigt Daten → Enhancement zeigt EMPFEHLUNGEN
- Tool findet selbst Optimierungen im Wert von €X/Monat
- Rechtfertigt Investment, zeigt Fortschritt
- Management-ready: "Nicht nur messen, sondern verbessern"

### Architecture Decision
Integration in bestehendes Dashboard:
- Quick Wins: Neue Section oberhalb der KPIs
- Weekly Trends: Neue Section zwischen KPIs und Timeline
- Executive Summary: Neues Sheet in bestehendem Excel-Export

### Implementation Steps
- [ ] Phase 1: Quick Wins Backend (backend/services/quickwins_service.py)
  - Recurring idle pattern detection
  - Underutilized time window detection
  - € Impact calculation
- [ ] Phase 2: Weekly Trends Backend (backend/services/trends_service.py)
  - Weekly aggregation (ISO week)
  - Trend calculations
  - Week-over-week changes
- [ ] Phase 3: Frontend Integration (frontend/streamlit_app.py)
  - render_quickwins_section()
  - render_weekly_trends_section()
- [ ] Phase 4: Excel Enhancement (backend/services/export_service.py)
  - create_executive_summary_sheet()
- [ ] Phase 5: Testing & Polish

### Progress Log
```
[2026-02-14] - MVP komplett funktionsfähig
[2026-02-14] - Feature-Planning: Quick Wins, Trends, Executive Summary
[2026-02-14] - Review-Prompt erstellt, bereit für Cursor
[TODO] - Cursor Review durchführen
[TODO] - Implementation starten
```

---

## 💡 Learnings & Patterns

### What Works Well
```
✅ Robot-Namen aus HostMachineName (RPA-DONALD-001 → Donald)
✅ Filter-System mit Schnellauswahl (1/7/30 Tage)
✅ Leerlauf-Berechnung: gemeinsamer Leerlauf beider Roboter
✅ Timeline-Tooltips: Prozessname zuerst, dann Details
✅ Nur abgeschlossene Tage (verhindert falsche Idle-Werte)
```

### What Doesn't Work
```
⚠️ Keine Jobs über Mitternacht → Utilization kann >100% werden
→ Lösung: Jobs werden am Tag des Starts gezählt, nicht gesplittet
```

### Existing Data Model
```python
# Was wir schon haben und nutzen können:
Jobs:
  - job_key, robot_name, process_name
  - start_time, end_time, duration_seconds
  - state (Successful, Faulted)
  - host_machine_name (RPA-DONALD-001, RPA-MICKY-002)

DailyUtilization:
  - date, robot_name
  - utilization_percent, idle_hours
  - run_count, success_count, error_count

# Leerlauf-Daten werden on-the-fly berechnet
# aus Jobs-Tabelle (gemeinsame Lücken)
```

---

## 📊 Quick Reference Data

### Environment (Confirmed)
```
Tenant: defaultenet
Org: lackmann
Orchestrator: https://cloud.uipath.com/lackmann/defaultenet/orchestrator_/
Robots: Donald (RPA-DONALD-001), Mickey (RPA-MICKY-002)
```

### UiPath API Endpoints Used
```
GET /odata/Jobs?$filter=StartTime ge {date}Z&$expand=Robot
→ Returns jobs with robot details
```

### Database Schema
```sql
-- Jobs table (exists, populated)
CREATE TABLE jobs (
    job_key TEXT UNIQUE,
    robot_name TEXT,  -- "Donald" or "Mickey"
    host_machine_name TEXT,  -- "RPA-DONALD-001" etc
    process_name TEXT,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    duration_seconds INTEGER,
    state TEXT  -- Successful, Faulted
);

-- DailyUtilization table (exists, populated)
CREATE TABLE daily_utilization (
    date DATE,
    robot_name TEXT,
    utilization_percent REAL,
    idle_hours REAL,
    run_count INTEGER,
    success_count INTEGER,
    error_count INTEGER
);
```

### Run Commands
```bash
# Sync Jobs
python -m backend.sync_jobs

# Calculate Utilization
python -m backend.calculate_utilization

# Start Dashboard
streamlit run frontend/streamlit_app.py

# Export Excel (via Dashboard Button)
```

---

## 🚀 Next Session Planning

### When I Return, Start Here:
1. Open Cursor in rpa-performance-system project
2. Check: Dashboard is running? (`streamlit run frontend/streamlit_app.py`)
3. Verify: Database has data? (at least 7 days)
4. Start Cursor Review (CURSOR_REVIEW_PROMPT.md in Plan Mode, Opus 4.5)
5. After Review: Implementation (CURSOR_IMPLEMENTATION_PROMPT.md)

### Questions to Ask Cursor:
- [ ] Is the Quick Wins algorithm feasible with our data model?
- [ ] Can we group by ISO week in SQLite/pandas?
- [ ] Is 3 hours realistic for all 3 features?
- [ ] Any data limitations we should know about?

### Commands to Run Before Implementation:
```bash
# Verify Dashboard works
streamlit run frontend/streamlit_app.py

# Check if we have enough data
sqlite3 data/rpa_performance.db "SELECT COUNT(*), MIN(date), MAX(date) FROM daily_utilization;"

# Should show: 7+ days of data
```

---

## 📈 Success Metrics Tracking

### Current Status (Update After Each Feature)
| Feature | Status | Notes |
|---------|--------|-------|
| **MVP** | ✅ | Komplett funktionsfähig |
| Quick Wins Dashboard | ⚪ | Not started |
| Weekly Trends | ⚪ | Not started |
| Executive Summary | ⚪ | Not started |

🟢 = Done  
🟡 = In Progress  
🔴 = Blocked  
⚪ = Not Started

---

**Last Updated**: 2026-02-14  
**Status**: MVP Complete, Ready for Enhancement Features  
**Next**: Cursor Review → Implementation → Testing
