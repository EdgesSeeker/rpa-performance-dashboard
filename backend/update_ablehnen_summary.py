"""
Erzeugt data/ablehnen_messstellen_summary.csv aus Claude Input/Ablehnen_Analyse/erledigt/
(ohne Malo-Daten – nur Tag + Anzahl Messstellen). Nur lokal ausführen; die Summary darf ins Repo.
Ausreißer 21.01.2026 wird auf 20 gesetzt.
Run: python -m backend.update_ablehnen_summary
"""
import re
import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
ERLEDIGT_DIR = ROOT / "Claude Input" / "Ablehnen_Analyse" / "erledigt"
OUTPUT_CSV = ROOT / "data" / "ablehnen_messstellen_summary.csv"
OUTLIER_DATE = date(2026, 1, 21)
OUTLIER_VALUE = 20


def main() -> None:
    if not ERLEDIGT_DIR.is_dir():
        print(f"Ordner nicht gefunden: {ERLEDIGT_DIR}")
        sys.exit(1)
    date_counts: list[tuple[date, int]] = []
    ts_fmt = "%d.%m.%Y %H:%M:%S"
    re_dates = re.compile(r"(\d{8})")
    for csv_path in ERLEDIGT_DIR.glob("*.csv"):
        try:
            df = pd.read_csv(csv_path, sep=";", encoding="utf-8", on_bad_lines="skip")
        except Exception:
            try:
                df = pd.read_csv(csv_path, sep=";", encoding="latin-1", on_bad_lines="skip")
            except Exception:
                continue
        if df.empty:
            continue
        matches = re_dates.findall(csv_path.stem)
        file_date: date | None = None
        if matches:
            last_ymd = matches[-1]
            file_date = datetime.strptime(last_ymd, "%Y%m%d").date()
        col_ts = None
        for c in ["RPA_Timestemp", "RPA_Timestemp ", "RPA_Timestamp"]:
            if c in df.columns:
                col_ts = c
                break
        if col_ts is None:
            col_ts = next((c for c in df.columns if "timestemp" in c.lower() or "timestamp" in c.lower()), None)
        if col_ts:
            for _, row in df.iterrows():
                val = row.get(col_ts)
                if pd.notna(val) and str(val).strip():
                    try:
                        dt = datetime.strptime(str(val).strip()[:19], ts_fmt)
                        date_counts.append((dt.date(), 1))
                    except ValueError:
                        if file_date is not None:
                            date_counts.append((file_date, 1))
                elif file_date is not None:
                    date_counts.append((file_date, 1))
        elif file_date is not None:
            date_counts.append((file_date, len(df)))
    if not date_counts:
        print("Keine Daten in erledigt/*.csv gefunden.")
        sys.exit(0)
    agg = pd.DataFrame(date_counts, columns=["date", "n"]).groupby("date", as_index=False)["n"].sum()
    agg.loc[agg["date"] == OUTLIER_DATE, "n"] = OUTLIER_VALUE
    agg = agg.sort_values("date").reset_index(drop=True)
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    agg.to_csv(OUTPUT_CSV, index=False)
    print(f"Geschrieben: {OUTPUT_CSV} ({len(agg)} Tage)")


if __name__ == "__main__":
    main()
