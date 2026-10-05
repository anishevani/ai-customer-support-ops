"""Load support tickets from CSV into PostgreSQL.

CSV -> Pandas -> stg_support_tickets -> validation -> support_tickets
Rejected rows are written to data/processed/rejected_rows.csv.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import psycopg

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config import PROJECT_ROOT, default_tickets_csv
from src.db import connect
from src.logger import configure_logging, get_logger

logger = get_logger(__name__)

SCHEMA_PATH = PROJECT_ROOT / "sql" / "03_schema.sql"
REJECTED_ROWS_PATH = PROJECT_ROOT / "data" / "processed" / "rejected_rows.csv"

ALLOWED_PRIORITIES = {
    "low": "Low",
    "medium": "Medium",
    "high": "High",
    "critical": "Critical",
    "urgent": "Urgent",
}

STAGING_COLUMNS = (
    "ticket_id",
    "customer_name",
    "customer_email",
    "ticket_subject",
    "ticket_description",
    "issue_category",
    "priority_level",
    "ticket_channel",
    "submission_date",
    "resolution_time_hours",
    "assigned_agent",
    "satisfaction_score",
)

REQUIRED_COLUMNS = (
    "ticket_id",
    "customer_name",
    "customer_email",
    "issue_category",
    "priority_level",
    "ticket_channel",
    "submission_date",
)


def _normalize_column_name(name: str) -> str:
    text = str(name).strip().lower().replace("-", " ").replace("_", " ")
    return "_".join(text.split())


def _is_missing(value) -> bool:
    if value is None:
        return True
    try:
        missing = pd.isna(value)
    except (TypeError, ValueError):
        return False
    return bool(missing)


def _strip_text(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()
    for column in cleaned.columns:
        if pd.api.types.is_string_dtype(cleaned[column]) or cleaned[column].dtype == object:
            text = cleaned[column].astype("string").str.strip()
            cleaned[column] = text.mask(text.isna() | (text == ""), pd.NA)
    return cleaned


def _rejection_reasons(df: pd.DataFrame) -> pd.Series:
    """First failing rule for each row. A missing reason means the row is accepted."""
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {', '.join(missing)}")

    working = _strip_text(df)
    reasons = pd.Series(pd.NA, index=working.index, dtype="string")

    ticket_id = working["ticket_id"]
    reasons = reasons.mask(ticket_id.isna(), "missing ticket_id")
    duplicate = ticket_id.duplicated(keep="first") & ticket_id.notna()
    reasons = reasons.mask(duplicate & reasons.isna(), "duplicate ticket_id")

    if "issue_category" in working.columns:
        working["issue_category"] = working["issue_category"].fillna("Unknown")

    typed = convert_types(working)
    priority_key = typed["priority_level"].astype("string").str.strip().str.casefold()
    missing_priority = typed["priority_level"].isna() & reasons.isna()
    reasons = reasons.mask(missing_priority, "missing priority_level")
    unknown_priority = ~priority_key.isin(ALLOWED_PRIORITIES) & reasons.isna()
    reasons = reasons.mask(unknown_priority, "unknown priority")

    for column in REQUIRED_COLUMNS:
        if column in {"ticket_id", "priority_level"}:
            continue
        missing_value = typed[column].isna() & reasons.isna()
        if column == "submission_date":
            blank_date = working["submission_date"].isna() & reasons.isna()
            reasons = reasons.mask(blank_date, "missing submission_date")
            reasons = reasons.mask(missing_value & reasons.isna(), "invalid submission_date")
            continue
        reasons = reasons.mask(missing_value, f"missing {column}")

    if "resolution_time_hours" in typed.columns:
        hours = typed["resolution_time_hours"]
        negative_hours = hours.notna() & (hours < 0) & reasons.isna()
        reasons = reasons.mask(negative_hours, "negative resolution_time_hours")
    return reasons


def _text_rows(df: pd.DataFrame, columns: tuple[str, ...]) -> list[tuple]:
    subset = df.reindex(columns=list(columns))
    rows = []
    for record in subset.itertuples(index=False, name=None):
        rows.append(tuple(None if _is_missing(value) else str(value) for value in record))
    return rows


def _clean_rows(df: pd.DataFrame) -> list[tuple]:
    rows = []
    for record in df.itertuples(index=False):
        submitted = record.submission_date
        if isinstance(submitted, pd.Timestamp):
            submitted = submitted.date()
        elif _is_missing(submitted):
            submitted = None

        hours = record.resolution_time_hours
        hours = None if _is_missing(hours) else float(hours)

        score = record.satisfaction_score
        score = None if _is_missing(score) else int(score)

        def text(value):
            return None if _is_missing(value) else str(value)

        rows.append(
            (
                text(record.ticket_id),
                text(record.customer_name),
                text(record.customer_email),
                text(record.ticket_subject),
                text(record.ticket_description),
                text(record.issue_category),
                text(record.priority_level),
                text(record.ticket_channel),
                submitted,
                hours,
                text(record.assigned_agent),
                score,
            )
        )
    return rows


def _copy_rows(cursor, sql: str, rows: list[tuple]) -> None:
    if not rows:
        return
    with cursor.copy(sql) as copy:
        for row in rows:
            copy.write_row(row)


def _execute_script(connection, path: Path) -> None:
    script = path.read_text()
    with connection.cursor() as cursor:
        for statement in script.split(";"):
            if statement.strip():
                cursor.execute(statement)
    connection.commit()


def _ensure_schema(connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT c.relname
            FROM pg_class AS c
            JOIN pg_namespace AS n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public'
              AND c.relkind = 'r'
              AND c.relname IN ('stg_support_tickets', 'support_tickets')
            """
        )
        found = {row[0] for row in cursor.fetchall()}
    if found == {"stg_support_tickets", "support_tickets"}:
        return
    logger.info("Creating ticket tables from %s", SCHEMA_PATH)
    _execute_script(connection, SCHEMA_PATH)


