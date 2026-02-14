"""
RPA Performance Dashboard - Streamlit. Run: streamlit run frontend/streamlit_app.py
"""
import json
import os
import sys
from pathlib import Path
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Project root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from backend.database import SessionLocal, Job, DailyUtilization, init_tables
import backend.sync_jobs as sync_jobs_module
import backend.calculate_utilization as calc_util_module

init_tables()

# Optional: map robot_key / Host name to display names (Donald, Mickey)
ROBOT_NAME_MAP: dict[str, str] = {
    "RPA-DONALD-001": "Donald",
    "RPA-MICKY-002": "Mickey",
    "RPA-MICKEY-002": "Mickey",
}
_raw = os.getenv("ROBOT_NAME_MAP")
if _raw:
    try:
        ROBOT_NAME_MAP = {**ROBOT_NAME_MAP, **json.loads(_raw)}
    except json.JSONDecodeError:
        pass


def _display_robot_name(name: str) -> str:
    return ROBOT_NAME_MAP.get(name, name)


def _format_duration(seconds: float) -> str:
    """Format seconds as 'X min' or 'Xh YY min'."""
    if pd.isna(seconds) or seconds < 0:
        return "—"
    sec = int(round(seconds))
    if sec < 60:
        return f"{sec} s"
    mins = sec // 60
    if mins < 60:
        return f"{mins} min"
    h = mins // 60
    m = mins % 60
    return f"{h}h {m:02d} min" if m else f"{h}h"


def _compute_process_stats(df_jobs: pd.DataFrame) -> pd.DataFrame | None:
    """Aggregate per process_name: runs, success_rate, duration mean/min/max (seconds). Returns None if no jobs."""
    if df_jobs.empty or "end_time" not in df_jobs.columns:
        return None
    df = df_jobs.copy()
    df["duration_sec"] = (df["end_time"] - df["start_time"]).dt.total_seconds()
    df = df[df["duration_sec"].notna() & (df["duration_sec"] >= 0)]
    if df.empty:
        return None
    proc = df.groupby("process_name").agg(
        runs=("job_key", "count"),
        success=("state", lambda s: (s == "Successful").sum()),
        duration_mean=("duration_sec", "mean"),
        duration_min=("duration_sec", "min"),
        duration_max=("duration_sec", "max"),
    ).reset_index()
    proc["success_rate"] = (proc["success"] / proc["runs"] * 100).round(1)
    return proc


st.set_page_config(page_title="RPA Performance", layout="wide")
st.title("RPA Performance Monitoring")

# Sidebar: date range with quick presets and custom range
today = date.today()
yesterday = today - timedelta(days=1)
st.sidebar.subheader("Zeitraum")
preset = st.sidebar.radio(
    "Schnellauswahl",
    ["1 Tag (gestern)", "7 Tage", "30 Tage", "90 Tage", "Eigener Bereich"],
    horizontal=False,
    label_visibility="collapsed",
)
if preset == "1 Tag (gestern)":
    date_start = yesterday
    date_end = yesterday
elif preset == "7 Tage":
    date_start = today - timedelta(days=6)
    date_end = today
elif preset == "30 Tage":
    date_start = today - timedelta(days=29)
    date_end = today
elif preset == "90 Tage":
    date_start = today - timedelta(days=89)
    date_end = today
else:
    date_start = st.sidebar.date_input("Von", value=yesterday, max_value=today)
    date_end = st.sidebar.date_input("Bis", value=today, max_value=today, min_value=date_start)
    if date_end < date_start:
        date_end = date_start
st.sidebar.caption(f"Anzeige: {date_start} bis {date_end}")

# Daten von UiPath laden (für gehostete App / Streamlit Cloud)
st.sidebar.divider()
if "load_success" in st.session_state:
    st.sidebar.success(st.session_state.load_success)
    del st.session_state["load_success"]
if st.sidebar.button("Daten von UiPath laden"):
    sync_days = 90
    with st.spinner(f"Lade Daten von UiPath … ({sync_days} Tage, kann 1–2 Min. dauern)"):
        try:
            n_jobs = sync_jobs_module.run_sync(days=sync_days)
            n_util = calc_util_module.calculate_and_store()
            st.cache_data.clear()
            st.session_state["load_success"] = f"Fertig: {n_jobs} Jobs synchronisiert, {n_util} Utilization-Tage berechnet."
        except Exception as e:
            st.sidebar.error(f"Fehler beim Laden: {e}")
            st.stop()
    st.rerun()


