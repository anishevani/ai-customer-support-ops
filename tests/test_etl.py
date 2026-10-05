"""ETL rules: compare the expected result with what the pipeline returns."""

import pandas as pd

from src.etl import split_validated_rows


def ticket(**overrides) -> dict:
    """One valid ticket. Tests override the field they care about."""
    row = {
        "ticket_id": "TKT-1",
        "customer_name": "Ada Lovelace",
        "customer_email": "ada@example.com",
        "issue_category": "Technical",
        "priority_level": "High",
        "ticket_channel": "Email",
        "submission_date": "2025-01-04",
        "resolution_time_hours": "5",
        "satisfaction_score": "4",
    }
    row.update(overrides)
    return row


def test_negative_resolution_time_is_rejected():
    accepted, rejected = split_validated_rows(
        pd.DataFrame([ticket(resolution_time_hours="-2")])
    )

    expected_reason = "negative resolution_time_hours"
    actual_reason = rejected.loc[0, "rejection_reason"]

    assert accepted.empty
    assert actual_reason == expected_reason


def test_valid_priority_is_accepted():
    accepted, rejected = split_validated_rows(
        pd.DataFrame([ticket(priority_level="high")])
    )

    expected_priority = "High"
    actual_priority = accepted.loc[0, "priority_level"]

    assert rejected.empty
    assert actual_priority == expected_priority


def test_null_ticket_id_is_rejected():
    accepted, rejected = split_validated_rows(
        pd.DataFrame([ticket(ticket_id="")])
    )

    expected_reason = "missing ticket_id"
    actual_reason = rejected.loc[0, "rejection_reason"]

    assert accepted.empty
    assert actual_reason == expected_reason


def test_duplicate_ticket_id_is_detected():
    rows = pd.DataFrame(
        [
            ticket(ticket_id="TKT-9"),
            ticket(ticket_id="TKT-9", customer_name="Grace Hopper"),
        ]
    )
    accepted, rejected = split_validated_rows(rows)

    expected_reason = "duplicate ticket_id"
    actual_reason = rejected.loc[0, "rejection_reason"]

    assert list(accepted["ticket_id"]) == ["TKT-9"]
    assert len(accepted) == 1
    assert actual_reason == expected_reason


def test_submission_date_is_parsed():
    accepted, rejected = split_validated_rows(pd.DataFrame([ticket()]))

    expected_date = pd.Timestamp("2025-01-04")
    actual_date = accepted.loc[0, "submission_date"]

    assert rejected.empty
    assert actual_date == expected_date
