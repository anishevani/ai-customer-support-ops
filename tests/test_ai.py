"""AI contract checks that do not call the API."""

import csv

import pytest
from pydantic import ValidationError

from src.ai_service import (
    ACTIONS,
    CATEGORIES,
    CATEGORY_ACTION,
    PRIORITIES,
    SAMPLE_SENTENCES,
    SENTIMENTS,
    UPSERT_SQL,
    TicketAnalysis,
    customer_sentence,
    load_csv_tickets,
    select_sample,
    ticket_prompt,
)
from src.evaluate_ai import error_labels, load_eval_rows, score_rows


def analysis(**overrides) -> TicketAnalysis:
    values = {
        "category": "Authentication",
        "priority": "High",
        "sentiment": "Frustrated",
        "summary": "Customer cannot access account.",
        "recommended_action": "Route to identity support queue.",
        "reason": "The customer still cannot log in after a reset.",
    }
    values.update(overrides)
    return TicketAnalysis(**values)


def test_contract_rejects_a_refund_action():
    with pytest.raises(ValidationError):
        analysis(recommended_action="Issue the refund now.")


def test_prompt_omits_customer_email():
    text = ticket_prompt("Login failed", "I cannot log into my account.")
    assert "example.com" not in text
    assert "Subject: Login failed" in text


def test_upsert_does_not_touch_source_columns():
    statement = UPSERT_SQL.casefold()
    assert "ai_ticket_enrichment" in statement
    assert "update support_tickets" not in statement
    assert "issue_category" not in statement
    assert "priority_level" not in statement


def test_sample_covers_ten_sentences():
    sample = select_sample(load_csv_tickets(), limit=10)
    assert len(sample) == 10
    sentences = {customer_sentence(row["ticket_description"]) for row in sample}
    assert sentences == set(SAMPLE_SENTENCES)


def test_eval_sheet_matches_the_hand_labels():
    rows = load_eval_rows()
    assert 25 <= len(rows) <= 30
    seen = set()
    for row in rows:
        assert row["expected_category"] in CATEGORIES
        assert row["expected_priority"] in PRIORITIES
        assert row["expected_sentiment"] in SENTIMENTS
        assert row["ambiguous"] in {"yes", "no"}
        seen.add(row["ticket_id"])
    assert len(seen) == len(rows)


def test_error_labels_for_a_clean_match():
    expected = {
        "expected_category": "Billing",
        "expected_priority": "High",
        "expected_sentiment": "Frustrated",
        "ambiguous": "no",
    }
    prediction = analysis(
        category="Billing",
        priority="High",
        recommended_action="Route to billing queue.",
    )
    assert error_labels(expected, prediction, invalid=False) == []


def test_ambiguous_subject_is_not_called_a_plain_miss():
    expected = {
        "expected_category": "Account",
        "expected_priority": "Low",
        "expected_sentiment": "Neutral",
        "ambiguous": "yes",
    }
    prediction = analysis(
        category="Authentication",
        priority="High",
        sentiment="Frustrated",
        recommended_action="Route to identity support queue.",
    )
    labels = error_labels(expected, prediction, invalid=False)
    assert "Ambiguous ticket" in labels
    assert "Over-escalation" in labels
    assert "Wrong classification" not in labels


def test_wrong_queue_is_an_unsupported_recommendation():
    expected = {
        "expected_category": "Technical",
        "expected_priority": "High",
        "expected_sentiment": "Frustrated",
        "ambiguous": "no",
    }
    prediction = analysis(
        category="Technical",
        priority="Low",
        recommended_action="Route to billing queue.",
    )
    labels = error_labels(expected, prediction, invalid=False)
    assert "Unsupported recommendation" in labels
    assert "Under-escalation" in labels


def test_score_rows_separates_invalid_output():
    rows = [
        {
            "ticket_id": "TKT-1",
            "expected_category": "Fraud",
            "expected_priority": "Critical",
            "expected_sentiment": "Concerned",
            "ambiguous": "no",
        }
    ]
    scored = score_rows(rows, [(None, "RateLimitError")])
    assert scored["invalid"] == 1
    assert scored["category_hits"] == 0
    assert scored["label_counts"]["Invalid output"] == 1


def test_each_category_has_one_queue():
    assert set(CATEGORY_ACTION) == set(CATEGORIES)
    assert set(CATEGORY_ACTION.values()) <= set(ACTIONS)


def test_eval_csv_has_the_sentence_columns():
    from src.config import PROJECT_ROOT

    path = PROJECT_ROOT / "evaluation" / "eval_tickets.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert "expected_category" in reader.fieldnames
        assert "source_issue_category" in reader.fieldnames