@st.cache_data(ttl=300)
def load_jobs(d_start: date, d_end: date) -> pd.DataFrame:
    """Lädt alle Jobs, die mit [d_start, d_end] überlappen (inkl. Übernacht-Jobs)."""
    db = SessionLocal()
    try:
        t_start = datetime.combine(d_start, datetime.min.time())
        t_end = datetime.combine(d_end, datetime.max.time())
        rows = (
            db.query(Job)
            .filter(
                Job.end_time.isnot(None),
                Job.start_time < t_end,
                Job.end_time >= t_start,
            )
            .all()
        )
        out = []
        for j in rows:
            rn = j.robot_name or "Unknown"
            mn = (j.machine_name or "").strip()
            robot_key = mn if mn else rn
            out.append({
                "job_key": j.job_key,
                "robot_name": rn,
                "machine_name": mn,
                "robot_key": robot_key,
                "process_name": j.process_name or "",
                "start_time": j.start_time,
                "end_time": j.end_time,
                "state": j.state or "",
            })
        return pd.DataFrame(out)
    finally:
        db.close()


@st.cache_data(ttl=300)
def load_utilization(d_start: date, d_end: date) -> pd.DataFrame:
    db = SessionLocal()
    try:
        rows = (
            db.query(DailyUtilization)
            .filter(DailyUtilization.date >= d_start, DailyUtilization.date <= d_end)
            .all()
        )
        return pd.DataFrame([
            {
                "date": u.date,
                "robot_name": u.robot_name,
                "total_runtime_hours": u.total_runtime_hours,
                "idle_hours": u.idle_hours,
                "utilization_percent": u.utilization_percent,
            }
            for u in rows
        ])
    finally:
        db.close()


df_jobs = load_jobs(date_start, date_end)
df_util = load_utilization(date_start, date_end)
df_util_complete = df_util[df_util["date"] < today] if not df_util.empty else pd.DataFrame()
df_util_kpi = df_util_complete[df_util_complete["robot_name"].astype(str).str.contains("RPA-", na=False)] if not df_util_complete.empty else pd.DataFrame()
if df_util_kpi.empty:
    df_util_kpi = df_util_complete
idle_hours_sum = df_util_kpi["idle_hours"].sum() if not df_util_kpi.empty else 0.0

# --- Overview KPIs ---
st.header("Übersicht")
if df_jobs.empty and df_util.empty:
    st.info("Keine Daten. Bitte zuerst Jobs synchronisieren: `python -m backend.sync_jobs` und dann `python -m backend.calculate_utilization`.")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
with c1:
    avg_util_raw = df_util_kpi["utilization_percent"].mean() if not df_util_kpi.empty else (df_util["utilization_percent"].mean() if not df_util.empty else 0)
    avg_util = min(100.0, avg_util_raw)
    st.metric("Ø Utilization %", f"{avg_util:.1f}%")
    st.caption("Durchschnitt pro Robot (Donald/Mickey), nur abgeschlossene Tage.")
with c2:
    st.metric("Leerlauf (ungenutzte Robot-Stunden)", f"{idle_hours_sum:.1f}h")
    st.caption("Donald + Mickey addiert: Zeit, in der ein Robot keinen Job hatte (Potenzial für mehr Prozesse).")
with c3:
    total = len(df_jobs)
    success = (df_jobs["state"] == "Successful").sum() if not df_jobs.empty else 0
    rate = (success / total * 100) if total else 0
    st.metric("Success Rate", f"{rate:.1f}%")
    st.caption("Anteil der erfolgreich abgeschlossenen Jobs")
with c4:
    impact = idle_hours_sum * 50
    st.metric("Business Impact (Idle)", f"€{impact:.0f}")
    st.caption("Geschätzter Verlust durch Idle-Zeit (50 €/h)")

