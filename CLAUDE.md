# RPA Performance Monitoring System - Project Context

## Project Overview
Building an independent performance intelligence system for UiPath RPA bots to optimize utilization, track performance trends, and enable data-driven capacity planning. Target: Management pitch in 1-2 weeks with live demo.

## Business Context
- **Industry**: Energy sector (Wilken Energy software)
- **Current State**: 2-3 robots, 39 processes, 29 active triggers
- **Pain Point**: Bots stopping each other, unknown idle times, no performance visibility
- **Goal**: Maximize bot utilization (currently ~70%, target 85%), prove ROI to management

## Technical Environment
- **RPA Platform**: UiPath Cloud Orchestrator
- **Bot Operation**: 24/7 (not 9-5)
- **Infrastructure**: Windows Servers
- **Development**: Solo developer with Cursor AI
- **Timeline**: MVP in 5-19 days

## Architecture Decisions (CRITICAL)

### Tech Stack (FINAL)
- **Backend**: Python 3.11+ with FastAPI
- **Database**: SQLite (start) → PostgreSQL (production)
- **Frontend**: Streamlit (MVP) → React + Vite (later)
- **API Client**: httpx (async)
- **Scheduler**: APScheduler
- **Excel Export**: openpyxl

**WHY THIS STACK**: 
- Python because pandas for analytics, easy Excel export, Cursor handles it well
- SQLite because quick start, simple deployment, sufficient for 2-3 bots
- Streamlit because fastest path to working demo, can migrate to React later
- FastAPI because async support for UiPath API, modern, well-documented

### File Structure (DO NOT DEVIATE)
```
rpa-performance-system/
├── backend/
│   ├── main.py                 # FastAPI app
│   ├── config.py               # Environment config
│   ├── database.py             # DB setup
│   ├── models.py               # SQLAlchemy models
│   ├── clients/
│   │   └── uipath_client.py    # UiPath API wrapper
│   ├── services/
│   │   ├── job_service.py      # Job sync logic
│   │   ├── utilization_service.py  # Utilization calculation
│   │   └── export_service.py   # Excel export
│   └── scheduler/
│       └── sync_jobs.py        # Background sync
├── frontend/
│   └── streamlit_app.py        # Dashboard
├── data/
│   └── rpa_performance.db      # SQLite database
├── exports/
│   └── (generated files)
├── .env                        # Secrets (NEVER commit)
├── requirements.txt
├── CLAUDE.md                   # This file
├── SCRATCHPAD.md              # Planning & progress
└── README.md
```

## Critical Constraints (MUST FOLLOW)

### What Claude Should NEVER Do
1. **DO NOT overcomplicate**: Start simple. One file is better than three if it works.
2. **DO NOT add abstractions I didn't ask for**: No BaseService, no AbstractFactory. Build what's needed.
3. **DO NOT install random packages**: Stick to requirements.txt. Ask before adding dependencies.
4. **DO NOT create separate CSS/JS files for Streamlit**: Everything in one file.
5. **DO NOT use localStorage in artifacts**: Not supported, will break.

### What Claude Should ALWAYS Do
1. **USE type hints**: Every function signature, every variable where unclear.
2. **HANDLE errors**: Try-except around API calls, DB operations, file I/O.
3. **LOG everything important**: OAuth token refresh, sync operations, errors.
4. **VALIDATE inputs**: Check dates, IDs, filter parameters before processing.
5. **TEST before marking done**: Run the code, check output, verify it works.

## UiPath API Specifics

### Authentication Flow
```python
# OAuth 2.0 Client Credentials
# Token expires after ~1h
# Always check token_expires before using cached token
# Retry once on 401, then fail with clear message
```

### Important Endpoints
- `/odata/Jobs` - Job history (this is primary data source)
- `/odata/Machines` - Machine info
- `/odata/Robots` - Robot details
- Rate Limits: Unknown, implement exponential backoff

### Field Mappings (FROM API → TO DB)
```python
{
    "Key": "job_key",
    "Robot.Name": "robot_name",
    "HostMachineName": "machine_name",  # Host Name in Orchestrator (RPA-DONALD-001, RPA-MICKY-002)
    "ReleaseName": "process_name",
    "StartTime": "start_time",  # ISO 8601, convert to datetime
    "EndTime": "end_time",      # ISO 8601, convert to datetime
    "State": "state"            # Successful, Faulted, Stopped
}
```
- **HostMachineName** is on the Job object (not Robot). Use for Donald/Mickey distinction.

### Known Issues
- Sometimes Robot.Name is missing → Fallback to RuntimeType
- EndTime can be null for running jobs → Skip duration calculation
- Timestamps are UTC with 'Z' suffix → Strip before datetime parsing

## Data Model Rules

### Utilization Calculation (24/7 Operation)
```python
# CRITICAL: Our bots run 24/7, not 9-5
total_available_hours = 24 * days  # NOT 16 * days

# Idle time = Gaps between jobs (not "outside work hours")
# Formula: next_job.start_time - current_job.end_time

# Utilization % = (total_runtime / total_available) * 100
# Target: 85% (not 100% - need buffer for retries)
```

### Database Indexes (MUST HAVE)
```sql
CREATE INDEX idx_job_start_time ON jobs(start_time);
CREATE INDEX idx_job_robot ON jobs(robot_name);
CREATE INDEX idx_job_process ON jobs(process_name);
-- WHY: Queries filter by date/robot constantly, without indexes it's slow
```

## Development Workflow

