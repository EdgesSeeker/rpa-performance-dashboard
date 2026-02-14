# 🎯 CURSOR IMPLEMENTATION PROMPT - Feature Enhancement
## Copy-Paste diesen kompletten Text in Cursor Plan Mode (Shift+Tab 2x)

---

## Context & Current State

Read CLAUDE.md, SCRATCHPAD_UPDATED.md, and PROJEKTSTAND.md for full context.

**WICHTIG: MVP IST KOMPLETT FERTIG!**

We're NOT building from scratch. We're ENHANCING an existing, working dashboard.

### What Already Works ✅
- UiPath API connection (OAuth, $expand=Robot)
- Database (SQLite): Jobs + DailyUtilization tables populated
- Sync & Utilization calculation scripts
- Streamlit Dashboard with:
  - Filter system (1/7/30 Tage, eigener Bereich)
  - KPIs (Ø Utilization, Idle, Success Rate, Business Impact)
  - Bot Utilization Chart (Balken für Donald & Mickey)
  - Timeline (Gantt Chart)
  - Leerlauf pro Tag (gemeinsamer Leerlauf beider Roboter)
  - Prozess-Statistik
- Excel Export (Summary + Daily Breakdown sheets)

### What We're Adding 🚀
3 new features that integrate into the existing dashboard:
1. **Quick Wins Dashboard** - Automated optimization recommendations
2. **Weekly Trends Analysis** - 4-week comparison showing improvement
3. **Executive Summary Export** - Management-ready Excel sheet

**Timeline**: 3-5 hours
**Approach**: Extend existing code, don't rewrite it

---

## Known Project Details

### Robots
- **Donald**: Identified by `host_machine_name` = "RPA-DONALD-001"
- **Mickey**: Identified by `host_machine_name` = "RPA-MICKY-002"
- Display names: "Donald" and "Mickey" (already mapped in frontend)

### Environment
```
Tenant: defaultenet
Org: lackmann
Orchestrator: https://cloud.uipath.com/lackmann/defaultenet/orchestrator_/
```

### Data Model (Existing)
```sql
-- Jobs table (populated)
CREATE TABLE jobs (
    job_key TEXT UNIQUE,
    robot_name TEXT,  -- "Donald" or "Mickey"
    host_machine_name TEXT,
    process_name TEXT,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    duration_seconds INTEGER,
    state TEXT  -- Successful, Faulted
);

-- DailyUtilization table (populated)
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

### Existing File Structure
```
rpa-performance-system/
├── backend/
│   ├── clients/
│   │   └── uipath_client.py  (EXISTS)
│   ├── services/
│   │   └── export_service.py  (EXISTS - extend this)
│   ├── sync_jobs.py  (EXISTS)
│   ├── calculate_utilization.py  (EXISTS)
│   └── database.py  (EXISTS)
├── frontend/
│   └── streamlit_app.py  (EXISTS - extend this)
└── data/
    └── rpa_performance.db  (EXISTS, populated)
```

---

## FEATURE 1: Quick Wins Dashboard 🏆

### Business Value
Shows actionable optimization opportunities automatically detected from data.
**Pitch Impact**: "Tool doesn't just show data - it finds €X/month in optimizations"

### Requirements

#### 1.1 Recurring Idle Pattern Detection
**What**: Find time slots that are consistently idle across multiple days

**Logic**:
```python
# For each robot (Donald, Mickey):
# 1. Get all jobs from last 7 days
# 2. Group by hour of day (0-23)
# 3. For each hour, check: How many days was it idle? (no job running)
# 4. If idle >=4 out of 7 days AND average idle duration >30min:
#    → Flag as recurring idle pattern

# Idle = no job running at that hour on that day
# Consider both robots (gemeinsamer Leerlauf from existing feature)

Output:
{
  "robot": "Donald",
  "time_slot": "14:00-15:00",
  "frequency": "5 von 7 Tagen",
  "avg_idle_minutes": 92,
  "potential_hours_week": 7.7
}
```

#### 1.2 Underutilized Time Windows
**What**: Broad time ranges (morning/afternoon/night) with low utilization

**Logic**:
```python
# Define windows:
windows = {
  "Nacht (00-06h)": (0, 6),
  "Morgen (06-12h)": (6, 12),
  "Nachmittag (12-18h)": (12, 18),
  "Abend (18-24h)": (18, 24)
}