# --- Weekly Trends ---
def render_weekly_trends_section(trends_data: dict) -> None:
    if not trends_data or len(trends_data.get("weeks", [])) < 2:
        st.info("Nicht genug Daten für Wochen-Vergleich (mindestens 2 Wochen benötigt).")
        return
    weeks = trends_data["weeks"]
    trend = trends_data.get("overall_trend", {})
    st.header("Wochen-Vergleich")
    st.caption(f"Entwicklung der letzten {len(weeks)} Wochen (Basis: letzte 90 Tage, gruppiert nach Kalenderwoche). "
               "Ø Auslastung = Mittel der täglichen Auslastung pro Robot (Donald & Mickey). "
               "Niedrige Werte in älteren Wochen entsprechen den tatsächlichen Daten – z. B. weniger Läufe im Nov/Dez.")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Trend Auslastung", f"{trend.get('utilization_change', 0):+.1f}%", delta=f"über {len(weeks)} Wochen", delta_color="normal")
    with col2:
        st.metric("Idle-Reduktion", f"{trend.get('idle_reduction_hours_week', 0):.1f}h/Woche", delta="vs. Anfang", delta_color="inverse")
    with col3:
        st.metric("Verbesserung", f"€{trend.get('improvement_value_euro_month', 0):.0f}/Monat", delta="zusätzliche Kapazität", delta_color="normal")
    st.divider()
    df_t = pd.DataFrame(weeks)
    trends_col = [""]
    for i in range(1, len(df_t)):
        prev = df_t.iloc[i - 1]["avg_utilization"]
        curr = df_t.iloc[i]["avg_utilization"]
        change = ((curr - prev) / prev * 100) if prev else 0
        trends_col.append(f"+{change:.1f}%" if change >= 0 else f"{change:.1f}%")
    df_t["Trend"] = trends_col
    df_t["Impact €"] = (df_t["total_idle_hours"] / 7 * 4.33 * 50).round(0).astype(int)
    display_df = df_t[["week_number", "date_range", "avg_utilization", "total_idle_hours", "Trend", "Impact €"]].rename(columns={
        "week_number": "Woche", "date_range": "Zeitraum", "avg_utilization": "Ø Auslastung %", "total_idle_hours": "Idle (h)"
    })
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    try:
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_t["week_number"],
            y=df_t["avg_utilization"],
            mode="lines+markers",
            name="Auslastung %",
            line=dict(color="#0066CC", width=3),
            marker=dict(size=10),
        ))
        fig.add_hline(y=85, line_dash="dash", line_color="green", annotation_text="Ziel: 85%", annotation_position="right")
        fig.update_layout(title="Auslastungs-Trend über Wochen", xaxis_title="Woche", yaxis_title="Auslastung %", yaxis_range=[0, 100], height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    except Exception:
        pass

try:
    from backend.services.trends_service import calculate_weekly_trends
    _db = SessionLocal()
    trends = calculate_weekly_trends(_db, 90)
    _db.close()
    render_weekly_trends_section(trends)
except Exception as e:
    st.warning(f"Wochen-Vergleich nicht verfügbar: {e}")

# --- Utilization pro Robot ---
st.header("Utilization pro Robot")
st.caption("Prozentuale Auslastung pro Robot (24h-Tagesbasis), nur abgeschlossene Tage.")
if not df_util.empty:
    df_util_chart = (df_util_complete if not df_util_complete.empty else df_util).copy()
    df_util_chart = df_util_chart[df_util_chart["robot_name"].astype(str).str.contains("RPA-", na=False)]
    if df_util_chart.empty:
        df_util_chart = (df_util_complete if not df_util_complete.empty else df_util).copy()
    by_robot = df_util_chart.groupby("robot_name").agg(
        utilization_percent=("utilization_percent", "mean"),
        idle_hours=("idle_hours", "sum"),
    ).reset_index()
    by_robot["utilization_percent"] = by_robot["utilization_percent"].clip(upper=100.0)
    by_robot["display_name"] = by_robot["robot_name"].map(_display_robot_name)
    if not by_robot.empty:
        try:
            import plotly.express as px
            fig_util = px.bar(
                by_robot, x="display_name", y="utilization_percent",
                labels={"display_name": "Robot", "utilization_percent": "Utilization %"},
                title="Utilization pro Robot",
            )
            fig_util.update_layout(yaxis_range=[0, 100], showlegend=False)
            fig_util.update_yaxes(title_text="Utilization %")
            st.plotly_chart(fig_util, use_container_width=True)
        except Exception:
            st.bar_chart(by_robot.set_index("display_name")["utilization_percent"])
    else:
        st.caption("Keine Robot-Daten (RPA-DONALD-001 / RPA-MICKY-002) für Utilization.")
else:
    st.caption("Keine Utilization-Daten. Führe `python -m backend.calculate_utilization` aus.")

# --- Timeline (Gantt) ---
st.header("Timeline (Jobs)")
if not df_jobs.empty and df_jobs["end_time"].notna().any():
    try:
        import plotly.express as px
        gantt_df = df_jobs[df_jobs["end_time"].notna()].copy()
        gantt_df["Start"] = pd.to_datetime(gantt_df["start_time"])
        gantt_df["End"] = pd.to_datetime(gantt_df["end_time"])
        gantt_df["Task"] = gantt_df["process_name"] + " (" + gantt_df["job_key"].astype(str).str[:8] + ")"
        rk_col = "robot_key" if "robot_key" in gantt_df.columns else "robot_name"
        gantt_df["display_robot"] = gantt_df[rk_col].map(_display_robot_name)
        fig = px.timeline(
            gantt_df, x_start="Start", x_end="End", y="display_robot",
            color="state", title="Jobs nach Robot",
            custom_data=["process_name", "Start", "End", "display_robot", "state"],
        )
        fig.update_traces(
            hovertemplate="<b>%{customdata[0]}</b><br>Robot: %{customdata[3]}<br>Start: %{base}<br>Ende: %{x}<br>Status: %{customdata[4]}<extra></extra>"
        )
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"Timeline konnte nicht gezeichnet werden: {e}")
else:
    st.caption("Keine Jobs mit Endzeit für Timeline.")

