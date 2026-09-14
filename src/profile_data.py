"""Profile a ticket extract: shape, types, missing values, and distributions."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config import (
    COL_CATEGORY,
    COL_CHANNEL,
    COL_PRIORITY,
    COL_RESOLUTION_HOURS,
    COL_SATISFACTION,
    default_tickets_csv,
)
from src.pandas_analysis import load_tickets_frame, prepare_ticket_frame


def profile_tickets(df: pd.DataFrame) -> str:
    prepared = prepare_ticket_frame(df)
    lines = [
        "1. STRUCTURE",
        f"Rows: {len(prepared)}",
        f"Columns: {len(prepared.columns)}",
        "",
        "Column types:",
        prepared.dtypes.to_string(),
        "",
        "Preview:",
        prepared.head().to_string(index=False),
        "",
        "2. QUALITY",
        "Missing values per column:",
        prepared.isna().sum().to_string(),
        f"Duplicate rows: {int(prepared.duplicated().sum())}",
        "",
        "Unique values per text column:",
    ]
    text_cols = prepared.select_dtypes(include=["object", "string", "category"]).columns
    for col in text_cols:
        lines.append(f"  - {col}: {prepared[col].nunique(dropna=False)} unique values")

    lines.extend(
        [
            "",
            "3. STATISTICS",
            "Numeric summary:",
            prepared.describe().to_string(),
        ]
    )

    for title, column in (
        ("Priority distribution", COL_PRIORITY),
        ("Category distribution", COL_CATEGORY),
        ("Channel distribution", COL_CHANNEL),
        ("Satisfaction distribution", COL_SATISFACTION),
        ("Resolution-time summary", COL_RESOLUTION_HOURS),
    ):
        lines.extend(["", f"{title} ({column}):"])
        if column not in prepared.columns:
            lines.append(f"  [Column '{column}' not found]")
            continue
        if column == COL_RESOLUTION_HOURS:
            lines.append(prepared[column].describe().to_string())
        else:
            lines.append(prepared[column].value_counts(dropna=False).to_string())

    return "\n".join(lines)


def main() -> None:
    csv_path = default_tickets_csv()
    try:
        frame = load_tickets_frame(csv_path)
    except FileNotFoundError:
        print(f"{csv_path} not found. Please verify the file path.")
        raise SystemExit(1)
    print(f"Source: {csv_path}")
    print(profile_tickets(frame))


if __name__ == "__main__":
    main()