# For each window, last 7 days:
# Calculate: avg_utilization = (jobs_runtime in window) / (window_hours * 7 days)
# If <40%: Flag as underutilized

Output:
{
  "window": "Nacht (00-06h)",
  "current_utilization": 15%,
  "target": 40%,
  "potential_hours_week": (40% - 15%) * 6h * 7 days = 10.5h
}
```

#### 1.3 € Impact Calculation
```python
# Per Quick Win:
impact_month = potential_hours_week * 4.33 * 50  # 50€/hour rate

# Sort Quick Wins by impact (descending)
# Show top 3-5
```

### Implementation

**New File**: `backend/services/quickwins_service.py`
```python
from datetime import datetime, timedelta, time
from typing import List, Dict
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models import Job, DailyUtilization

def analyze_quickwins(db: Session, days: int = 7) -> Dict:
    """
    Analyze last N days for optimization opportunities
    
    Returns:
    {
        "recurring_idle": [
            {
                "robot": str,
                "time_slot": str,  # "14:00-15:00"
                "frequency": str,  # "5 von 7 Tagen"
                "avg_idle_minutes": float,
                "potential_hours_week": float,
                "impact_euro_month": float,
                "priority": str  # "HIGH", "MEDIUM", "LOW"
            }
        ],
        "underutilized_windows": [
            {
                "window": str,  # "Nacht (00-06h)"
                "current_utilization": float,
                "target": float,
                "potential_hours_week": float,
                "impact_euro_month": float,
                "priority": str
            }
        ],
        "total_potential_hours_week": float,
        "total_impact_euro_month": float
    }
    """
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Get all jobs in timeframe
    jobs = db.query(Job).filter(
        Job.start_time >= datetime.combine(start_date, datetime.min.time()),
        Job.start_time < datetime.combine(end_date, datetime.min.time())
    ).all()
    
    # Analyze
    recurring = find_recurring_idle(jobs, days)
    underutilized = find_underutilized_windows(jobs, days)
    
    # Calculate totals
    total_hours = sum(r["potential_hours_week"] for r in recurring)
    total_hours += sum(u["potential_hours_week"] for u in underutilized)
    total_impact = total_hours * 4.33 * 50
    
    return {
        "recurring_idle": sorted(recurring, key=lambda x: x["impact_euro_month"], reverse=True),
        "underutilized_windows": sorted(underutilized, key=lambda x: x["impact_euro_month"], reverse=True),
        "total_potential_hours_week": round(total_hours, 1),
        "total_impact_euro_month": round(total_impact, 0)
    }

def find_recurring_idle(jobs: List[Job], days: int) -> List[Dict]:
    """
    Find time slots that are consistently idle
    """
    # TODO: Implement pattern detection
    # Group jobs by robot, date, hour
    # Identify hours with no jobs running
    # Find patterns (same hour idle 4+ days)
    # Calculate average idle duration
    # Return list of recurring patterns
    
    pass  # Implement in Phase 1

def find_underutilized_windows(jobs: List[Job], days: int) -> List[Dict]:
    """
    Find broad time windows with low utilization
    """
    # TODO: Implement window analysis
    # Define 4 time windows
    # Calculate utilization per window
    # Flag windows <40%
    # Calculate potential
    
    pass  # Implement in Phase 1
