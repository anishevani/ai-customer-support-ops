"""Reconcile the CSV, staging, clean tickets, and rejected rows."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config import COL_CATEGORY, COL_PRIORITY, COL_SUBMITTED, COL_TICKET_ID, default_tickets_csv
from src.db import connect
from src.etl import ALLOWED_PRIORITIES, REJECTED_ROWS_PATH, REQUIRED_COLUMNS

LABEL_WIDTH = 26
VALUE_WIDTH = 10
PRIORITY_ORDER = ("Low", "Medium", "High", "Critical", "Urgent")


def _row(label: str, value: object) -> str:
    if isinstance(value, bool):
        text = "YES" if value else "NO"
    elif isinstance(value, int):
        text = f"{value:,}"
    else:
        text = str(value)
    return f"{label:<{LABEL_WIDTH}}{text:>{VALUE_WIDTH}}"


def _count_row(label: str, value: int) -> str:
    return f"  {label:<{LABEL_WIDTH - 2}}{value:>{VALUE_WIDTH},}"


def _normalize_category(values: pd.Series) -> pd.Series:
    text = values.astype("string").str.strip()
    return text.mask(text.isna() | (text == ""), "Unknown")


def _normalize_priority(values: pd.Series) -> pd.Series:
    text = values.astype("string").str.strip()
    canonical = text.str.casefold().map(ALLOWED_PRIORITIES)
    return canonical.fillna(text).fillna("Unknown")


def _value_counts(values: pd.Series) -> dict[str, int]:
    return {str(name): int(count) for name, count in values.value_counts(dropna=False).items()}


def _duplicate_id_count(values: pd.Series) -> int:
    text = values.astype("string").str.strip()
    text = text.mask(text.isna() | (text == ""), pd.NA)
    counts = text.dropna().value_counts()
    return int((counts > 1).sum())


def _parse_dates(values: pd.Series) -> pd.Series:
    return pd.to_datetime(values, errors="coerce")


def _date_bounds(values: pd.Series) -> tuple[str | None, str | None]:
    parsed = _parse_dates(values).dropna()
    if parsed.empty:
        return None, None
    return parsed.min().date().isoformat(), parsed.max().date().isoformat()


def _read_source(csv_path: Path) -> pd.DataFrame:
    return pd.read_csv(csv_path, encoding="utf-8", dtype="string")


def _read_rejected(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=["ticket_id", "issue_category", "priority_level", "submission_date"])
    return pd.read_csv(path, encoding="utf-8", dtype="string")


def _fetch_database(connection) -> dict:
    null_filters = " OR ".join(f"{column} IS NULL" for column in REQUIRED_COLUMNS)
    null_columns = ", ".join(
        f"COUNT(*) FILTER (WHERE {column} IS NULL) AS {column}" for column in REQUIRED_COLUMNS
    )
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM stg_support_tickets")
        staging_rows = int(cursor.fetchone()[0])
        cursor.execute("SELECT COUNT(*) FROM support_tickets")
        clean_rows = int(cursor.fetchone()[0])
        cursor.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT ticket_id
                FROM stg_support_tickets
                WHERE ticket_id IS NOT NULL AND btrim(ticket_id) <> ''
                GROUP BY ticket_id
                HAVING COUNT(*) > 1
            ) AS duplicate_ids
            """
        )
        staging_duplicates = int(cursor.fetchone()[0])
        cursor.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT ticket_id
                FROM support_tickets
                WHERE ticket_id IS NOT NULL AND btrim(ticket_id) <> ''
                GROUP BY ticket_id
                HAVING COUNT(*) > 1
            ) AS duplicate_ids
            """
        )
        clean_duplicates = int(cursor.fetchone()[0])
        cursor.execute(
            f"""
            SELECT COUNT(*) FILTER (WHERE {null_filters}) AS null_rows, {null_columns}
            FROM support_tickets
            """
        )
        null_row = cursor.fetchone()
        cursor.execute(
            """
            SELECT issue_category, COUNT(*)
            FROM support_tickets
            GROUP BY issue_category
            """
        )
        categories = {name: int(count) for name, count in cursor.fetchall()}
        cursor.execute(
            """
            SELECT priority_level, COUNT(*)
            FROM support_tickets
            GROUP BY priority_level
            """
        )
        priorities = {name: int(count) for name, count in cursor.fetchall()}
        cursor.execute("SELECT MIN(submission_date), MAX(submission_date) FROM support_tickets")
        minimum, maximum = cursor.fetchone()
    null_columns = {
        column: int(count)
        for column, count in zip(REQUIRED_COLUMNS, null_row[1:])
        if int(count)
    }
    return {
        "staging_rows": staging_rows,
        "clean_rows": clean_rows,
        "staging_duplicates": staging_duplicates,
        "clean_duplicates": clean_duplicates,
        "null_rows": int(null_row[0]),
        "null_columns": null_columns,
        "categories": categories,
        "priorities": priorities,
        "min_date": None if minimum is None else minimum.isoformat(),
        "max_date": None if maximum is None else maximum.isoformat(),
    }


def _add_counts(left: dict[str, int], right: dict[str, int]) -> dict[str, int]:
    keys = set(left) | set(right)
    return {key: left.get(key, 0) + right.get(key, 0) for key in keys}


def _ordered_items(counts: dict[str, int], first: tuple[str, ...] = ()) -> list[tuple[str, int]]:
    remaining = sorted(set(counts) - set(first))
    ordered = [name for name in first if name in counts]
    ordered.extend(remaining)
    return [(name, counts[name]) for name in ordered]


def collect_report(csv_path: Path | None = None, rejected_path: Path = REJECTED_ROWS_PATH) -> dict:
    """Compare the extract, PostgreSQL, and rejected-row file."""
    source_path = Path(csv_path) if csv_path is not None else default_tickets_csv()
    source = _read_source(source_path)
    rejected = _read_rejected(rejected_path)
    connection = connect()
    try:
        database = _fetch_database(connection)
    finally:
        connection.close()

    source_categories = _value_counts(_normalize_category(source[COL_CATEGORY]))
    source_priorities = _value_counts(_normalize_priority(source[COL_PRIORITY]))
    rejected_categories = _value_counts(
        _normalize_category(rejected.get("issue_category", pd.Series(dtype="string")))
    )
    rejected_priorities = _value_counts(
        _normalize_priority(rejected.get("priority_level", pd.Series(dtype="string")))
    )
    if rejected.empty:
        rejected_categories = {}
        rejected_priorities = {}

    source_min, source_max = _date_bounds(source[COL_SUBMITTED])
    rejected_min, rejected_max = _date_bounds(
        rejected.get("submission_date", pd.Series(dtype="string"))
    )
    clean_min = database["min_date"]
    clean_max = database["max_date"]
    covered_min = min((value for value in (clean_min, rejected_min) if value), default=None)
    covered_max = max((value for value in (clean_max, rejected_max) if value), default=None)

    source_rows = len(source)
    rejected_rows = len(rejected)
    reconciled = source_rows == database["clean_rows"] + rejected_rows
    categories_match = source_categories == _add_counts(database["categories"], rejected_categories)
    priorities_match = source_priorities == _add_counts(database["priorities"], rejected_priorities)
    dates_match = source_min == covered_min and source_max == covered_max

    return {
        "source_rows": source_rows,
        "staging_rows": database["staging_rows"],
        "clean_rows": database["clean_rows"],
        "rejected_rows": rejected_rows,
        "reconciled": reconciled,
        "source_duplicates": _duplicate_id_count(source[COL_TICKET_ID]),
        "staging_duplicates": database["staging_duplicates"],
        "clean_duplicates": database["clean_duplicates"],
        "null_rows": database["null_rows"],
        "null_columns": database["null_columns"],
        "categories": database["categories"],
        "categories_match": categories_match,
        "priorities": database["priorities"],
        "priorities_match": priorities_match,
        "source_min_date": source_min,
        "source_max_date": source_max,
        "clean_min_date": clean_min,
        "clean_max_date": clean_max,
        "dates_match": dates_match,
    }


def format_report(report: dict) -> str:
    """Render the reconciliation checks."""
    lines = [
        "ETL VALIDATION REPORT",
        "",
        _row("Source rows:", report["source_rows"]),
        _row("Staging rows:", report["staging_rows"]),
        _row("Loaded:", report["clean_rows"]),
        _row("Rejected:", report["rejected_rows"]),
        _row("Reconciled:", report["reconciled"]),
        _row("Duplicate ticket IDs:", report["clean_duplicates"]),
        _count_row("source:", report["source_duplicates"]),
        _count_row("staging:", report["staging_duplicates"]),
        _count_row("clean:", report["clean_duplicates"]),
        _row("Null critical columns:", report["null_rows"]),
    ]
    for column, count in report["null_columns"].items():
        lines.append(_count_row(f"{column}:", count))

    lines.extend(["", f"Category counts: {'YES' if report['categories_match'] else 'NO'}"])
    for name, count in _ordered_items(report["categories"]):
        lines.append(_count_row(f"{name}:", count))

    lines.extend(["", f"Priority counts: {'YES' if report['priorities_match'] else 'NO'}"])
    for name, count in _ordered_items(report["priorities"], PRIORITY_ORDER):
        lines.append(_count_row(f"{name}:", count))

    lines.extend(
        [
            "",
            f"Submission dates: {report['clean_min_date']} to {report['clean_max_date']}",
            _row("Dates match source:", report["dates_match"]),
        ]
    )
    if not report["dates_match"]:
        lines.append(
            f"Source dates: {report['source_min_date']} to {report['source_max_date']}"
        )
    return "\n".join(lines)


def report_passed(report: dict) -> bool:
    return bool(
        report["reconciled"]
        and report["clean_duplicates"] == 0
        and report["null_rows"] == 0
        and report["categories_match"]
        and report["priorities_match"]
        and report["dates_match"]
    )


def main() -> None:
    try:
        report = collect_report()
    except FileNotFoundError as exc:
        print(exc)
        raise SystemExit(1) from None
    except Exception as exc:
        print(f"PostgreSQL validation failed: {exc}")
        raise SystemExit(1) from None
    print(format_report(report))
    if not report_passed(report):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
