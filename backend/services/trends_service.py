"""
Weekly trends: aggregate daily_utilization by calendar week for Wochen-Vergleich.
"""
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from sqlalchemy.orm import Session

from backend.database import DailyUtilization

EUR_PER_HOUR = 50.0
WEEKS_PER_MONTH = 4.33


def calculate_weekly_trends(db: Session, last_n_days: int = 30) -> dict[str, Any]:
    """
    Load daily utilization for the last `last_n_days` days, group by ISO week,
    return structure for render_weekly_trends_section: weeks list + overall_trend.
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=last_n_days - 1)
    rows = (
        db.query(DailyUtilization)
        .filter(
            DailyUtilization.date >= start_date,
            DailyUtilization.date <= end_date,
        )
        .all()
    )
    # Filter RPA robots for KPI (optional: use all if you want)
    rpa_rows = [
        r for r in rows
        if r.robot_name and "RPA-" in str(r.robot_name)
    ]
    use_rows = rpa_rows if rpa_rows else rows

    # Group by (iso_year, iso_week)
    week_data: dict[tuple[int, int], list[tuple[date, float, float]]] = defaultdict(list)
    for r in use_rows:
        d = r.date
        if hasattr(d, "isocalendar"):
            iso = d.isocalendar()
            key = (iso[0], iso[1])
        else:
            key = (d.year, (d - date(d.year, 1, 1)).days // 7 + 1)
        week_data[key].append((d, r.utilization_percent or 0.0, r.idle_hours or 0.0))

    weeks_list: list[dict[str, Any]] = []
    for (iso_year, iso_week), items in sorted(week_data.items()):
        if not items:
            continue
        dates_in_week = [d for d, _, _ in items]
        min_d, max_d = min(dates_in_week), max(dates_in_week)
        avg_util = sum(u for _, u, _ in items) / len(items)
        total_idle = sum(h for _, _, h in items)
        date_range_str = f"{min_d.strftime('%d.%m.')} - {max_d.strftime('%d.%m.')}"
        week_label = f"{iso_year}-KW{iso_week:02d}"
        weeks_list.append({
            "week_number": week_label,
            "date_range": date_range_str,
            "avg_utilization": round(avg_util, 1),
            "total_idle_hours": round(total_idle, 1),
        })

    # Sort by week (oldest first for trend)
    weeks_list.sort(key=lambda x: x["week_number"])

    # Overall trend: first vs last week
    utilization_change = 0.0
    idle_reduction_hours_week = 0.0
    improvement_value_euro_month = 0.0
    if len(weeks_list) >= 2:
        first_util = weeks_list[0]["avg_utilization"]
        last_util = weeks_list[-1]["avg_utilization"]
        utilization_change = last_util - first_util
        first_idle = weeks_list[0]["total_idle_hours"]
        last_idle = weeks_list[-1]["total_idle_hours"]
        idle_reduction_hours_week = first_idle - last_idle  # positive = we reduced idle
        improvement_value_euro_month = idle_reduction_hours_week * WEEKS_PER_MONTH * EUR_PER_HOUR

    overall_trend = {
        "utilization_change": round(utilization_change, 1),
        "idle_reduction_hours_week": round(idle_reduction_hours_week, 1),
        "improvement_value_euro_month": round(improvement_value_euro_month, 0),
    }

    return {
        "weeks": weeks_list,
        "overall_trend": overall_trend,
    }
