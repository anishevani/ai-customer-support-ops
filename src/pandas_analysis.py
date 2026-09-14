"""Pandas ticket analysis: metrics first, printing second."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config import (
    COL_AGENT,
    COL_CATEGORY,
    COL_CHANNEL,
    COL_PRIORITY,
    COL_RESOLUTION_HOURS,
    COL_SATISFACTION,
    COL_SUBJECT,
    COL_TICKET_ID,
    LONG_RESOLUTION_HOURS,
    SATISFACTION_SCALE,
    default_tickets_csv,
    is_high_priority,
)


def load_tickets_frame(csv_path=None) -> pd.DataFrame:
    path = Path(csv_path) if csv_path is not None else default_tickets_csv()
    return pd.read_csv(path, encoding="utf-8")


def prepare_ticket_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Copy the frame and coerce numeric fields used in KPIs."""
    prepared = df.copy()
    prepared[COL_RESOLUTION_HOURS] = pd.to_numeric(
        prepared[COL_RESOLUTION_HOURS], errors="coerce"
    )
    prepared[COL_SATISFACTION] = pd.to_numeric(
        prepared[COL_SATISFACTION], errors="coerce"
    )
    if COL_CATEGORY in prepared.columns:
        category = prepared[COL_CATEGORY].astype("string").str.strip()
        prepared[COL_CATEGORY] = category.mask(category.isna() | (category == ""), "Unknown")
    return prepared


def _format_optional_hours(value: Optional[float]) -> str:
    if value is None or pd.isna(value):
        return "n/a (no valid times)"
    return f"{value:.2f} hours"


def compute_metrics(df: pd.DataFrame) -> dict:
    """Return analysis results as plain Python objects (easy to test)."""
    prepared = prepare_ticket_frame(df)
    hours = prepared[COL_RESOLUTION_HOURS]
    satisfaction = prepared[COL_SATISFACTION]
    high_mask = prepared[COL_PRIORITY].map(is_high_priority)
    long_mask = hours > LONG_RESOLUTION_HOURS

    high_preview_cols = [COL_TICKET_ID, COL_PRIORITY, COL_SUBJECT]
    long_preview_cols = [COL_TICKET_ID, COL_RESOLUTION_HOURS, COL_SUBJECT]
    high_preview_cols = [col for col in high_preview_cols if col in prepared.columns]
    long_preview_cols = [col for col in long_preview_cols if col in prepared.columns]

    return {
        "row_count": int(len(prepared)),
        "columns": prepared.columns.tolist(),
        "avg_resolution_hours": float(hours.mean()) if hours.notna().any() else None,
        "median_resolution_hours": float(hours.median()) if hours.notna().any() else None,
        "priority_counts": prepared[COL_PRIORITY].value_counts(dropna=False).to_dict(),
        "category_counts": prepared[COL_CATEGORY].value_counts(dropna=False).to_dict(),
        "channel_counts": prepared[COL_CHANNEL].value_counts(dropna=False).to_dict()
        if COL_CHANNEL in prepared.columns
        else {},
        "avg_satisfaction": float(satisfaction.mean()) if satisfaction.notna().any() else None,
        "high_priority_count": int(high_mask.sum()),
        "high_priority_preview": prepared.loc[high_mask, high_preview_cols].head(5),
        "long_ticket_count": int(long_mask.fillna(False).sum()),
        "long_ticket_preview": prepared.loc[long_mask.fillna(False), long_preview_cols].head(5),
        "avg_resolution_by_category": prepared.groupby(COL_CATEGORY, dropna=False)[COL_RESOLUTION_HOURS]
        .mean()
        .sort_values(ascending=False)
        .to_dict(),
        "avg_satisfaction_by_category": prepared.groupby(COL_CATEGORY, dropna=False)[COL_SATISFACTION]
        .mean()
        .sort_values()
        .to_dict(),
        "agent_counts": prepared[COL_AGENT].value_counts(dropna=False).to_dict()
        if COL_AGENT in prepared.columns
        else {},
    }


def format_report(metrics: dict) -> str:
    lines = [
        "========================================",
        "       TICKET ANALYSIS REPORT          ",
        "========================================",
        "",
        f"1. Total dataset rows: {metrics['row_count']}",
        "",
        "2. Columns in dataset:",
        f"   {metrics['columns']}",
        "",
        f"3. Average resolution time: {_format_optional_hours(metrics['avg_resolution_hours'])}",
        "   (pandas mean skips missing values; it does not treat blanks as zero)",
        "",
        f"4. Median resolution time: {_format_optional_hours(metrics['median_resolution_hours'])}",
        "   (use median alongside mean when a few very slow tickets pull the average up)",
        "",
        "5. Ticket counts by priority (includes missing labels):",
    ]
    for priority, count in metrics["priority_counts"].items():
        lines.append(f"   - {priority}: {count}")

    lines.extend(["", "6. Ticket counts by category (includes missing labels):"])
    for category, count in metrics["category_counts"].items():
        lines.append(f"   - {category}: {count}")

    avg_sat = metrics["avg_satisfaction"]
    sat_display = (
        f"{avg_sat:.2f} out of {SATISFACTION_SCALE}"
        if avg_sat is not None and not pd.isna(avg_sat)
        else "n/a"
    )
    lines.extend(
        [
            "",
            f"7. Average satisfaction score: {sat_display}",
            "",
            f"8. High / critical tickets found: {metrics['high_priority_count']}",
        ]
    )
    preview = metrics["high_priority_preview"]
    if len(preview.index) == 0:
        lines.append("   (none)")
    else:
        lines.append(f"   Showing first {len(preview)} of {metrics['high_priority_count']}:")
        lines.append(preview.to_string(index=False))

    lines.extend(
        [
            "",
            f"9. Tickets taking >{LONG_RESOLUTION_HOURS} hours: {metrics['long_ticket_count']}",
        ]
    )
    long_preview = metrics["long_ticket_preview"]
    if len(long_preview.index) == 0:
        lines.append("   (none)")
    else:
        lines.append(f"   Showing first {len(long_preview)} of {metrics['long_ticket_count']}:")
        lines.append(long_preview.to_string(index=False))

    lines.extend(["", "10. Average resolution time by category:"])
    for category, avg_time in metrics["avg_resolution_by_category"].items():
        lines.append(f"   - {category}: {_format_optional_hours(avg_time)}")

    lines.extend(["", "11. Average satisfaction by category:"])
    for category, avg_score in metrics["avg_satisfaction_by_category"].items():
        if avg_score is None or pd.isna(avg_score):
            lines.append(f"   - {category}: n/a")
        else:
            lines.append(f"   - {category}: {avg_score:.2f} / {SATISFACTION_SCALE}")

    lines.extend(["", "========================================"])
    return "\n".join(lines)


def run_ticket_analysis(df: pd.DataFrame) -> dict:
    """Compute metrics and print the report. Returns the metrics dict."""
    metrics = compute_metrics(df)
    print(format_report(metrics))
    return metrics


def main() -> None:
    csv_path = default_tickets_csv()
    try:
        frame = load_tickets_frame(csv_path)
    except FileNotFoundError:
        print(f"{csv_path} not found. Please verify the file path.")
        raise SystemExit(1)
    print(f"Source: {csv_path}")
    run_ticket_analysis(frame)


if __name__ == "__main__":
    main()