# --- Leerlauf pro Tag ---
st.header("Leerlauf pro Tag")
st.caption("Pro Tag: Donald-Leerlauf + Mickey-Leerlauf (Zeiten, in denen ein Robot keinen Job hatte – Potenzial für mehr Prozesse). Nur abgeschlossene Tage.")
if not df_jobs.empty and df_jobs["end_time"].notna().any():
    def _format_idle_min(minutes: float) -> str:
        if minutes <= 0:
            return "0 min"
        h, m = divmod(int(minutes), 60)
        if h > 0:
            return f"{h}h {m}min"
        return f"{int(minutes)} min"

    start_dates = pd.to_datetime(df_jobs["start_time"]).dt.date
    end_dates = pd.to_datetime(df_jobs["end_time"]).dt.date
    all_dates_sorted = sorted(set(start_dates.dropna()) | set(end_dates.dropna()), reverse=True)
    completed_dates = [d for d in all_dates_sorted if d < today]
    dates_to_show = completed_dates[:7]

    for d in dates_to_show:
        day_start = datetime.combine(d, datetime.min.time())
        day_end = datetime.combine(d, datetime.max.time())
        start_ts = pd.to_datetime(df_jobs["start_time"])
        end_ts = pd.to_datetime(df_jobs["end_time"])
        day_jobs = df_jobs[
            (start_ts < pd.Timestamp(day_end))
            & (end_ts >= pd.Timestamp(day_start))
            & (df_jobs["end_time"].notna())
        ].copy()
        day_jobs = day_jobs[day_jobs["robot_key"].astype(str).str.contains("RPA-", na=False)]
        if day_jobs.empty:
            continue
        sum_idle_min_day = 0.0
        timeline_entries: list[dict] = []
        for rk in day_jobs["robot_key"].unique():
            rj = day_jobs[day_jobs["robot_key"] == rk].sort_values("start_time")
            prev_end = day_start
            for _, j in rj.iterrows():
                s, e = j["start_time"], j["end_time"]
                if s is None or e is None:
                    continue
                s = pd.Timestamp(s).to_pydatetime() if hasattr(s, "to_pydatetime") else s
                e = pd.Timestamp(e).to_pydatetime() if hasattr(e, "to_pydatetime") else e
                s_in = max(s, day_start)
                e_in = min(e, day_end)
                if e_in <= s_in:
                    continue
                if s_in > prev_end:
                    gap_min = (s_in - prev_end).total_seconds() / 60
                    sum_idle_min_day += gap_min
                    if gap_min >= 1:
                        timeline_entries.append({
                            "Von": prev_end, "Bis": s_in,
                            "Prozess": "— Leerlauf —", "Robot": _display_robot_name(rk),
                            "Dauer": _format_idle_min(gap_min), "Status": "",
                        })
                timeline_entries.append({
                    "Von": s_in, "Bis": e_in,
                    "Prozess": j["process_name"] or "(ohne Name)", "Robot": _display_robot_name(rk),
                    "Dauer": f"{int((e_in - s_in).total_seconds() // 3600)}h {int((e_in - s_in).total_seconds() % 3600 // 60)}min" if (e_in - s_in).total_seconds() >= 3600 else f"{int((e_in - s_in).total_seconds() // 60)}min",
                    "Status": j["state"] or "",
                })
                prev_end = max(prev_end, e_in)
            if prev_end < day_end:
                gap_min = (day_end - prev_end).total_seconds() / 60
                sum_idle_min_day += gap_min
                if gap_min >= 1:
                    timeline_entries.append({
                        "Von": prev_end, "Bis": day_end,
                        "Prozess": "— Leerlauf —", "Robot": _display_robot_name(rk),
                        "Dauer": _format_idle_min(gap_min), "Status": "",
                    })
        timeline_entries.sort(key=lambda x: x["Von"])
        sum_idle_min_day = min(sum_idle_min_day, 24 * 60 * 2)
        idle_str = _format_idle_min(sum_idle_min_day)
        with st.expander(f"**{d.strftime('%d.%m.%Y')}** — Leerlauf (Donald + Mickey): **{idle_str}**", expanded=False):
            if timeline_entries:
                tbl = pd.DataFrame(timeline_entries)
                tbl["Von"] = pd.to_datetime(tbl["Von"]).dt.strftime("%H:%M")
                tbl["Bis"] = pd.to_datetime(tbl["Bis"]).dt.strftime("%H:%M")
                st.caption("Chronologisch: Jobs und Leerläufe pro Robot (wann welcher Robot idle war)")
                st.dataframe(tbl[["Von", "Bis", "Prozess", "Robot", "Dauer", "Status"]], use_container_width=True, hide_index=True, column_config={
                    "Von": st.column_config.TextColumn("Von", width="small"),
                    "Bis": st.column_config.TextColumn("Bis", width="small"),
                    "Prozess": st.column_config.TextColumn("Prozess", width="large"),
                    "Robot": st.column_config.TextColumn("Robot", width="small"),
                    "Dauer": st.column_config.TextColumn("Dauer", width="small"),
                    "Status": st.column_config.TextColumn("Status", width="small"),
                })
            else:
                st.caption("Keine Daten für diesen Tag.")