def _read_staging(connection) -> pd.DataFrame:
    column_list = ", ".join(STAGING_COLUMNS)
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT {column_list}
            FROM stg_support_tickets
            ORDER BY stg_ticket_id
            """
        )
        rows = cursor.fetchall()
    frame = pd.DataFrame(rows, columns=list(STAGING_COLUMNS))
    if frame.empty:
        return frame.astype("string")
    return frame.astype("string")


def extract_data(csv_path=None) -> pd.DataFrame:
    """Read a ticket CSV as text so later steps own the type conversion."""
    path = Path(csv_path) if csv_path is not None else default_tickets_csv()
    logger.info("Extracting tickets from %s", path)
    frame = pd.read_csv(path, encoding="utf-8", dtype="string")
    logger.info("Extracted %s rows", len(frame))
    return frame


def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Strip CSV headers and convert them to snake_case."""
    cleaned = df.copy()
    cleaned.columns = [_normalize_column_name(column) for column in cleaned.columns]
    logger.info("Cleaned column names: %s", ", ".join(map(str, cleaned.columns)))
    return cleaned


def clean_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """Trim text, turn blanks into missing values, and drop unusable ticket ids."""
    cleaned = _strip_text(df)
    if "issue_category" in cleaned.columns:
        cleaned["issue_category"] = cleaned["issue_category"].fillna("Unknown")

    before = len(cleaned)
    if "ticket_id" in cleaned.columns:
        cleaned = cleaned.dropna(subset=["ticket_id"])
        cleaned = cleaned.drop_duplicates(subset=["ticket_id"], keep="first")
    dropped = before - len(cleaned)
    if dropped:
        logger.info("Dropped %s rows with a blank or duplicate ticket_id", dropped)
    return cleaned.reset_index(drop=True)


def convert_types(df: pd.DataFrame) -> pd.DataFrame:
    """Parse dates and numbers. Invalid cells become missing, not zero."""
    converted = df.copy()
    if "submission_date" in converted.columns:
        converted["submission_date"] = pd.to_datetime(
            converted["submission_date"], errors="coerce"
        )
    if "resolution_time_hours" in converted.columns:
        converted["resolution_time_hours"] = pd.to_numeric(
            converted["resolution_time_hours"], errors="coerce"
        )
    if "satisfaction_score" in converted.columns:
        converted["satisfaction_score"] = pd.to_numeric(
            converted["satisfaction_score"], errors="coerce"
        )
    logger.info("Converted submission date, resolution hours, and satisfaction score")
    return converted


def validate_data(df: pd.DataFrame) -> pd.DataFrame:
    """Keep rows that can load: known priority, required fields, hours >= 0."""
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {', '.join(missing)}")

    validated = df.copy()
    priority_key = validated["priority_level"].astype("string").str.strip().str.casefold()
    known_priority = priority_key.isin(ALLOWED_PRIORITIES)
    rejected_priority = int((~known_priority).sum())
    validated = validated.loc[known_priority].copy()
    validated["priority_level"] = priority_key.loc[known_priority].map(ALLOWED_PRIORITIES)

    rejected_negative = 0
    if "resolution_time_hours" in validated.columns:
        hours = validated["resolution_time_hours"]
        negative_hours = hours.notna() & (hours < 0)
        rejected_negative = int(negative_hours.sum())
        validated = validated.loc[~negative_hours].copy()

    if "satisfaction_score" in validated.columns:
        scores = validated["satisfaction_score"]
        valid_score = scores.isna() | (scores.between(1, 5) & scores.eq(scores.round()))
        invalid_scores = int((~valid_score).sum())
        if invalid_scores:
            logger.info("Cleared %s satisfaction scores outside 1-5", invalid_scores)
        validated.loc[~valid_score, "satisfaction_score"] = pd.NA
        validated["satisfaction_score"] = validated["satisfaction_score"].astype("Int64")

    before = len(validated)
    validated = validated.dropna(subset=list(REQUIRED_COLUMNS))
    rejected_required = before - len(validated)
    if rejected_priority or rejected_required or rejected_negative:
        logger.info(
            "Rejected %s rows (%s unknown priority, %s missing required fields, %s negative hours)",
            rejected_priority + rejected_required + rejected_negative,
            rejected_priority,
            rejected_required,
            rejected_negative,
        )
    logger.info("Validated %s tickets", len(validated))
    return validated.reset_index(drop=True)


