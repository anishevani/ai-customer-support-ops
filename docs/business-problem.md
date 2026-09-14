# Business problem

## Company

**CloudDesk** is a fictional B2B SaaS company with about 50,000 customers. Customers contact support by email, chat, and web form. Support is Tier 1 + Tier 2. Ticket volume and cost are growing, and leadership hears more SLA complaints.

Management says:

> Ticket volume is growing, customers are complaining about response times, and support leadership has limited visibility into what's causing operational problems.

## What this dataset can and cannot prove

The extract has `Submission_Date`, `Resolution_Time_Hours`, and `Satisfaction_Score`. It does **not** have a first-response timestamp.

| Leadership complaint | What we can measure in V1 |
| --- | --- |
| “Response times are bad” | **Handle time** (open to close), plus mean vs median so a long tail is visible |
| “We cannot see what is wrong” | Volume, priority mix, CSAT, and handle time by category / channel / agent |
| Speed-to-first-reply SLA | **Out of scope** until a first-response field exists |

V1 answers: where volume sits, whether the queue is slow typically or only in a tail, which issue types hurt CSAT, and whether High/Critical actually close faster.

## Stakeholders

Four users for V1. Each has one care, one decision, and one metric.

### VP Customer Operations

- **Cares about:** Overall operating performance and where to put money (staff vs process vs self-service).
- **Decision:** Where should support investment go this quarter?
- **Needs:** Trend-ready KPIs: volume, high/critical share, median handle time, CSAT by category — not a spreadsheet of 20,000 rows.

### Support Manager

- **Cares about:** Queue health and which issue types are actually failing customers.
- **Decision:** Change Billing macros / training, or leave agent coaching as-is?
- **Needs:** CSAT and handle time by category. This extract shows Billing CSAT at 2.98 / 5 vs ~4.04 for Technical and Account, with even agent load — so the first decision is process, not “who is the bad agent.”

### Product Manager

- **Cares about:** Which product or billing experiences generate repeat contacts.
- **Decision:** What to put on the roadmap (Billing clarity, Fraud tooling, vs a General Inquiry help center).
- **Needs:** Volume and handle time by `Issue_Category`. General Inquiry sitting ~43 hours is a deflection candidate; Fraud is already treated as urgent.

### Customers

- **Cares about:** Fast, correct resolution and a fair outcome (especially Billing).
- **Decision:** Stay, churn, or escalate publicly.
- **Needs:** They never see this dashboard. Their signal in the data is `Satisfaction_Score` and how long the ticket stayed open.

Customer Success and IT/Data are consumers later (handoffs, warehouse ownership). They are not V1 dashboard users.

## Problem statement

CloudDesk leadership cannot see whether slow support is a typical ticket, a long tail, a category problem, or an agent problem. Without shared KPI definitions, every team brings a different spreadsheet.

This project defines those KPIs in Python and PostgreSQL first, then puts them on a dashboard. AI tagging and workflow automation come after the structured metrics are trusted.
