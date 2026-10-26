# AI evaluation results

Prompt version `ticket-analysis-v1`. Model `gpt-4.1-mini`.
Ground truth is `evaluation/eval_tickets.csv`. The scorer compares category, priority, and sentiment with exact text match.
Exact-match rates use valid outputs only. Invalid outputs are counted on their own.

Token use for this run: input 20225, output 1981. Dollar cost depends on the price for this model. This file does not convert tokens to dollars.

| Check | Result |
| --- | --- |
| Tickets | 30 |
| Category exact match | 86.7% (26/30) |
| Priority exact match | 93.3% (28/30) |
| Sentiment exact match | 90.0% (27/30) |
| Invalid outputs | 0 |

A ticket can carry more than one error label. Sentiment misses stay in the table above. They are listed below when category and priority already match.

| Error category | Tickets |
| --- | --- |
| Ambiguous ticket | 1 |
| Bad prompt | 0 |
| Wrong classification | 3 |
| Unsupported recommendation | 0 |
| Over-escalation | 1 |
| Under-escalation | 1 |
| Invalid output | 0 |

## Misses

| Ticket | Expected | Model | Error labels |
| --- | --- | --- | --- |
| TKT-100002 | Account / Low / Neutral | General Inquiry / Low / Neutral | Ambiguous ticket |
| TKT-100017 | Account / Low / Frustrated | Technical / Low / Frustrated | Wrong classification |
| TKT-100018 | Billing / Medium / Neutral | Billing / Low / Neutral | Under-escalation |
| TKT-100057 | Fraud / Critical / Concerned | Fraud / Critical / Urgent | Sentiment mismatch |
| TKT-100081 | Fraud / High / Concerned | Authentication / High / Concerned | Wrong classification |
| TKT-100135 | Fraud / Critical / Concerned | Fraud / Critical / Urgent | Sentiment mismatch |
| TKT-100151 | Fraud / High / Concerned | Authentication / Critical / Urgent | Wrong classification, Over-escalation |
