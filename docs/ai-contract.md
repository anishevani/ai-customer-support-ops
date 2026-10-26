# AI contract

Prompt version: `ticket-analysis-v1`.

The model reads a ticket subject and description. It returns one JSON object. `src/ai_service.py` validates that object with `TicketAnalysis` before anything is stored. The stored row goes to `ai_ticket_enrichment`. `support_tickets.issue_category` and `support_tickets.priority_level` stay as they were loaded.

## Terms

| Term | In this project |
| --- | --- |
| Client | `OpenAI()` in Python. It holds the connection to the API. |
| API key | `OPENAI_API_KEY` in `.env`. The example file leaves it blank. `.env` is gitignored. |
| Request | `client.responses.create()` or `client.responses.parse()`. |
| Model | `OPENAI_MODEL` in `.env`. It must support structured outputs. |
| Input | The subject and description. Customer name and email are not sent. |
| Response | The object returned by the API. Structured calls expose `output_parsed`. |
| Tokens | Input and output pieces the API bills. The scripts print the counts from `response.usage`. |
| Cost | The vendor price for those tokens. This repo records the counts and does not convert them to dollars. |
| Rate limits | How many requests the account can send in a period. A limit response is retried twice, then the ticket is an invalid output. |
| JSON | The response shape below. Structured outputs make the model follow this schema. |

## Expected output

```json
{
  "category": "Authentication",
  "priority": "High",
  "sentiment": "Frustrated",
  "summary": "Customer cannot access account.",
  "recommended_action": "Route to identity support queue.",
  "reason": "Repeated authentication problem."
}
```

`summary` is at most 180 characters. `reason` is at most 240 characters.

## Allowed values

| Field | Allowed values |
| --- | --- |
| category | Authentication, Account, Billing, Technical, Fraud, General Inquiry |
| priority | Critical, High, Medium, Low |
| sentiment | Frustrated, Concerned, Neutral, Urgent |
| recommended_action | Route to identity support queue. Route to account support queue. Route to billing queue. Route to technical support queue. Route to fraud review queue. Route to general support queue. |

The queue follows the category:

| Category | Queue |
| --- | --- |
| Authentication | Route to identity support queue. |
| Account | Route to account support queue. |
| Billing | Route to billing queue. |
| Technical | Route to technical support queue. |
| Fraud | Route to fraud review queue. |
| General Inquiry | Route to general support queue. |

Classification uses the customer sentence in the description. On this extract the subject line is often a different template. When they disagree, the description wins.

Priority:

- Critical: compromised account, stolen card, transactions the customer did not make, or a request to lock the account now.
- High: the customer is blocked, or the charge is wrong right now. Login failure, 2FA lockout, missing password-reset email, failed payment, double charge, refund still missing, crash, API 500, dashboard stuck, data not syncing.
- Medium: bill amount question, cancellation, invoice copy, email change, account deletion.
- Low: how-to and information requests. Hours, location, pricing explanation, demo, discount, roadmap, install steps, profile picture.

Sentiment:

- Urgent: the customer demands immediate action.
- Concerned: a security worry without that demand.
- Frustrated: something is broken, late, or charged incorrectly.
- Neutral: a plain question or request.

## What the AI should not do

- Do not make refunds.
- Do not send customer-facing communications.
- Do not invent account information.
- Do not claim an incident exists without evidence.
- Do not replace the source category or priority. Those columns stay on `support_tickets` so a later comparison is possible.
- Do not promise a resolution time or a compensation amount.

A human still owns the queue, the refund decision, and any message to the customer.
