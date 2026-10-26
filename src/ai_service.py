"""Classify a support ticket into the AI contract and store the result.

The original issue_category and priority_level on support_tickets stay as loaded.
Results are written only to ai_ticket_enrichment.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError
from pydantic import BaseModel, Field

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config import PROJECT_ROOT, default_tickets_csv
from src.logger import configure_logging, get_logger

logger = get_logger(__name__)

PROMPT_VERSION = "ticket-analysis-v1"
ENV_PATH = PROJECT_ROOT / ".env"

CATEGORIES = (
    "Authentication",
    "Account",
    "Billing",
    "Technical",
    "Fraud",
    "General Inquiry",
)
PRIORITIES = ("Critical", "High", "Medium", "Low")
SENTIMENTS = ("Frustrated", "Concerned", "Neutral", "Urgent")
ACTIONS = (
    "Route to identity support queue.",
    "Route to account support queue.",
    "Route to billing queue.",
    "Route to technical support queue.",
    "Route to fraud review queue.",
    "Route to general support queue.",
)

# The action that matches each category. Evaluation uses this map.
CATEGORY_ACTION = {
    "Authentication": "Route to identity support queue.",
    "Account": "Route to account support queue.",
    "Billing": "Route to billing queue.",
    "Technical": "Route to technical support queue.",
    "Fraud": "Route to fraud review queue.",
    "General Inquiry": "Route to general support queue.",
}

# Ten customer sentences used for the first structured-output check.
SAMPLE_SENTENCES = (
    "I cannot log into my account even after resetting the password.",
    "I lost my phone and cannot pass the 2FA check.",
    "I noticed a double charge on my statement for last month.",
    "I requested a refund 5 days ago, where is it?",
    "The application crashes every time I open the settings tab.",
    "We are receiving a 500 Internal Server Error on the API endpoint.",
    "I think my account has been compromised.",
    "Lock my account immediately, I see transactions I didn't make.",
    "What are your support operating hours?",
    "How do I upgrade to the Enterprise plan?",
)

SYSTEM_PROMPT = """You classify one customer support ticket for an internal human queue.

Use the customer's request in the description. The subject line is often an unrelated template. When the subject and the description disagree, follow the description.

category must be one of: Authentication, Account, Billing, Technical, Fraud, General Inquiry.
priority must be one of: Critical, High, Medium, Low.
sentiment must be one of: Frustrated, Concerned, Neutral, Urgent.
recommended_action must be one of:
- Route to identity support queue.
- Route to account support queue.
- Route to billing queue.
- Route to technical support queue.
- Route to fraud review queue.
- Route to general support queue.

Priority:
- Critical: the customer reports a compromised account, a stolen card, transactions they did not make, or tells you to lock the account now.
- High: the customer is blocked, or money is wrong right now. Examples: cannot log in, cannot pass 2FA, password reset email never arrives, payment fails, double charge, refund not received, app crash, API 500, dashboard stuck, data not syncing.
- Medium: a billing dispute that is not a duplicate charge, a cancellation, an invoice copy, an email change, or an account deletion.
- Low: a how-to or an information question. Examples: hours, office location, pricing explanation, demo, discount, roadmap, install steps, profile picture.

Sentiment:
- Urgent: the customer demands immediate action, such as locking the account now.
- Concerned: a security worry without that immediate demand.
- Frustrated: something is broken, late, or charged incorrectly.
- Neutral: a plain question or request.

Choose the queue that matches the category: identity for Authentication, account for Account, billing for Billing, technical for Technical, fraud review for Fraud, and general support for General Inquiry.

