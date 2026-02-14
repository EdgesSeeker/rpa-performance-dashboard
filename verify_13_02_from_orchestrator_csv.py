"""
Abgleich 13.02.2026: Orchestrator-CSV vs. Dashboard-Tagesansicht.
Verwendet die gleiche Leerlauf-Logik wie die App (nur RPA-*, pro Robot Lücken, Tag 00:00–23:59).
"""
import csv
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# CSV-Pfad (Orchestrator-Export)
CSV_PATH = Path(r"c:\UiPath\jobs-1b4bdd9a-2ec0-4e32-b388-ffb396751c9b-2026-02-14-11-56-37-463-193486\jobs-1b4bdd9a-2ec0-4e32-b388-ffb396751c9b-2026-02-14-11-56-37-463-193486.csv")
DAY = date(2026, 2, 13)
DAY_START = datetime.combine(DAY, datetime.min.time())
DAY_END = datetime.combine(DAY, datetime.max.time())


def parse_ts(s: str) -> datetime | None:
    if not s or not s.strip():
        return None
    s = s.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s[:26], fmt)
        except ValueError:
            continue
    return None


def main():
    if not CSV_PATH.exists():
        print(f"CSV nicht gefunden: {CSV_PATH}")
        print("Bitte Pfad anpassen oder CSV dorthin kopieren.")
        return

    # Alle Jobs, die mit dem 13.02 überlappen (Start vor Ende 13.02, Ende nach Start 13.02)
    rows = []
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            host = (row.get("Hostname") or "").strip()
            if host not in ("RPA-DONALD-001", "RPA-MICKY-002"):
                continue
            start_dt = parse_ts(row.get("Started (absolute)", ""))
            end_dt = parse_ts(row.get("Ended (absolute)", ""))
            if start_dt is None or end_dt is None:
                continue
            if end_dt <= DAY_START or start_dt >= DAY_END:
                continue
            rows.append({
                "host": host,
                "process": (row.get("Process") or "").strip(),
                "state": (row.get("State") or "").strip(),
                "start": start_dt,
                "end": end_dt,
            })

    # Pro Robot: nur Zeiten innerhalb 13.02 (s, e, process)
    by_host: dict[str, list[tuple[datetime, datetime, str]]] = {}
    for r in rows:
        host = r["host"]
        s = max(r["start"], DAY_START)
        e = r["end"]
        if e is None or e <= s:
            continue
        e = min(e, DAY_END)
        if e <= s:
            continue
        by_host.setdefault(host, []).append((s, e, r.get("process", "")[:50]))

    for host in by_host:
        by_host[host].sort(key=lambda x: x[0])

    sum_idle_min = 0.0
    print(f"\n=== 13.02.2026 - Abgleich mit Orchestrator-CSV ===\n")
    print(f"Jobs mit Start am 13.02. und Host RPA-DONALD-001 / RPA-MICKY-002: {sum(len(by_host[h]) for h in by_host)}")

    for host in sorted(by_host.keys()):
        intervals = by_host[host]
        prev_end = DAY_START
        idle_min_robot = 0.0
        print(f"\n--- {host} ---")
        for s, e, proc in intervals:
            if s > prev_end:
                gap_min = (s - prev_end).total_seconds() / 60
                idle_min_robot += gap_min
                if gap_min >= 1:
                    print(f"  Leerlauf {prev_end.strftime('%H:%M')}-{s.strftime('%H:%M')}: {int(gap_min)} min")
            print(f"  Job {s.strftime('%H:%M')}-{e.strftime('%H:%M')}: {proc}")
            prev_end = max(prev_end, e)
        if prev_end < DAY_END:
            gap_min = (DAY_END - prev_end).total_seconds() / 60
            idle_min_robot += gap_min
            if gap_min >= 1:
                print(f"  Leerlauf {prev_end.strftime('%H:%M')}-24:00: {int(gap_min)} min")
        sum_idle_min += idle_min_robot
        print(f"  => Idle {host}: {idle_min_robot / 60:.2f} h")

    h, m = divmod(int(sum_idle_min), 60)
    print(f"\n** Erwarteter Leerlauf (Donald + Mickey) am 13.02.: {h}h {m}min**")
    print("\nVergleiche diese Zahl mit der Tagesansicht im Dashboard (Leerlauf pro Tag -> 13.02.2026).")


if __name__ == "__main__":
    main()
