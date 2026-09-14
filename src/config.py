"""Shared paths, column names, and business rules."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"

FULL_TICKETS_CSV = DATA_RAW_DIR / "customer_support_tickets.csv"
SAMPLE_TICKETS_CSV = DATA_RAW_DIR / "sample_tickets.csv"

COL_TICKET_ID = "Ticket_ID"
COL_CUSTOMER_NAME = "Customer_Name"
COL_CUSTOMER_EMAIL = "Customer_Email"
COL_SUBJECT = "Ticket_Subject"
COL_DESCRIPTION = "Ticket_Description"
COL_CATEGORY = "Issue_Category"
COL_PRIORITY = "Priority_Level"
COL_CHANNEL = "Ticket_Channel"
COL_SUBMITTED = "Submission_Date"
COL_RESOLUTION_HOURS = "Resolution_Time_Hours"
COL_AGENT = "Assigned_Agent"
COL_SATISFACTION = "Satisfaction_Score"

# Matches this dataset: High and Critical. Urgent is included so older exports still work.
HIGH_PRIORITY_LABELS = frozenset({"high", "critical", "urgent"})

SATISFACTION_SCALE = 5
LONG_RESOLUTION_HOURS = 10


def default_tickets_csv() -> Path:
    """Prefer the full local extract; fall back to the committed sample file."""
    if FULL_TICKETS_CSV.exists():
        return FULL_TICKETS_CSV
    if SAMPLE_TICKETS_CSV.exists():
        return SAMPLE_TICKETS_CSV
    raise FileNotFoundError(
        "No ticket CSV found. Place customer_support_tickets.csv or "
        f"sample_tickets.csv in {DATA_RAW_DIR}"
    )


def normalize_label(value) -> str:
    """Strip whitespace and ignore letter case. Empty cells become ''."""
    if value is None:
        return ""
    return str(value).strip().casefold()


def is_high_priority(value) -> bool:
    return normalize_label(value) in HIGH_PRIORITY_LABELS