### Before Writing Code
1. **Plan in SCRATCHPAD.md** - What are we building? Why? What's the API?
2. **Check existing code** - Is this already implemented?
3. **Verify approach** - Does this fit the architecture?

### When Implementing
1. **One feature per conversation** - Auth system ≠ Dashboard
2. **Test incrementally** - Don't write 500 lines then test
3. **Use /compact** when context gets heavy (>40%)
4. **Use /clear** when conversation derails

### Quality Gates
Before marking ANY feature "done":
- [ ] Code runs without errors
- [ ] Type hints present
- [ ] Error handling implemented
- [ ] Tested with real UiPath data
- [ ] Logged important operations

## Common Patterns

### API Call Pattern
```python
async def fetch_from_uipath():
    """Always follow this pattern for UiPath API"""
    try:
        token = await client.get_access_token()  # Auto-refresh
        async with httpx.AsyncClient(timeout=60.0) as http:
            response = await http.get(url, headers={...})
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            # Token expired, retry once
            logger.warning("Token expired, retrying...")
            # retry logic
        else:
            logger.error(f"API error: {e}")
            raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise
```

### Database Operation Pattern
```python
def db_operation():
    """Always use sessions properly"""
    db = SessionLocal()
    try:
        # do work
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"DB error: {e}")
        raise
    finally:
        db.close()
```

## Streamlit-Specific Rules

### State Management
```python
# Initialize session state at top of file
if 'key' not in st.session_state:
    st.session_state.key = default_value

# Don't fight Streamlit's rerun model
# Don't use while loops for UI updates
```

### Chart Libraries
- **Bar/Line Charts**: Use Plotly (interactive, tooltips)
- **Gantt/Timeline**: Use plotly.figure_factory.create_gantt
- **Simple Charts**: st.bar_chart / st.line_chart okay for MVP

### Performance
```python
# Cache expensive operations
@st.cache_data(ttl=300)  # 5 min cache
def load_jobs(date):
    # expensive query
    return data

# Don't query DB on every rerun
```

## Excel Export Standards

### Formatting Rules
- Header row: Bold, colored background (#366092)
- Numeric columns: Number format with 2 decimals
- Dates: DD.MM.YYYY format
- Utilization >80%: Green fill, 60-80%: Yellow, <60%: Red
- Auto-column-width for readability

### Required Sheets
1. **Summary**: Overview table + bar chart
2. **Daily Breakdown**: Time series + line chart
3. **Process Stats**: (if implemented) Process-level metrics

## Management Pitch Requirements

### Must-Have for Demo
1. **Dashboard showing real data** from last 7 days
2. **Bot utilization %** clearly visible
3. **Timeline view** (Gantt chart) showing when bots ran
4. **Excel export** that actually downloads

### Must Show These Metrics
- Current utilization % (should be ~70%)
- Idle hours per day
- Success rate %
- Business impact in € (idle hours * 50€/h)

### Demo Script Flow
1. Open dashboard → Show today's overview
2. Select date → Show historical data
3. Scroll to utilization → Point out 70% (problem)
4. Show timeline → Point out gaps (opportunity)
5. Click export → Download Excel → Open file

## Debugging Cheatsheet

### "401 Unauthorized"
→ Check .env credentials, regenerate External App if needed

### "Jobs but no utilization data"
→ Run calculate_utilization.py separately, check if it inserted to DB

### "Dashboard shows no data"
→ Check if DB file exists, check if jobs table has rows

### "Excel export fails silently"
→ Check if exports/ folder exists, check write permissions

### "Context window full"
→ /compact first, if still bad /clear and copy-paste essentials

## Project-Specific Commands

### Initial Setup
```bash
python -m venv venv
venv\Scripts\activate  # Windows
pip install fastapi uvicorn sqlalchemy httpx python-dotenv apscheduler streamlit pandas openpyxl
python init_db.py  # Create tables
```

### Daily Development
```bash
# Start Streamlit dashboard
streamlit run frontend/streamlit_app.py

# Run one-time sync
python sync_yesterday.py

# Calculate utilization
python calculate_utilization.py
```

### Testing
```bash
# Test UiPath API connection
python test_api.py

# Test utilization calculation
python test_utilization.py
```

## Context Management Rules

### When to /compact
- Context usage >40%
- Claude starts repeating itself
- Responses get slower

### When to /clear
- Conversation went off-track
- Trying to fix same bug 3+ times
- Switching to completely different feature

### External Memory Pattern
```markdown
# In SCRATCHPAD.md:
## Current Task: [Feature Name]
### Plan
- Step 1
- Step 2
### Progress
- [x] Step 1 done
- [ ] Step 2 in progress
### Blockers
- Issue X, tried Y, need Z
```

## Success Metrics

### MVP is done when:
- [ ] Dashboard shows real UiPath data
- [ ] Utilization calculated correctly (24/7 basis)
- [ ] Timeline view works
- [ ] Excel export downloads
- [ ] No errors in 5-minute demo

### Production-ready when:
- [ ] Background scheduler runs daily
- [ ] Error handling for all edge cases
- [ ] Logging implemented
- [ ] Docker container works
- [ ] Documentation complete

## Remember
- **Think before typing** - Plan in SCRATCHPAD.md first
- **One conversation per feature** - Don't mix tasks
- **Show, don't tell** - Give examples, not descriptions
- **Test continuously** - Don't write 500 lines untested
- **Clear when stuck** - Don't loop, change approach

## Current Phase
**MVP Development** - Focus: Working demo for management pitch

Last Updated: 2026-02-13
