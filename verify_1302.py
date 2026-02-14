"""
Verification: 13.02.2026 Job-Daten gegen Orchestrator prüfen.
Orchestrator: 33 Jobs, 13.02. 12:00 AM bis 11:00 PM (lokale Zeit).
"""
import sys
from pathlib import Path
from datetime import date, datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backend.database import SessionLocal, Job, init_tables

init_tables()


def _merge_intervals(intervals: list[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    if not intervals:
        return []
    sorted_i = sorted(intervals, key=lambda x: x[0])
    merged = [sorted_i[0]]
    for s, e in sorted_i[1:]:
        last_s, last_e = merged[-1]
        if s <= last_e:
            merged[-1] = (last_s, max(last_e, e))
        else:
            merged.append((s, e))
    return merged


def main():
    db = SessionLocal()
    d = date(2026, 2, 13)
    day_start = datetime.combine(d, datetime.min.time())
    day_end = datetime.combine(d, datetime.max.time())

    jobs = (
        db.query(Job)
        .filter(Job.start_time >= day_start, Job.start_time <= day_end)
        .order_by(Job.start_time)
        .all()
    )

    print(f"=== 13.02.2026 Verifikation ===\n")
    print(f"Anzahl Jobs (DB): {len(jobs)}")
    print(f"Orchestrator (laut User): 33 Jobs\n")

    if not jobs:
        print("Keine Jobs gefunden. Möglicherweise Timezone-Unterschied (API=UTC, Orchestrator= Lokal).")
        # Probiere auch 12.02 spät
        day_start_12 = datetime(2026, 2, 12, 23, 0, 0)
        jobs_12 = db.query(Job).filter(Job.start_time >= day_start_12, Job.start_time <= day_end).order_by(Job.start_time).all()
        print(f"Jobs 12.02 23:00 - 13.02 23:59: {len(jobs_12)}")
        jobs = jobs_12
        if jobs_12:
            jobs = jobs_12

    if jobs:
        first = jobs[0].start_time
        last = max(j.end_time or j.start_time for j in jobs)
        print(f"Erster Job Start: {first}")
        print(f"Letzter Job Ende:  {last}\n")

        # Host-Verteilung
        by_host: dict[str, int] = {}
        for j in jobs:
            mn = (j.machine_name or "").strip() or (j.robot_name or "?")
            by_host[mn] = by_host.get(mn, 0) + 1
        print("Jobs pro Host:", by_host)

        # Combined Idle
        intervals = []
        for j in jobs:
            s, e = j.start_time, j.end_time
            if s and e and e > s:
                intervals.append((s, e))
        merged = _merge_intervals(intervals)
        day_start_dt = datetime.combine(d, datetime.min.time())
        day_end_dt = datetime.combine(d, datetime.max.time())
        combined_idle_sec = 0.0
        prev_end = day_start_dt
        for s, e in merged:
            if s > prev_end:
                combined_idle_sec += (s - prev_end).total_seconds()
            prev_end = max(prev_end, e)
        if prev_end < day_end_dt:
            combined_idle_sec += (day_end_dt - prev_end).total_seconds()
        combined_idle_h = combined_idle_sec / 3600
        print(f"\nLeerlauf (beide Roboter, kein Job aktiv): {combined_idle_h:.2f}h")

        # Runtime
        total_runtime_sec = sum((j.end_time - j.start_time).total_seconds() for j in jobs if j.end_time and j.start_time and j.end_time > j.start_time)
        print(f"Gesamt-Laufzeit (alle Jobs): {total_runtime_sec / 3600:.2f}h")
        print(f"Verfügbar (24h): 24h")
        print(f"Nutzung: {(total_runtime_sec / 3600) / 24 * 100:.1f}%")

    db.close()


if __name__ == "__main__":
    main()
