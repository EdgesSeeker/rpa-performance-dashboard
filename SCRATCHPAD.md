# RPA Performance System - Development Scratchpad

> **Purpose**: External memory for Claude across sessions. Update this constantly.

---

## Current Sprint Goal
**MVP Demo-Ready** – Minimal version: API + DB + Sync + Utilization + Streamlit + Excel

### Must-Have Features
- [ ] UiPath API connection working
- [ ] Jobs synced to database (last 7 days)
- [ ] Utilization calculated (24/7 basis)
- [ ] Streamlit dashboard: Overview KPIs, Bot chart, Timeline (Gantt), Process stats
- [ ] Excel export functional

---

## Current Task: Project Setup Complete – Next: API + DB + Dashboard

### Progress Log
- Project structure created (rpa-performance-system)
- .env, requirements.txt, README, CLAUDE.md, SCRATCHPAD.md in place
- Next: database.py, uipath_client.py, sync_jobs, calculate_utilization, streamlit_app

---

## Environment (confirmed)
- **Tenant**: defaultenet
- **Org**: lackmann
- **Orchestrator**: https://cloud.uipath.com/lackmann/defaultenet/orchestrator_/

---

## Quick Reference
- DB: `data/rpa_performance.db`, Jobs + DailyUtilization
- Run: `python init_db.py` → `python test_api.py` → `python -m backend.sync_jobs` → `python -m backend.calculate_utilization` → `streamlit run frontend/streamlit_app.py`
