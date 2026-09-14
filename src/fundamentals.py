"""CSV-only ticket metrics. No pandas required."""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config import (
    COL_CATEGORY,
    COL_PRIORITY,
    COL_RESOLUTION_HOURS,
    default_tickets_csv,
    is_high_priority,
)


def load_tickets(csv_path) -> List[Dict[str, str]]:
    """Read a ticket extract into a list of row dictionaries."""
    with open(csv_path, encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def count_tickets(tickets: Sequence[Mapping]) -> int:
    """Return the total number of tickets."""
    return len(tickets)


def high_priority_tickets(tickets: Iterable[Mapping]) -> List[Mapping]:
    """Return tickets whose priority is High, Critical, or Urgent."""
    return [ticket for ticket in tickets if is_high_priority(ticket.get(COL_PRIORITY))]


def parse_resolution_hours(value) -> Optional[float]:
    """Convert a cell to hours. Blank, negative, or invalid values return None."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        hours = float(text)
    except ValueError:
        return None
    if hours < 0:
        return None
    return hours


def average_resolution_time(tickets: Iterable[Mapping]) -> Optional[float]:
    """Average resolution hours, ignoring blank or invalid cells.

    Returns None when no usable values exist so callers do not treat
    "no data" as a true zero-hour average.
    """
    hours = []
    for ticket in tickets:
        parsed = parse_resolution_hours(ticket.get(COL_RESOLUTION_HOURS))
        if parsed is not None:
            hours.append(parsed)
    if not hours:
        return None
    return sum(hours) / len(hours)


def tickets_by_category(tickets: Iterable[Mapping]) -> Dict[str, int]:
    """Count tickets for each issue category. Blank categories become Unknown."""
    counts: Counter = Counter()
    for ticket in tickets:
        category = str(ticket.get(COL_CATEGORY) or "").strip() or "Unknown"
        counts[category] += 1
    return dict(counts)


def format_metrics(tickets: Sequence[Mapping]) -> str:
    average_hours = average_resolution_time(tickets)
    if average_hours is None:
        average_display = "n/a (no valid times)"
    else:
        average_display = f"{average_hours:.2f} hours"

    category_counts = tickets_by_category(tickets)
    category_lines = ", ".join(
        f"{name}: {count}" for name, count in sorted(category_counts.items())
    )
    return (
        f"Total tickets: {count_tickets(tickets)}\n"
        f"High-priority tickets: {len(high_priority_tickets(tickets))}\n"
        f"Average resolution time: {average_display}\n"
        f"Tickets by category: {category_lines}"
    )


def main() -> None:
    csv_path = default_tickets_csv()
    try:
        tickets = load_tickets(csv_path)
    except FileNotFoundError:
        print(f"{csv_path} not found. Please verify the file path.")
        raise SystemExit(1)
    print(f"Source: {csv_path}")
    print(format_metrics(tickets))


if __name__ == "__main__":
    main()