Do not issue a refund. Do not draft or send a customer-facing message. Do not invent order numbers, balances, devices, or account facts that the ticket does not state. Do not say an incident or outage exists unless the ticket itself reports one. summary and reason must stay inside the ticket text.
"""

UPSERT_SQL = """
INSERT INTO ai_ticket_enrichment (
    ticket_id,
    ai_category,
    ai_priority,
    sentiment,
    summary,
    recommended_action,
    reason,
    model_used,
    prompt_version,
    processed_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, now()
)
ON CONFLICT (ticket_id) DO UPDATE SET
    ai_category = EXCLUDED.ai_category,
    ai_priority = EXCLUDED.ai_priority,
    sentiment = EXCLUDED.sentiment,
    summary = EXCLUDED.summary,
    recommended_action = EXCLUDED.recommended_action,
    reason = EXCLUDED.reason,
    model_used = EXCLUDED.model_used,
    prompt_version = EXCLUDED.prompt_version,
    processed_at = now()
"""


class TicketAnalysis(BaseModel):
    """Structured output for one ticket. Field names match docs/ai-contract.md."""

    category: Literal[
        "Authentication",
        "Account",
        "Billing",
        "Technical",
        "Fraud",
        "General Inquiry",
    ]
    priority: Literal["Critical", "High", "Medium", "Low"]
    sentiment: Literal["Frustrated", "Concerned", "Neutral", "Urgent"]
    summary: str = Field(max_length=180)
    recommended_action: Literal[
        "Route to identity support queue.",
        "Route to account support queue.",
        "Route to billing queue.",
        "Route to technical support queue.",
        "Route to fraud review queue.",
        "Route to general support queue.",
    ]
    reason: str = Field(max_length=240)

    def normalized(self) -> "TicketAnalysis":
        """Return a copy whose labels use the contract spelling."""
        return self.model_copy(
            update={
                "category": _canonical(self.category, CATEGORIES),
                "priority": _canonical(self.priority, PRIORITIES),
                "sentiment": _canonical(self.sentiment, SENTIMENTS),
                "recommended_action": _canonical(self.recommended_action, ACTIONS),
            }
        )


def _canonical(value: str, allowed: tuple[str, ...]) -> str:
    folded = value.strip().casefold()
    for item in allowed:
        if item.casefold() == folded:
            return item
    raise ValueError(f"{value!r} is outside the AI contract")


def load_model_settings() -> str:
    """Load .env and return the model name. The key stays in the environment."""
    load_dotenv(ENV_PATH)
    missing = [
        name
        for name in ("OPENAI_API_KEY", "OPENAI_MODEL")
        if not os.getenv(name)
    ]
    if missing:
        raise RuntimeError(
            "Missing "
            + ", ".join(missing)
            + f" in {ENV_PATH}. Put the real key only in .env."
        )
    return os.environ["OPENAI_MODEL"]


def make_client() -> OpenAI:
    """Build a client. OpenAI() reads OPENAI_API_KEY from the environment."""
    load_model_settings()
    return OpenAI()


def ticket_prompt(subject: str, description: str) -> str:
    """Ticket text sent to the model. Name and email are not included."""
    return f"Subject: {subject}\n\nDescription: {description}"


def analyze_ticket(
    client: OpenAI,
    model: str,
    subject: str,
    description: str,
) -> tuple[TicketAnalysis, object]:
    """Call the Responses API and parse the output into TicketAnalysis."""
    delay_seconds = 2
    response = None
    for attempt in range(3):
        try:
            response = client.responses.parse(
                model=model,
                instructions=SYSTEM_PROMPT,
                input=ticket_prompt(subject, description),
                text_format=TicketAnalysis,
            )
            break
        except RateLimitError:
            if attempt == 2:
                raise
            logger.info("Rate limit reached. Waiting %s seconds.", delay_seconds)
            time.sleep(delay_seconds)
            delay_seconds *= 2
    if response is None or response.output_parsed is None:
        raise RuntimeError("The model returned no structured ticket analysis.")
    return response.output_parsed.normalized(), response


def customer_sentence(description: str) -> str:
    """The request after 'Hi Support,'. Later filler text is ignored."""
    marker = "Hi Support,"
    text = description or ""
    if marker in text:
        text = text.split(marker, 1)[1].strip()
    cuts = [text.find(separator) for separator in ".?!" if separator in text]
    if not cuts:
        return text.strip()
    cut = min(cuts)
    return text[: cut + 1].strip()


def load_csv_tickets(path: Path | None = None) -> list[dict[str, str]]:
    """Read the extract. Only the columns the AI flow needs are returned."""
    csv_path = path or default_tickets_csv()
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        tickets = []
        for row in reader:
            tickets.append(
                {
                    "ticket_id": row["Ticket_ID"],
                    "ticket_subject": row["Ticket_Subject"],
                    "ticket_description": row["Ticket_Description"],
                    "issue_category": row["Issue_Category"],
                    "priority_level": row["Priority_Level"],
                }
            )
    return tickets


def select_sample(tickets: list[dict[str, str]], limit: int = 10) -> list[dict[str, str]]:
    """Pick one ticket for each sample sentence, in contract order."""
    chosen = []
    seen = set()
    for sentence in SAMPLE_SENTENCES:
        if len(chosen) >= limit:
            break
        for ticket in tickets:
            if customer_sentence(ticket["ticket_description"]) != sentence:
                continue
            if ticket["ticket_id"] in seen:
                continue
            chosen.append(ticket)
            seen.add(ticket["ticket_id"])
            break
    return chosen


def ensure_prompt_version_column(connection) -> None:
    """Add prompt_version when an older database does not have it yet."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'ai_ticket_enrichment'
              AND column_name = 'prompt_version'
            """
        )
        if cursor.fetchone():
            return
        cursor.execute(
            "ALTER TABLE ai_ticket_enrichment "
            "ADD COLUMN prompt_version VARCHAR(40)"
        )


def save_analysis(
    connection,
    ticket_id: str,
    analysis: TicketAnalysis,
    model: str,
) -> None:
    """Upsert one AI result. support_tickets is not updated."""
    ensure_prompt_version_column(connection)
    with connection.cursor() as cursor:
        cursor.execute(
            UPSERT_SQL,
            (
                ticket_id,
                analysis.category,
                analysis.priority,
                analysis.sentiment,
                analysis.summary,
                analysis.recommended_action,
                analysis.reason,
                model,
                PROMPT_VERSION,
            ),
        )


def analyze_many(tickets: list[dict[str, str]], store: bool) -> int:
    """Classify tickets. Returns the number of structured results printed."""
    model = load_model_settings()
    client = make_client()
    connection = None
    if store:
        from src.db import connect

        connection = connect()
    input_tokens = 0
    output_tokens = 0
    try:
        for ticket in tickets:
            analysis, response = analyze_ticket(
                client,
                model,
                ticket["ticket_subject"],
                ticket["ticket_description"],
            )
            usage = getattr(response, "usage", None)
            if usage is not None:
                input_tokens += usage.input_tokens or 0
                output_tokens += usage.output_tokens or 0
            print(ticket["ticket_id"])
            print(analysis.model_dump_json(indent=2))
            if connection is not None:
                save_analysis(connection, ticket["ticket_id"], analysis, model)
        if connection is not None:
            connection.commit()
    except Exception:
        if connection is not None:
            connection.rollback()
        raise
    finally:
        if connection is not None:
            connection.close()
    print(
        f"prompt_version={PROMPT_VERSION} model={model} "
        f"tickets={len(tickets)} tokens input={input_tokens} output={output_tokens}"
    )
    return len(tickets)


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description="Classify support tickets.")
    parser.add_argument(
        "--store",
        action="store_true",
        help="Write results to ai_ticket_enrichment. Source ticket columns stay as loaded.",
    )
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    try:
        tickets = select_sample(load_csv_tickets(), args.limit)
        if len(tickets) < args.limit:
            raise RuntimeError(
                f"Found {len(tickets)} sample tickets, needed {args.limit}."
            )
        analyze_many(tickets, store=args.store)
    except Exception:
        logger.exception("Ticket analysis failed")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