def split_validated_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split a snake_case frame into rows to load and rows to reject."""
    reasons = _rejection_reasons(df)
    for reason, count in reasons.dropna().value_counts().items():
        logger.info("Rejected %s rows: %s", int(count), reason)
    rejected = df.loc[reasons.notna()].copy()
    rejected["rejection_reason"] = reasons.loc[reasons.notna()].astype("string").to_numpy()
    accepted_source = df.loc[reasons.isna()].copy()
    accepted = validate_data(convert_types(clean_missing_values(accepted_source)))
    if rejected.empty:
        columns = list(df.columns)
        if "rejection_reason" not in columns:
            columns.append("rejection_reason")
        rejected = pd.DataFrame(columns=columns)
    return accepted, rejected.reset_index(drop=True)


def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean names, fill gaps, convert types, then validate."""
    cleaned = clean_column_names(df)
    accepted, _rejected = split_validated_rows(cleaned)
    return accepted


def write_rejected_rows(rejected: pd.DataFrame, path: Path = REJECTED_ROWS_PATH) -> Path:
    """Write rejected tickets to CSV. An empty file still keeps the header."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rejected.to_csv(path, index=False)
    logger.info("Wrote %s rejected rows to %s", len(rejected), path)
    return path


def load_staging(df: pd.DataFrame, connection=None) -> int:
    """Replace stg_support_tickets with the current extract. Values stay text."""
    if "ticket_id" not in df.columns:
        df = clean_column_names(df)
    rows = _text_rows(df, STAGING_COLUMNS)
    own_connection = connection is None
    connection = connect() if own_connection else connection
    column_list = ", ".join(STAGING_COLUMNS)
    try:
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE stg_support_tickets")
            _copy_rows(
                cursor,
                f"COPY stg_support_tickets ({column_list}) FROM STDIN",
                rows,
            )
        if own_connection:
            connection.commit()
    except Exception:
        if own_connection:
            connection.rollback()
        raise
    finally:
        if own_connection:
            connection.close()
    logger.info("Loaded %s rows into stg_support_tickets", len(rows))
    return len(rows)


def load_clean(df: pd.DataFrame, connection=None) -> int:
    """Replace support_tickets with the accepted rows."""
    rows = _clean_rows(df)
    own_connection = connection is None
    connection = connect() if own_connection else connection
    column_list = ", ".join(STAGING_COLUMNS)
    try:
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE support_tickets CASCADE")
            _copy_rows(
                cursor,
                f"COPY support_tickets ({column_list}) FROM STDIN",
                rows,
            )
        if own_connection:
            connection.commit()
    except Exception:
        if own_connection:
            connection.rollback()
        raise
    finally:
        if own_connection:
            connection.close()
    logger.info("Loaded %s rows into support_tickets", len(rows))
    return len(rows)


def run_etl(csv_path=None) -> dict[str, int]:
    """Load the CSV through staging and validation, then record the counts."""
    raw = extract_data(csv_path)
    rows_input = len(raw)
    named = clean_column_names(raw)

    connection = connect()
    try:
        _ensure_schema(connection)
        load_staging(named, connection)
        staged = _read_staging(connection)
        rows_staging = len(staged)
        accepted, rejected = split_validated_rows(staged)
        write_rejected_rows(rejected)
        rows_accepted = load_clean(accepted, connection)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    rows_rejected = len(rejected)
    if rows_staging != rows_input:
        raise RuntimeError(
            f"Staging row count {rows_staging} does not match input {rows_input}"
        )
    if rows_accepted + rows_rejected != rows_staging:
        raise RuntimeError(
            "Accepted plus rejected rows do not match staging "
            f"({rows_accepted} + {rows_rejected} != {rows_staging})"
        )
    return {
        "rows_input": rows_input,
        "rows_staging": rows_staging,
        "rows_accepted": rows_accepted,
        "rows_rejected": rows_rejected,
    }


def main() -> None:
    configure_logging()
    try:
        counts = run_etl()
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        raise SystemExit(1) from None
    except psycopg.errors.InsufficientPrivilege:
        logger.error(
            "The database user in .env cannot write stg_support_tickets "
            "or support_tickets. Grant INSERT, DELETE, and TRUNCATE on those tables."
        )
        raise SystemExit(1) from None
    except Exception:
        logger.exception("PostgreSQL load failed")
        raise SystemExit(1) from None

    print(f"Rows input: {counts['rows_input']}")
    print(f"Rows staging: {counts['rows_staging']}")
    print(f"Rows accepted: {counts['rows_accepted']}")
    print(f"Rows rejected: {counts['rows_rejected']}")


if __name__ == "__main__":
    main()