else:
    st.caption("Keine Job-Daten mit Endzeit.")

# --- Quick Wins ---
def render_quickwins_section(quickwins_data: dict) -> None:
    st.header("Quick Wins – Sofort umsetzbare Optimierungen")
    with st.expander("Wie funktioniert Quick Wins?"):
        st.markdown("""
        **Recurring Idle (wiederkehrender Leerlauf)**  
        Pro Robot und pro Stunde wird geprüft: An wie vielen der letzten 7 Tage war der Robot in dieser Stunde **nicht** im Einsatz?
        Wenn in mindestens 4 von 7 Tagen Leerlauf herrschte und im Schnitt mehr als 30 Minuten idle sind, erscheint die Stunde als Quick Win.
        **In genau dieser Zeit könnt ihr neue Prozesse schedulen** – der Robot ist dort regelmäßig frei.

        **Unterlastete Zeitfenster**  
        Nacht (0–6 h), Morgen (6–12 h), Nachmittag (12–18 h), Abend (18–24 h): Wenn die Auslastung in einem Fenster unter 40 % liegt, wird es als unterausgelastet gemeldet.

        *Datenbasis: letzte 7 Tage, nur Donald & Mickey (RPA-Roboter).*
        """)
    if not quickwins_data or quickwins_data.get("total_impact_euro_month", 0) == 0:
        st.info("Keine Optimierungen gefunden – Bots sind gut ausgelastet oder zu wenig Daten (mind. 7 Tage).")
        return
    st.caption("Automatisch erkannt aus den letzten 7 Tagen")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Gesamt-Potential", f"{quickwins_data.get('total_potential_hours_week', 0)}h/Woche")
    with col2:
        st.metric("Business Impact", f"€{quickwins_data.get('total_impact_euro_month', 0):.0f}/Monat", delta="zusätzliche Kapazität", delta_color="normal")
    st.divider()
    win_number = 1
    for pattern in quickwins_data.get("recurring_idle", [])[:3]:
        with st.container():
            c1, c2, c3 = st.columns([3, 1, 1])
            with c1:
                st.subheader(f"#{win_number}: Recurring Idle – {pattern.get('robot', '')}")
                st.write(f"**{pattern.get('time_slot', '')}** – {pattern.get('frequency', '')} idle")
                st.write(f"Ø {pattern.get('avg_idle_minutes', 0):.0f} Minuten")
            with c2:
                st.metric("Potential", f"{pattern.get('potential_hours_week', 0):.1f}h/Woche")
            with c3:
                st.metric("Impact", f"€{pattern.get('impact_euro_month', 0):.0f}/Monat", delta=f"Prio: {pattern.get('priority', '')}")
        st.divider()
        win_number += 1
    for window in quickwins_data.get("underutilized_windows", [])[:2]:
        with st.container():
            c1, c2, c3 = st.columns([3, 1, 1])
            with c1:
                st.subheader(f"#{win_number}: Unterlastetes Zeitfenster")
                st.write(f"**{window.get('window', '')}**")
                st.write(f"Aktuelle Auslastung: {window.get('current_utilization', 0):.1f}%")
            with c2:
                st.metric("Potential", f"{window.get('potential_hours_week', 0):.1f}h/Woche")
            with c3:
                st.metric("Impact", f"€{window.get('impact_euro_month', 0):.0f}/Monat")
        st.divider()
        win_number += 1