```

### UI Integration

**In**: `frontend/streamlit_app.py`

**Location**: Add section AFTER filter selection, BEFORE KPIs

```python
def render_quickwins_section(quickwins_data: Dict):
    """Display Quick Wins prominently"""
    
    if not quickwins_data or quickwins_data["total_impact_euro_month"] == 0:
        st.info("✅ Keine Optimierungen gefunden - Bots sind gut ausgelastet!")
        return
    
    st.header("🎯 Quick Wins - Sofort umsetzbare Optimierungen")
    st.caption(f"Automatisch erkannt aus den letzten 7 Tagen")
    
    # Summary Box
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "Gesamt-Potential",
            f"{quickwins_data['total_potential_hours_week']}h/Woche"
        )
    with col2:
        st.metric(
            "Business Impact",
            f"€{quickwins_data['total_impact_euro_month']:.0f}/Monat",
            delta="zusätzliche Kapazität",
            delta_color="normal"
        )
    
    st.divider()
    
    # Quick Wins
    win_number = 1
    
    # Recurring Idle Patterns
    for pattern in quickwins_data["recurring_idle"][:3]:  # Top 3
        priority_color = "normal" if pattern["priority"] == "HIGH" else "off"
        
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.subheader(f"🏆 #{win_number}: Recurring Idle - {pattern['robot']}")
                st.write(f"⏰ **{pattern['time_slot']}** - {pattern['frequency']} idle")
                st.write(f"Ø {pattern['avg_idle_minutes']:.0f} Minuten")
                st.write(f"💡 *Empfehlung: Prozess mit passender Dauer hier schedulen*")
            
            with col2:
                st.metric("Potential", f"{pattern['potential_hours_week']:.1f}h/Woche")
            
            with col3:
                st.metric(
                    "Impact",
                    f"€{pattern['impact_euro_month']:.0f}/Monat",
                    delta=f"Prio: {pattern['priority']}",
                    delta_color=priority_color
                )
        
        st.divider()
        win_number += 1
    
    # Underutilized Windows
    for window in quickwins_data["underutilized_windows"][:2]:  # Top 2
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.subheader(f"📊 #{win_number}: Unterlastetes Zeitfenster")
                st.write(f"🕐 **{window['window']}**")
                st.write(f"Aktuelle Auslastung: {window['current_utilization']:.1f}%")
                st.write(f"💡 *Empfehlung: Batch-Jobs in dieses Fenster verlegen*")
            
            with col2:
                st.metric("Potential", f"{window['potential_hours_week']:.1f}h/Woche")
            
            with col3:
                st.metric("Impact", f"€{window['impact_euro_month']:.0f}/Monat")
        
        st.divider()
        win_number += 1

# In main() function, add after filter selection:
def main():
    # ... existing filter code ...
    
    # NEW: Quick Wins Section
    try:
        from backend.services.quickwins_service import analyze_quickwins
        db = SessionLocal()
        quickwins = analyze_quickwins(db, days=7)
        db.close()
        
        render_quickwins_section(quickwins)
    except Exception as e:
        st.warning(f"Quick Wins Analyse nicht verfügbar: {e}")
    
    # ... rest of existing code (KPIs, charts, etc.) ...
```

---

## FEATURE 2: Weekly Trends Analysis 📈

### Business Value
Shows improvement over time. "We're getting better!" justifies continued investment.

### Requirements

#### 2.1 Weekly Aggregation
```python
# Group DailyUtilization by ISO week (Monday start)
# For each of last 4 weeks:
{
  "week_number": "KW 06",
  "year": 2026,
  "date_range": "10.02 - 16.02",
  "avg_utilization": 72.3,
  "total_idle_hours": 47.2,
  "total_runs": 156,
  "avg_success_rate": 94.8
}
```

#### 2.2 Trend Calculation
```python
# Week-over-week change
trend_percent = ((current_week - previous_week) / previous_week) * 100

# Overall improvement (week 4 vs week 1)
improvement = ((week_4 - week_1) / week_1) * 100
timespan = "4 Wochen"
```

### Implementation

**New File**: `backend/services/trends_service.py`
```python
from datetime import datetime, timedelta
from typing import List, Dict
from sqlalchemy.orm import Session
from backend.models import DailyUtilization
import pandas as pd

