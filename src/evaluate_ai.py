"""Score model output against the hand-labeled evaluation sheet."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.ai_service import (
    CATEGORY_ACTION,
    PROMPT_VERSION,
    TicketAnalysis,
    analyze_ticket,
    load_model_settings,
    make_client,
)
from src.logger import configure_logging, get_logger

logger = get_logger(__name__)

EVAL_PATH = _ROOT / "evaluation" / "eval_tickets.csv"
RESULTS_PATH = _ROOT / "docs" / "ai-evaluation-results.md"
PRIORITY_RANK = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}


def load_eval_rows(path: Path = EVAL_PATH) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def error_labels(
    expected: dict[str, str],
    actual: TicketAnalysis | None,
    invalid: bool,
) -> list[str]:
    """Name the failure modes on one ticket. A clean ticket returns no labels."""
    if invalid or actual is None:
        return ["Invalid output"]
    labels = []
    ambiguous = expected.get("ambiguous", "").strip().casefold() == "yes"
    if actual.category != expected["expected_category"]:
        labels.append("Ambiguous ticket" if ambiguous else "Wrong classification")
    if actual.priority != expected["expected_priority"]:
        if PRIORITY_RANK[actual.priority] > PRIORITY_RANK[expected["expected_priority"]]:
            labels.append("Over-escalation")
        else:
            labels.append("Under-escalation")
    if actual.recommended_action != CATEGORY_ACTION[actual.category]:
        labels.append("Unsupported recommendation")
    prose = f"{actual.summary} {actual.reason} {actual.recommended_action}".casefold()
    forbidden = (
        "refund issued",
        "refund has been",
        "have emailed the customer",
        "sent the customer",
        "known outage",
        "incident is underway",
    )
    if any(phrase in prose for phrase in forbidden):
        labels.append("Bad prompt")
    return labels


def exact_rate(matches: int, total: int) -> str:
    if total == 0:
        return "n/a"
    return f"{matches / total:.1%} ({matches}/{total})"


def score_rows(rows: list[dict], predictions: list[tuple[TicketAnalysis | None, str]]) -> dict:
    """Aggregate exact-match rates and error labels."""
    total = len(rows)
    category_hits = 0
    priority_hits = 0
    sentiment_hits = 0
    invalid = 0
    label_counts = {
        "Ambiguous ticket": 0,
        "Bad prompt": 0,
        "Wrong classification": 0,
        "Unsupported recommendation": 0,
        "Over-escalation": 0,
        "Under-escalation": 0,
        "Invalid output": 0,
    }
    misses = []
    for row, (prediction, failure) in zip(rows, predictions):
        is_invalid = prediction is None
        if is_invalid:
            invalid += 1
        else:
            if prediction.category == row["expected_category"]:
                category_hits += 1
            if prediction.priority == row["expected_priority"]:
                priority_hits += 1
            if prediction.sentiment == row["expected_sentiment"]:
                sentiment_hits += 1
        labels = error_labels(row, prediction, is_invalid)
        for label in labels:
            label_counts[label] += 1
        if labels or (
            prediction is not None
            and prediction.sentiment != row["expected_sentiment"]
        ):
            misses.append(
                {
                    "ticket_id": row["ticket_id"],
                    "expected_category": row["expected_category"],
                    "expected_priority": row["expected_priority"],
                    "expected_sentiment": row["expected_sentiment"],
                    "actual_category": "" if prediction is None else prediction.category,
                    "actual_priority": "" if prediction is None else prediction.priority,
                    "actual_sentiment": "" if prediction is None else prediction.sentiment,
                    "labels": labels,
                    "failure": failure,
                }
            )
    return {
        "total": total,
        "category": exact_rate(category_hits, total - invalid),
        "priority": exact_rate(priority_hits, total - invalid),
        "sentiment": exact_rate(sentiment_hits, total - invalid),
        "invalid": invalid,
        "label_counts": label_counts,
        "misses": misses,
        "category_hits": category_hits,
        "priority_hits": priority_hits,
        "sentiment_hits": sentiment_hits,
    }


def render_results(model: str, token_line: str, scored: dict) -> str:
    lines = [
        "# AI evaluation results",
        "",
        f"Prompt version `{PROMPT_VERSION}`. Model `{model}`.",
        "Ground truth is `evaluation/eval_tickets.csv`. The scorer compares category, priority, and sentiment with exact text match.",
        "Exact-match rates use valid outputs only. Invalid outputs are counted on their own.",
        "",
        token_line,
        "",
        "| Check | Result |",
        "| --- | --- |",
        f"| Tickets | {scored['total']} |",
        f"| Category exact match | {scored['category']} |",
        f"| Priority exact match | {scored['priority']} |",
        f"| Sentiment exact match | {scored['sentiment']} |",
        f"| Invalid outputs | {scored['invalid']} |",
        "",
        "A ticket can carry more than one error label. Sentiment misses stay in the table above. They are listed below when category and priority already match.",
        "",
        "| Error category | Tickets |",
        "| --- | --- |",
    ]
    for label, count in scored["label_counts"].items():
        lines.append(f"| {label} | {count} |")
    lines.extend(["", "## Misses", ""])
    if not scored["misses"]:
        lines.append("No misses.")
    else:
        lines.extend(
            [
                "| Ticket | Expected | Model | Error labels |",
                "| --- | --- | --- | --- |",
            ]
        )
        for miss in scored["misses"]:
            expected = (
                f"{miss['expected_category']} / {miss['expected_priority']} / "
                f"{miss['expected_sentiment']}"
            )
            actual = miss["failure"] or (
                f"{miss['actual_category']} / {miss['actual_priority']} / "
                f"{miss['actual_sentiment']}"
            )
            labels = ", ".join(miss["labels"]) if miss["labels"] else "Sentiment mismatch"
            lines.append(
                f"| {miss['ticket_id']} | {expected} | {actual} | {labels} |"
            )
    lines.append("")
    return "\n".join(lines)


def evaluate(write_path: Path = RESULTS_PATH) -> dict:
    rows = load_eval_rows()
    model = load_model_settings()
    client = make_client()
    predictions = []
    input_tokens = 0
    output_tokens = 0
    for row in rows:
        try:
            analysis, response = analyze_ticket(
                client,
                model,
                row["ticket_subject"],
                row["ticket_description"],
            )
            usage = getattr(response, "usage", None)
            if usage is not None:
                input_tokens += usage.input_tokens or 0
                output_tokens += usage.output_tokens or 0
            predictions.append((analysis, ""))
            logger.info("Scored %s as %s", row["ticket_id"], analysis.category)
        except Exception as exc:
            logger.exception("Invalid output for %s", row["ticket_id"])
            predictions.append((None, exc.__class__.__name__))
    scored = score_rows(rows, predictions)
    token_line = (
        f"Token use for this run: input {input_tokens}, output {output_tokens}. "
        "Dollar cost depends on the price for this model. This file does not convert tokens to dollars."
    )
    write_path.write_text(render_results(model, token_line, scored), encoding="utf-8")
    return scored


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description="Evaluate ticket classification.")
    parser.add_argument("--output", type=Path, default=RESULTS_PATH)
    args = parser.parse_args()
    try:
        scored = evaluate(args.output)
    except Exception:
        logger.exception("Evaluation failed")
        raise SystemExit(1) from None
    print(
        f"Wrote {args.output} category={scored['category']} "
        f"priority={scored['priority']} sentiment={scored['sentiment']} "
        f"invalid={scored['invalid']}"
    )


if __name__ == "__main__":
    main()
