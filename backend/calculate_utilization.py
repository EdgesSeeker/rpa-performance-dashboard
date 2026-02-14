"""
Calculate daily utilization per robot (24/7 basis) from jobs and store in daily_utilization.
Run: python -m backend.calculate_utilization
"""
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import and_
from backend.database import SessionLocal, Job, DailyUtilization, init_tables


def _to_date(dt: datetime | date) -> date:
    if isinstance(dt, date) and not isinstance(dt, datetime):
        return dt
    return dt.date() if hasattr(dt, "date") else dt


def _to_naive(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if hasattr(dt, "tzinfo") and dt.tzinfo:
        return dt.replace(tzinfo=None)
    return dt


def _merge_intervals(ranges: list[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    if not ranges:
        return []
    sorted_r = sorted(ranges, key=lambda x: x[0])
    out = [sorted_r[0]]
    for s, e in sorted_r[1:]:
        lo, hi = out[-1]
        if s <= hi:
            out[-1] = (lo, max(hi, e))
        else:
            out.append((s, e))
    return out


def calculate_and_store() -> int:
    """Compute utilization per robot per day and upsert into daily_utilization. Returns rows updated."""
    init_tables()
    db = SessionLocal()
    try:
        jobs = db.query(Job).order_by(Job.robot_name, Job.start_time).all()
        # Group by (date, robot_name): list of (start, end) clipped to that day (Job kann mehrere Tage überlappen)
        by_day_robot: dict[tuple[date, str], list[tuple[datetime, datetime]]] = defaultdict(list)
        for j in jobs:
            start = _to_naive(j.start_time) if j.start_time else None
            end = _to_naive(j.end_time) if j.end_time else None
            if start is None or end is None or end <= start:
                continue
            rn = j.robot_name or "Unknown"
            mn = (j.machine_name or "").strip()
            robot_key = mn if mn else rn
            d_start = _to_date(start)
            d_end = _to_date(end)
            # Job allen Kalendertagen zuordnen, die er überlappt (Abgleich mit Orchestrator/CSV)
            for i in range((d_end - d_start).days + 1):
                d = d_start + timedelta(days=i)
                day_start = datetime.combine(d, datetime.min.time())
                day_end = datetime.combine(d, datetime.max.time())
                if start >= day_end or end <= day_start:
                    continue
                clip_start = max(start, day_start)
                clip_end = min(end, day_end)
                if clip_end > clip_start:
                    by_day_robot[(d, robot_key)].append((clip_start, clip_end))

        count = 0
        for (d, robot_key), ranges in by_day_robot.items():
            day_start = datetime.combine(d, datetime.min.time())
            day_end = datetime.combine(d, datetime.max.time())
            merged = _merge_intervals(ranges)
            total_seconds = 0.0
            for start, end in merged:
                if end is None or end <= start:
                    continue
                clip_start = max(start, day_start)
                clip_end = min(end, day_end)
                if clip_end > clip_start:
                    total_seconds += (clip_end - clip_start).total_seconds()
            total_hours = min(24.0, total_seconds / 3600.0)  # Sicherheitscap
            available_hours = 24.0  # 24/7
            utilization_percent = (total_hours / available_hours) * 100.0 if available_hours else 0.0
            idle_hours = max(0.0, available_hours - total_hours)

            existing = db.query(DailyUtilization).filter(
                and_(DailyUtilization.date == d, DailyUtilization.robot_name == robot_key)
            ).first()
            if existing:
                existing.total_runtime_hours = total_hours
                existing.idle_hours = idle_hours
                existing.utilization_percent = utilization_percent
            else:
                db.add(DailyUtilization(
                    date=d,
                    robot_name=robot_key,
                    total_runtime_hours=total_hours,
                    idle_hours=idle_hours,
                    utilization_percent=utilization_percent,
                ))
            count += 1
        db.commit()
        return count
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    n = calculate_and_store()
    print(f"Updated {n} daily utilization rows.")