def calculate_weekly_trends(db: Session, weeks: int = 4) -> Dict:
    """
    Calculate weekly aggregations and trends
    
    Returns:
    {
        "weeks": [
            {
                "week_number": "KW 06",
                "year": 2026,
                "date_range": "10.02 - 16.02",
                "avg_utilization": 72.3,
                "total_idle_hours": 47.2,
                "total_runs": 156,
                "avg_success_rate": 94.8
            }
        ],
        "overall_trend": {
            "utilization_change": 7.2,  # % points
            "idle_reduction_hours_week": 9.3,
            "improvement_value_euro_month": 2015
        }
    }
    """
    
    # Get data for last X weeks
    end_date = datetime.now().date()
    start_date = end_date - timedelta(weeks=weeks * 7)
    
    util_data = db.query(DailyUtilization).filter(
        DailyUtilization.date >= start_date,
        DailyUtilization.date <= end_date
    ).all()
    
    # Convert to DataFrame for easier grouping
    df = pd.DataFrame([{
        "date": u.date,
        "robot": u.robot_name,
        "utilization": u.utilization_percent,
        "idle_hours": u.idle_hours,
        "runs": u.run_count,
        "success_rate": (u.success_count / u.run_count * 100) if u.run_count > 0 else 0
    } for u in util_data])
    
    # Add ISO week
    df["week"] = pd.to_datetime(df["date"]).dt.isocalendar().week
    df["year"] = pd.to_datetime(df["date"]).dt.isocalendar().year
    
    # Group by week
    weekly = df.groupby(["year", "week"]).agg({
        "date": ["min", "max"],
        "utilization": "mean",
        "idle_hours": "sum",
        "runs": "sum",
        "success_rate": "mean"
    }).reset_index()
    
    # Format results
    weeks_list = []
    for _, row in weekly.iterrows():
        weeks_list.append({
            "week_number": f"KW {row['week']}",
            "year": int(row['year']),
            "date_range": f"{row['date']['min'].strftime('%d.%m')} - {row['date']['max'].strftime('%d.%m')}",
            "avg_utilization": round(row['utilization']['mean'], 1),
            "total_idle_hours": round(row['idle_hours']['sum'], 1),
            "total_runs": int(row['runs']['sum']),
            "avg_success_rate": round(row['success_rate']['mean'], 1)
        })
    
    # Calculate overall trend
    if len(weeks_list) >= 2:
        first = weeks_list[0]
        last = weeks_list[-1]
        
        util_change = last["avg_utilization"] - first["avg_utilization"]
        idle_reduction = (first["total_idle_hours"] / 7) - (last["total_idle_hours"] / 7)  # per week
        improvement_value = idle_reduction * 4.33 * 50  # per month
    else:
        util_change = 0
        idle_reduction = 0
        improvement_value = 0
    
    return {
        "weeks": weeks_list,
        "overall_trend": {
            "utilization_change": round(util_change, 1),
            "idle_reduction_hours_week": round(idle_reduction, 1),
            "improvement_value_euro_month": round(improvement_value, 0)
        }
    }
```

### UI Integration

**In**: `frontend/streamlit_app.py`

**Location**: Add section AFTER KPIs, BEFORE Timeline

```python
def render_weekly_trends_section(trends_data: Dict):
    """Display weekly comparison"""
    
    if not trends_data or len(trends_data["weeks"]) < 2:
        st.info("📊 Nicht genug Daten für Wochen-Vergleich (mindestens 2 Wochen benötigt)")
        return
    
    st.header("📈 Wochen-Vergleich")
    st.caption(f"Entwicklung der letzten {len(trends_data['weeks'])} Wochen")
    
    # Summary Metrics
    trend = trends_data["overall_trend"]
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Trend Auslastung",
            f"{trend['utilization_change']:+.1f}%",
            delta=f"über {len(trends_data['weeks'])} Wochen",
            delta_color="normal"
        )
    
    with col2:
        st.metric(
            "Idle-Reduktion",
            f"{trend['idle_reduction_hours_week']:.1f}h/Woche",
            delta="vs. Anfang",
            delta_color="inverse"  # Less idle = good
        )
    
    with col3:
        st.metric(
            "Verbesserung",
            f"€{trend['improvement_value_euro_month']:.0f}/Monat",
            delta="zusätzliche Kapazität",
            delta_color="normal"
        )
    
    st.divider()
    
    # Weekly Table
    import pandas as pd
    df = pd.DataFrame(trends_data["weeks"])
    
    # Calculate week-over-week trends
    trends_col = [""]
    for i in range(1, len(df)):
        prev = df.iloc[i-1]["avg_utilization"]
        curr = df.iloc[i]["avg_utilization"]
        change = ((curr - prev) / prev) * 100
        if change > 0:
            trends_col.append(f"↗️ +{change:.1f}%")
        elif change < 0:
            trends_col.append(f"↘️ {change:.1f}%")
        else:
            trends_col.append("→ 0%")
    
    df["Trend"] = trends_col
    df["Impact €"] = (df["total_idle_hours"] / 7 * 4.33 * 50).round(0).astype(int)
    
    # Rename for display
    display_df = df[[
        "week_number", "date_range", "avg_utilization",
        "total_idle_hours", "Trend", "Impact €"
    ]].rename(columns={
        "week_number": "Woche",
        "date_range": "Zeitraum",
        "avg_utilization": "Ø Auslastung %",
        "total_idle_hours": "Idle (h)"
    })
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Trend Chart
    import plotly.graph_objects as go
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df["week_number"],
        y=df["avg_utilization"],
        mode='lines+markers',
        name='Auslastung %',
        line=dict(color='#0066CC', width=3),
        marker=dict(size=10)
    ))
    
    # Target line at 85%
    fig.add_hline(
        y=85,
        line_dash="dash",
        line_color="green",
        annotation_text="Ziel: 85%",
        annotation_position="right"
    )
    
    fig.update_layout(
        title="Auslastungs-Trend über Wochen",
        xaxis_title="Woche",
        yaxis_title="Auslastung %",
        yaxis_range=[0, 100],
        height=400,
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)

