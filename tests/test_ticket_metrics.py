from pathlib import Path

import pandas as pd
import pytest

from src.config import is_high_priority
from src.fundamentals import (
    average_resolution_time,
    count_tickets,
    high_priority_tickets,
    load_tickets,
    tickets_by_category,
)
from src.pandas_analysis import compute_metrics, load_tickets_frame

FIXTURE = Path(__file__).parent / "fixtures" / "mini_tickets.csv"


@pytest.fixture
def tickets():
    return load_tickets(FIXTURE)


def test_count_tickets(tickets):
    assert count_tickets(tickets) == 7


def test_high_priority_is_case_insensitive_and_includes_critical(tickets):
    high = high_priority_tickets(tickets)
    ids = {row["Ticket_ID"] for row in high}
    assert ids == {"TKT-1", "TKT-4", "TKT-5", "TKT-6"}
    assert is_high_priority("HIGH")
    assert is_high_priority(" Critical ")
    assert not is_high_priority("Low")


def test_average_resolution_time_skips_invalid_and_blank(tickets):
    # 5, 20, 8, 2, 12  -> 47 / 5
    assert average_resolution_time(tickets) == pytest.approx(9.4)


def test_average_resolution_time_returns_none_when_empty():
    assert average_resolution_time([{"Resolution_Time_Hours": ""}, {"Resolution_Time_Hours": "abc"}]) is None


def test_tickets_by_category_uses_unknown_for_blank(tickets):
    counts = tickets_by_category(tickets)
    assert counts["Technical"] == 2
    assert counts["Unknown"] == 1
    assert counts["Fraud"] == 1


def test_pandas_metrics_match_csv_rules():
    frame = load_tickets_frame(FIXTURE)
    metrics = compute_metrics(frame)
    assert metrics["row_count"] == 7
    assert metrics["high_priority_count"] == 4
    assert metrics["avg_resolution_hours"] == pytest.approx(9.4)
    assert metrics["category_counts"]["Unknown"] == 1
    assert metrics["long_ticket_count"] == 2  # 20h and 12h
    assert metrics["avg_satisfaction"] == pytest.approx(3.0)