try:
    from backend.services.quickwins_service import analyze_quickwins
    _db = SessionLocal()
    quickwins = analyze_quickwins(_db, days=7)
    _db.close()
    render_quickwins_section(quickwins)
except Exception as e:
    st.warning(f"Quick Wins Analyse nicht verfügbar: {e}")

# --- Excel Export ---
st.header("Excel-Export")
exports_dir = ROOT / "exports"
exports_dir.mkdir(exist_ok=True)

def build_excel() -> Path:
    from backend.services.export_service import export_daily_summary
    fname = exports_dir / f"rpa_performance_{date_end.isoformat()}.xlsx"
    db = SessionLocal()
    try:
        kpi_metrics = {"avg_util": avg_util, "idle_hours_sum": idle_hours_sum, "success_rate": rate, "impact": impact}
        return export_daily_summary(db, date_start, date_end, kpi_metrics, df_util, fname)
    finally:
        db.close()

if "export_path" not in st.session_state:
    st.session_state.export_path = None
if st.button("Excel exportieren"):
    try:
        path = build_excel()
        st.session_state.export_path = path
        st.success(f"Export erstellt: {path.name}")
    except Exception as e:
        st.error(f"Export fehlgeschlagen: {e}")
if st.session_state.export_path and st.session_state.export_path.exists():
    with open(st.session_state.export_path, "rb") as f:
        st.download_button("Download Excel", data=f.read(), file_name=st.session_state.export_path.name, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# --- Prozess-Detail: Laufzeiten & Scheduling ---
proc_df = _compute_process_stats(df_jobs)
st.header("Prozess-Detail: Laufzeiten & Scheduling")
st.caption("Für optimale Trigger-Planung: Runs, Success Rate, Ø-/Min-/Max-Laufzeit pro Prozess.")
if proc_df is not None and not proc_df.empty:
    detail = proc_df.sort_values("runs", ascending=False).copy()
    detail["Ø Dauer"] = detail["duration_mean"].apply(_format_duration)
    detail["Min"] = detail["duration_min"].apply(_format_duration)
    detail["Max (Worst-Case)"] = detail["duration_max"].apply(_format_duration)
    st.dataframe(
        detail[["process_name", "runs", "success_rate", "Ø Dauer", "Min", "Max (Worst-Case)"]].rename(
            columns={"process_name": "Prozess", "runs": "Runs", "success_rate": "Success Rate %"}
        ),
        use_container_width=True,
        hide_index=True,
    )
    try:
        import plotly.graph_objects as go
        n_chart = min(20, len(detail))
        chart_df = detail.head(n_chart).sort_values("runs", ascending=True)
        st.subheader("Runs pro Prozess (Wichtigkeit)")
        fig_runs = go.Figure(go.Bar(x=chart_df["runs"], y=chart_df["process_name"], orientation="h"))
        fig_runs.update_layout(xaxis_title="Anzahl Runs", height=400 + n_chart * 18, margin=dict(l=180), showlegend=False)
        st.plotly_chart(fig_runs, use_container_width=True)
        st.subheader("Success Rate pro Prozess")
        sr_colors = chart_df["success_rate"].apply(lambda x: "#2e7d32" if x >= 80 else "#f9a825" if x >= 50 else "#c62828").tolist()
        fig_sr = go.Figure(go.Bar(x=chart_df["success_rate"], y=chart_df["process_name"], orientation="h", marker_color=sr_colors))
        fig_sr.update_layout(xaxis_title="Success Rate %", xaxis_range=[0, 100], xaxis_dtick=10, height=400 + n_chart * 18, margin=dict(l=180), showlegend=False)
        st.plotly_chart(fig_sr, use_container_width=True)
        st.caption("Grün ≥80 %, Gelb 50–80 %, Rot <50 %")
        st.subheader("Prozess-Verlauf über die Zeit")
        st.caption("Prozess wählen, um zu sehen, wie sich Success Rate und Läufe im gewählten Zeitraum entwickelt haben.")
        selected_process = st.selectbox("Prozess auswählen", options=detail.sort_values("runs", ascending=False)["process_name"].tolist(), index=0, key="process_trend_select", label_visibility="collapsed")
        if selected_process and not df_jobs.empty:
            proc_jobs = df_jobs[df_jobs["process_name"] == selected_process].copy()
            if not proc_jobs.empty:
                proc_jobs["date"] = pd.to_datetime(proc_jobs["start_time"]).dt.date
                by_day = proc_jobs.groupby("date").agg(runs=("job_key", "count"), success=("state", lambda s: (s == "Successful").sum())).reset_index()
                by_day["success_rate"] = (by_day["success"] / by_day["runs"] * 100).round(1)
                by_day = by_day.sort_values("date")
                try:
                    fig_sr_trend = go.Figure()
                    fig_sr_trend.add_trace(go.Scatter(x=by_day["date"], y=by_day["success_rate"], mode="lines+markers", line=dict(color="#0066CC", width=2), marker=dict(size=8)))
                    fig_sr_trend.update_layout(title=f"Success Rate über die Zeit – „{selected_process}“", xaxis_title="Datum", yaxis_title="Success Rate %", yaxis_range=[0, 105], height=320, showlegend=False)
                    st.plotly_chart(fig_sr_trend, use_container_width=True)
                    fig_runs_trend = go.Figure(go.Bar(x=by_day["date"], y=by_day["runs"], marker_color="#B0BEC5"))
                    fig_runs_trend.update_layout(title=f"Läufe pro Tag – „{selected_process}“", xaxis_title="Datum", yaxis_title="Anzahl Läufe", height=280, showlegend=False)
                    st.plotly_chart(fig_runs_trend, use_container_width=True)
                except Exception:
                    st.dataframe(by_day.rename(columns={"date": "Datum", "runs": "Läufe", "success": "Erfolgreich", "success_rate": "Success Rate %"}), use_container_width=True, hide_index=True)
        st.subheader("Laufzeiten (Ø und Worst-Case)")
        duration_minutes_mean = chart_df["duration_mean"] / 60.0
        duration_minutes_max = chart_df["duration_max"] / 60.0
        fig_dur = go.Figure()
        fig_dur.add_trace(go.Bar(name="Ø Dauer (min)", x=chart_df["process_name"], y=duration_minutes_mean.round(1), marker_color="#0066CC"))
        fig_dur.add_trace(go.Bar(name="Max / Worst-Case (min)", x=chart_df["process_name"], y=duration_minutes_max.round(1), marker_color="#B0BEC5"))
        fig_dur.update_layout(barmode="group", xaxis_tickangle=-45, yaxis_title="Minuten", yaxis_rangemode="tozero", height=max(400, n_chart * 28), margin=dict(b=120, t=40), showlegend=True)
        st.plotly_chart(fig_dur, use_container_width=True)
    except Exception:
        pass
else:
    st.info("Keine Prozess-Daten für den gewählten Zeitraum.")
