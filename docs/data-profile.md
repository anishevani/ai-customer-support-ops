# Dataset profile

Source: `data/raw/customer_support_tickets.csv` (20,000 tickets, 12 columns).  
This file is gitignored because it is large. A 60-row sample lives in `data/raw/sample_tickets.csv`.

## Fields

| Column | Type | Notes |
| --- | --- | --- |
| Ticket_ID | text | Unique (`TKT-100000` …) |
| Customer_Name | text | Synthetic names |
| Customer_Email | text | `example.com` / `example.org` addresses |
| Ticket_Subject | text | Short title |
| Ticket_Description | text | Customer message |
| Issue_Category | text | Technical, Billing, Account, General Inquiry, Fraud |
| Priority_Level | text | Low, Medium, High, Critical |
| Ticket_Channel | text | Chat, Email, Web Form |
| Submission_Date | date | 2024-01-02 to 2026-01-01 (25 months) |
| Resolution_Time_Hours | integer | 1–120 hours |
| Assigned_Agent | text | Five agents, even load |
| Satisfaction_Score | integer | 1–5 |

## Quality

- Missing values: **0** in every column
- Duplicate rows: **0**
- Ticket IDs: 20,000 unique values

## Category mix

| Issue_Category | Tickets |
| --- | ---: |
| Technical | 5,918 |
| Billing | 5,036 |
| Account | 4,081 |
| General Inquiry | 3,925 |
| Fraud | 1,040 |

## Priority mix

| Priority_Level | Tickets | Share |
| --- | ---: | ---: |
| Low | 7,716 | 38.6% |
| Medium | 7,570 | 37.9% |
| High | 3,416 | 17.1% |
| Critical | 1,298 | 6.5% |

High + Critical = **4,714 tickets (23.6%)**. This dataset does not use the label `Urgent`.

## Numeric summary

| Metric | Resolution hours | Satisfaction (1–5) |
| --- | ---: | ---: |
| Mean | 39.23 | 3.72 |
| Median | 27.00 | 4.00 |
| Min | 1 | 1 |
| Max | 120 | 5 |

Mean resolution time is much higher than the median, so a minority of slow tickets pull the average up. About **76%** of tickets take more than 10 hours; **31%** take more than 48 hours.

## Findings worth acting on

1. **Billing CSAT is the problem child.** Billing averages **2.98 / 5**. Technical, Account, and General Inquiry sit near **4.04**. That is a process issue, not an even “support quality is low” story.
2. **Fraud is slow to arrive, fast to close.** Every fraud ticket is High or Critical (68.8% Critical). Average handle time is **15.8 hours**, versus **43 hours** for General Inquiry. Priority routing appears to work for fraud; it does not appear to work for unstructured questions.
3. **Critical tickets really are faster.** Critical mean handle time is **12.1 hours**; Low is **45.2 hours**. The queue is using priority.
4. **Agents are interchangeable on volume.** Each of the five agents handles about 4,000 tickets with CSAT ~3.72. Do not start with a “bad agent” hypothesis.
5. **Channels are not the CSAT driver.** Chat, Email, and Web Form all average ~3.7.

## Questions this raises for operations

- Why does Billing score a full point lower than Technical if agents and channels look even?
- Should General Inquiry be deflected to self-service before it sits 43 hours in the queue?
- What SLA should High vs Critical use, given Critical already closes in ~12 hours?

Handle-time SLA in this project is an **assumption** (Critical 24h, High 48h, Medium/Low 72h), not a first-response SLA. See `docs/kpis.md`.

## Next data work

- Load the CSV into the PostgreSQL schema in `sql/01_schema.sql` and rebuild these KPIs as views.
- Confirm SQL matches Python (20,000 rows, Billing CSAT ~2.98, 4,714 high-priority).
- Connect Power BI to `vw_ticket_kpis` instead of the raw CSV.
- Use ticket text with an LLM to tag Billing sub-reasons (refunds, double charge, plan change) once the warehouse is stable.
