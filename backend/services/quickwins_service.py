"""
Quick Wins analysis: recurring idle patterns and underutilized time windows.
"""
from collections import defaultdict
from datetime import datetime, timedelta, time
from typing import Any

from sqlalchemy.orm import Session

from backend.database import Job

EUR_PER_HOUR = 50.0
WEEKS_PER_MONTH = 4.33
IDLE_DAYS_THRESHOLD = 4
IDLE_AVG_MINUTES_THRESHOLD = 30.0
WINDOW_UTILIZATION_TARGET = 0.40  # 40%

WINDOWS = {
    "Nacht (00-06h)": (0, 6),
    "Morgen (06-12h)": (6, 12),
    "Nachmittag (12-18h)": (12, 18),
    "Abend (18-24h)": (18, 24),
}


def _to_naive(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if hasattr(dt, "tzinfo") and dt.tzinfo:
        return dt.replace(tzinfo=None)
    return dt


def _robot_key(job: Job) -> str:
    mn = (job.machine_name or "").strip()
    rn = job.robot_name or "Unknown"
    return mn if mn else rn


def _job_overlaps_hour(start: datetime, end: datetime, day: datetime.date, hour: int) -> float:
    """Return minutes of job runtime within the given day and hour (0-23)."""
    day_start = datetime.combine(day, time(hour, 0, 0))
    day_end = datetime.combine(day, time(hour, 59, 59, 999999))
    s = max(start, day_start)
    e = min(end, day_end)
    if e <= s:
        return 0.0
    return (e - s).total_seconds() / 60.0


def find_recurring_idle(jobs: list[Job], days: int) -> list[dict[str, Any]]:
    """
    Find time slots that are consistently idle (>= IDLE_DAYS_THRESHOLD days idle,
    and average idle duration in that hour > IDLE_AVG_MINUTES_THRESHOLD).
    """
    from datetime import date as date_type
    # Filter RPA-* only and normalize to naive datetime
    rpa_jobs: list[tuple[str, datetime, datetime]] = []
    for j in jobs:
        key = _robot_key(j)
        if "RPA-" not in (key or ""):
            continue
        start = _to_naive(j.start_time)
        end = _to_naive(j.end_time)
        if start is None or end is None or end <= start:
            continue
        rpa_jobs.append((key, start, end))

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    date_list = [start_date + timedelta(days=i) for i in range(days)]

    # Per (robot, day, hour): runtime minutes in that hour
    robot_hour_day_runtime: dict[str, dict[int, dict[date_type, float]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(float))
    )
    for robot, start, end in rpa_jobs:
        for d in date_list:
            for hour in range(24):
                mins = _job_overlaps_hour(start, end, d, hour)
                if mins > 0:
                    robot_hour_day_runtime[robot][hour][d] += mins

    result: list[dict[str, Any]] = []
    for robot in sorted(robot_hour_day_runtime.keys()):
        for hour in range(24):
            day_runtime = robot_hour_day_runtime[robot][hour]
            # For each day in range: idle = 60 - runtime (0 if no jobs that day = 60 min idle)
            idle_minutes_per_day: list[float] = []
            for d in date_list:
                runtime = day_runtime.get(d, 0.0)
                idle_minutes_per_day.append(max(0.0, 60.0 - runtime))
            days_idle = sum(1 for idle in idle_minutes_per_day if idle >= IDLE_AVG_MINUTES_THRESHOLD)
            total_idle_min = sum(idle_minutes_per_day)
            avg_idle = total_idle_min / days if days > 0 else 0.0
            if days_idle >= IDLE_DAYS_THRESHOLD and avg_idle >= IDLE_AVG_MINUTES_THRESHOLD:
                potential_hours_week = (avg_idle * 7) / 60.0
                impact_euro_month = potential_hours_week * WEEKS_PER_MONTH * EUR_PER_HOUR
                priority = "HIGH" if impact_euro_month >= 1000 else "MEDIUM" if impact_euro_month >= 500 else "LOW"
                result.append({
                    "robot": robot,
                    "time_slot": f"{hour:02d}:00-{hour + 1:02d}:00",
                    "frequency": f"{days_idle} von {days} Tagen",
                    "avg_idle_minutes": round(avg_idle, 1),
                    "potential_hours_week": round(potential_hours_week, 1),
                    "impact_euro_month": round(impact_euro_month, 0),
                    "priority": priority,
                })
    return result


def find_underutilized_windows(jobs: list[Job], days: int) -> list[dict[str, Any]]:
    """Find broad time windows with utilization < 40%."""
    rpa_jobs: list[tuple[datetime, datetime]] = []
    for j in jobs:
        key = _robot_key(j)
        if "RPA-" not in (key or ""):
            continue
        start = _to_naive(j.start_time)
        end = _to_naive(j.end_time)
        if start is None or end is None or end <= start:
            continue
        rpa_jobs.append((start, end))

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    date_list = [start_date + timedelta(days=i) for i in range(days)]

    result: list[dict[str, Any]] = []
    for window_name, (h_start, h_end) in WINDOWS.items():
        window_hours = h_end - h_start
        available_robot_hours = 2 * window_hours * days
        runtime_minutes = 0.0
        for start, end in rpa_jobs:
            for d in date_list:
                day_start = datetime.combine(d, time(h_start, 0, 0))
                day_end = datetime.combine(d, time(h_end - 1, 59, 59, 999999)) if h_end <= 24 else datetime.combine(d, time(23, 59, 59, 999999))
                s = max(start, day_start)
                e = min(end, day_end)
                if e > s:
                    runtime_minutes += (e - s).total_seconds() / 60.0
        runtime_hours = runtime_minutes / 60.0
        utilization = runtime_hours / available_robot_hours if available_robot_hours > 0 else 0.0
        if utilization < WINDOW_UTILIZATION_TARGET:
            potential_hours_week = (WINDOW_UTILIZATION_TARGET - utilization) * 2 * window_hours * 7
            impact_euro_month = potential_hours_week * WEEKS_PER_MONTH * EUR_PER_HOUR
            priority = "HIGH" if impact_euro_month >= 1000 else "MEDIUM" if impact_euro_month >= 500 else "LOW"
            result.append({
                "window": window_name,
                "current_utilization": round(utilization * 100, 1),
                "target": round(WINDOW_UTILIZATION_TARGET * 100, 0),
                "potential_hours_week": round(potential_hours_week, 1),
                "impact_euro_month": round(impact_euro_month, 0),
                "priority": priority,
            })
    return result


def _process_avg_durations_minutes(jobs: list[Job]) -> list[tuple[str, float]]:
    """Pro Prozess: (process_name, Ø Dauer in Minuten). Sortiert nach Dauer aufsteigend."""
    from collections import defaultdict
    by_process: dict[str, list[float]] = defaultdict(list)
    for j in jobs:
        name = (j.process_name or "").strip()
        if not name or j.start_time is None or j.end_time is None:
            continue
        start = _to_naive(j.start_time)
        end = _to_naive(j.end_time)
        if end is None or start is None or end <= start:
            continue
        mins = (end - start).total_seconds() / 60.0
        by_process[name].append(mins)
    result = [
        (name, sum(durs) / len(durs))
        for name, durs in by_process.items()
        if durs
    ]
    result.sort(key=lambda x: x[1])
    return result


def analyze_quickwins(db: Session, days: int = 7) -> dict[str, Any]:
    """
    Analyze last N days for optimization opportunities.
    Returns recurring_idle, underutilized_windows, totals, impact, and suggested processes per slot.
    """
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    t_start = datetime.combine(start_date, datetime.min.time())
    t_end = datetime.combine(end_date, datetime.max.time())

    jobs = (
        db.query(Job)
        .filter(
            Job.end_time.isnot(None),
            Job.start_time < t_end,
            Job.end_time >= t_start,
        )
        .all()
    )

    # Prozess-Ø-Dauern: zuerst 90-Tage-Fenster, Fallback = dieselben 7-Tage-Jobs wie für Quick Wins
    days_for_durations = 90
    start_dur = end_date - timedelta(days=days_for_durations)
    t_start_dur = datetime.combine(start_dur, datetime.min.time())
    jobs_for_durations = (
        db.query(Job)
        .filter(
            Job.end_time.isnot(None),
            Job.process_name.isnot(None),
            Job.start_time < t_end,
            Job.end_time >= t_start_dur,
        )
        .all()
    )
    process_durations = _process_avg_durations_minutes(jobs_for_durations)
    if not process_durations:
        process_durations = _process_avg_durations_minutes(jobs)

    recurring = find_recurring_idle(jobs, days)
    underutilized = find_underutilized_windows(jobs, days)

    # Prozessvorschläge: passen in die verfügbare Zeit (Ø Dauer <= avg_idle_minutes); sonst Fallback = kürzeste Prozesse
    max_suggestions = 5
    for r in recurring:
        avail_min = r.get("avg_idle_minutes", 0)
        fitting = [(name, round(dur, 1)) for name, dur in process_durations if 1 <= dur <= avail_min][:max_suggestions]
        r["suggested_processes"] = fitting if fitting else [(name, round(dur, 1)) for name, dur in process_durations[:max_suggestions]]
    # Unterlastete Fenster: Prozesse mit Ø Dauer bis 90 Min; sonst kürzeste
    window_max_min = 90
    for u in underutilized:
        fitting = [(name, round(dur, 1)) for name, dur in process_durations if 1 <= dur <= window_max_min][:max_suggestions]
        u["suggested_processes"] = fitting if fitting else [(name, round(dur, 1)) for name, dur in process_durations[:max_suggestions]]

    total_hours = sum(r["potential_hours_week"] for r in recurring) + sum(u["potential_hours_week"] for u in underutilized)
    total_impact = total_hours * WEEKS_PER_MONTH * EUR_PER_HOUR

    return {
        "recurring_idle": sorted(recurring, key=lambda x: x["impact_euro_month"], reverse=True),
        "underutilized_windows": sorted(underutilized, key=lambda x: x["impact_euro_month"], reverse=True),
        "total_potential_hours_week": round(total_hours, 1),
        "total_impact_euro_month": round(total_impact, 0),
    }