# In main() function, add after Quick Wins:
def main():
    # ... existing code ...
    # ... Quick Wins section ...
    
    # NEW: Weekly Trends Section
    try:
        from backend.services.trends_service import calculate_weekly_trends
        db = SessionLocal()
        trends = calculate_weekly_trends(db, weeks=4)
        db.close()
        
        render_weekly_trends_section(trends)
    except Exception as e:
        st.warning(f"Wochen-Vergleich nicht verfügbar: {e}")
    
    # ... rest of existing code ...
```

---

## FEATURE 3: Executive Summary Export 📄

### Business Value
1-page management report in Excel. Perfect for forwarding to decision-makers.

### Requirements

Add new sheet as FIRST sheet in existing Excel export.

**Sheet Structure**:
```
Row 1: [TITLE] RPA Performance - Executive Summary
Row 2: [DATE] Analysezeitraum: DD.MM - DD.MM
Row 3: [TIMESTAMP] Erstellt: DD.MM.YYYY HH:MM

Row 5: KEY METRICS
Row 6-9: Table with Current vs Target

Row 11: TREND (Letzte 4 Wochen)
Row 12-14: Text summary of improvement

Row 16: TOP 3 QUICK WINS
Row 17-23: Numbered list with impact

Row 25: EMPFEHLUNG
Row 26-28: Action items
```

### Implementation

**Extend**: `backend/services/export_service.py`

```python
from openpyxl.chart import LineChart, Reference

def create_executive_summary_sheet(
    wb: Workbook,
    quickwins_data: Dict,
    trends_data: Dict,
    date_start,
    date_end
) -> None:
    """
    Create Executive Summary as first sheet
    
    This is added to existing export_daily_summary() function
    """
    
    # Create sheet at position 0
    ws = wb.create_sheet("Executive Summary", 0)
    
    # Styles
    title_font = Font(size=18, bold=True, color="1F4E78")
    header_font = Font(size=14, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    
    # Title
    ws['A1'] = "RPA Performance - Executive Summary"
    ws['A1'].font = title_font
    ws.merge_cells('A1:D1')
    
    # Date & Timestamp
    ws['A2'] = f"Analysezeitraum: {date_start.strftime('%d.%m')} - {date_end.strftime('%d.%m.%Y')}"
    ws['A3'] = f"Erstellt: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    
    # Key Metrics Section
    ws['A5'] = "KEY METRICS"
    ws['A5'].font = header_font
    ws['A5'].fill = header_fill
    ws.merge_cells('A5:D5')
    
    # Metrics table headers
    ws['A6'] = "Metrik"
    ws['B6'] = "Aktuell"
    ws['C6'] = "Ziel"
    ws['D6'] = "Gap"
    for cell in ['A6', 'B6', 'C6', 'D6']:
        ws[cell].font = Font(bold=True)
    
    # TODO: Get actual metrics from data
    # ws['A7'] = "Durchschn. Auslastung"
    # ws['B7'] = "70.5%"
    # etc.
    
    # Trend Section
    ws['A11'] = "TREND (Letzte 4 Wochen)"
    ws['A11'].font = header_font
    ws['A11'].fill = header_fill
    ws.merge_cells('A11:D11')
    
    if trends_data:
        trend = trends_data['overall_trend']
        ws['A12'] = f"Auslastung: {trend['utilization_change']:+.1f}% Verbesserung"
        ws['A13'] = f"Idle-Reduktion: {trend['idle_reduction_hours_week']:.1f}h/Woche"
        ws['A14'] = f"→ Wert: €{trend['improvement_value_euro_month']:.0f}/Monat zusätzliche Kapazität"
    
    # Quick Wins Section
    ws['A16'] = "TOP 3 QUICK WINS"
    ws['A16'].font = header_font
    ws['A16'].fill = header_fill
    ws.merge_cells('A16:D16')
    
    if quickwins_data:
        row = 17
        win_num = 1
        
        # Recurring idle
        for pattern in quickwins_data['recurring_idle'][:2]:
            ws[f'A{row}'] = f"{win_num}. Recurring Idle: {pattern['robot']} @ {pattern['time_slot']}"
            ws[f'A{row}'].font = Font(bold=True)
            ws[f'A{row+1}'] = f"   • {pattern['frequency']} idle, Ø {pattern['avg_idle_minutes']:.0f}min"
            ws[f'A{row+2}'] = f"   • Potential: €{pattern['impact_euro_month']:.0f}/Monat"
            row += 3
            win_num += 1
        
        # Underutilized window
        if quickwins_data['underutilized_windows']:
            window = quickwins_data['underutilized_windows'][0]
            ws[f'A{row}'] = f"{win_num}. Unterlastetes Zeitfenster: {window['window']}"
            ws[f'A{row}'].font = Font(bold=True)
            ws[f'A{row+1}'] = f"   • Aktuell {window['current_utilization']:.1f}% Auslastung"
            ws[f'A{row+2}'] = f"   • Potential: €{window['impact_euro_month']:.0f}/Monat"
            row += 3
    
    # Recommendations
    ws[f'A{row+1}'] = "EMPFEHLUNG"
    ws[f'A{row+1}'].font = header_font
    ws[f'A{row+1}'].fill = header_fill
    ws.merge_cells(f'A{row+1}:D{row+1}')
    
    ws[f'A{row+2}'] = "Nächste Schritte:"
    ws[f'A{row+2}'].font = Font(bold=True)
    ws[f'A{row+3}'] = "1. Quick Win #1 umsetzen (Aufwand: Gering, Impact: Hoch)"
    ws[f'A{row+4}'] = "2. Weitere Prozesse für unterlastete Zeitfenster identifizieren"
    ws[f'A{row+5}'] = "3. Nach 2 Wochen: Erfolg messen (Ziel: +5% Auslastung)"
    
    # Column widths
    ws.column_dimensions['A'].width = 50
    ws.column_dimensions['B'].width = 15
    ws.column_dimensions['C'].width = 15
    ws.column_dimensions['D'].width = 15


# Update existing export_daily_summary() function:
def export_daily_summary(db: Session, date_start, date_end, output_path: str):
    """Enhanced to include Executive Summary"""
    
    wb = Workbook()
    
    # NEW: Get data for Executive Summary
    try:
        from backend.services.quickwins_service import analyze_quickwins
        from backend.services.trends_service import calculate_weekly_trends
        
        quickwins = analyze_quickwins(db, days=7)
        trends = calculate_weekly_trends(db, weeks=4)
        
        # Create Executive Summary as first sheet
        create_executive_summary_sheet(wb, quickwins, trends, date_start, date_end)
    except Exception as e:
        # If Quick Wins/Trends not available, skip Executive Summary
        print(f"Warning: Executive Summary not created: {e}")
    
    # ... rest of existing export code (Summary, Daily Breakdown) ...
    
    wb.save(output_path)
    return output_path
```

---

## Implementation Plan

### Phase 1: Quick Wins Backend (60 min)
1. Create `backend/services/quickwins_service.py`
2. Implement `find_recurring_idle()`
3. Implement `find_underutilized_windows()`
4. Test with real data
5. Verify calculations make sense

### Phase 2: Weekly Trends Backend (30 min)
1. Create `backend/services/trends_service.py`
2. Implement weekly grouping (pandas + ISO week)
3. Calculate trends
4. Test with real data

### Phase 3: Frontend Integration (45 min)
1. Add `render_quickwins_section()` to streamlit_app.py
2. Add `render_weekly_trends_section()` to streamlit_app.py
3. Integrate into main() after filters
4. Test UI, verify styling

### Phase 4: Excel Enhancement (30 min)
1. Extend export_service.py
2. Implement `create_executive_summary_sheet()`
3. Integrate into existing export function
4. Test Excel output, verify formatting

### Phase 5: Testing & Polish (30 min)
1. Full integration test
2. Verify calculations with manual spot-checks
3. UI polish (spacing, colors, emojis)
4. Take screenshots for pitch
5. Test Excel export end-to-end

**Total: ~3 hours**

---

## Testing Strategy

### Before Starting
- [ ] Verify dashboard runs: `streamlit run frontend/streamlit_app.py`
- [ ] Check data availability: At least 7 days in database
- [ ] Confirm filter system works

### After Each Phase
- [ ] Phase 1: Print Quick Wins to console, verify logic
- [ ] Phase 2: Print Weekly Trends to console, spot-check
- [ ] Phase 3: Reload dashboard, verify new sections appear
- [ ] Phase 4: Export Excel, open and review formatting
- [ ] Phase 5: Full demo run-through

### Edge Cases to Test
- [ ] Only 3 days of data (not enough for patterns)
- [ ] 100% utilization (no idle patterns found)
- [ ] Only 1 week of data (trends can't calculate)
- [ ] Excel export when Quick Wins/Trends fail

---

## Success Criteria

### Feature 1: Quick Wins ✅
- [ ] Detects recurring idle patterns (>=3 days)
- [ ] Detects underutilized time windows (<40%)
- [ ] Calculates € impact correctly
- [ ] Shows top 3-5 sorted by impact
- [ ] UI is prominent (top of dashboard)

### Feature 2: Weekly Trends ✅
- [ ] Groups by ISO week correctly
- [ ] Shows last 4 weeks (or available weeks)
- [ ] Calculates trends (% change)
- [ ] Displays chart with target line
- [ ] Shows overall improvement metrics

### Feature 3: Executive Summary ✅
- [ ] Creates sheet as first in Excel
- [ ] Professional formatting
- [ ] Includes all sections (Metrics, Trends, Wins, Recommendations)
- [ ] Readable in one page
- [ ] Can be printed/forwarded

---

## Known Constraints

### Must Follow (from CLAUDE.md)
1. Type hints on all functions
2. Error handling (try/except)
3. Logging for important calculations
4. Test incrementally (don't write all at once)
5. Keep algorithms simple and readable

### Integration Points
- Don't modify existing filter system
- Don't modify existing KPIs calculation
- Extend, don't replace, Excel export
- Keep existing dashboard layout functional

### Data Assumptions
- At least 7 days of data for meaningful analysis
- Jobs have valid start_time, end_time
- Robot names are "Donald" and "Mickey"
- DailyUtilization table is populated

---

## Questions Resolved

1. ✅ **Robot names**: Donald & Mickey (from HostMachineName)
2. ✅ **€ rate**: 50€/hour (from PROJEKTSTAND.md)
3. ✅ **Target utilization**: 85%
4. ✅ **Leerlauf calculation**: Already exists (gemeinsamer Leerlauf)
5. ✅ **Filter system**: Already exists (reuse it)

---

## Output for Review

After review, confirm:
1. ✅ Integration approach makes sense (extend, not replace)
2. ✅ Can use existing Leerlauf calculation
3. ✅ Time estimate realistic (3 hours with existing MVP)
4. ✅ No database schema changes needed
5. ⚠️ Any concerns about pattern detection algorithm?
6. 💡 Suggestions for simplification?

---

If plan looks good, implement phase by phase with testing after each phase.
