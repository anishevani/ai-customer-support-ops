# KPI definitions

Grain is **one row per ticket** unless noted. Python (`src/pandas_analysis.py`) and SQL (`sql/02_analytics.sql`) must use the same rules. Blank / invalid `Resolution_Time_Hours` are skipped, not treated as zero. High priority is **High, Critical, or Urgent**, ignoring letter case (`src/config.py`).

This extract has no first-response timestamp. Every time KPI below is **handle time** (submission to close), not speed-to-first-reply.

| ID | KPI | Formula | Grain | Source |
| --- | --- | --- | --- | --- |
| KPI-01 | Ticket volume | `COUNT(ticket_id)` | Ticket | `Ticket_ID` |
| KPI-02 | Average handle time (hours) | `AVG(resolution_time_hours)` where value is numeric and ≥ 0 | Ticket | `Resolution_Time_Hours` |
| KPI-03 | Median handle time (hours) | `PERCENTILE_CONT(0.5)` / pandas `median()` | Ticket | `Resolution_Time_Hours` |
| KPI-04 | CSAT | `AVG(satisfaction_score)` on a 1–5 scale | Ticket | `Satisfaction_Score` |
| KPI-05 | High/critical share | Tickets with High, Critical, or Urgent ÷ all tickets | Ticket | `Priority_Level` |
| KPI-06 | Volume by category | `COUNT(*)` grouped by category; blank → `Unknown` | Category | `Issue_Category` |
| KPI-07 | Handle time by category | Mean (and median in SQL views) of hours, grouped by category | Category | `Issue_Category`, `Resolution_Time_Hours` |
| KPI-08 | Handle time by channel | Mean hours grouped by channel | Channel | `Ticket_Channel`, `Resolution_Time_Hours` |
| KPI-09 | CSAT by category | Mean score grouped by category | Category | `Issue_Category`, `Satisfaction_Score` |
| KPI-10 | Assumed handle-time SLA breach % | Share of tickets whose hours exceed the target for that priority (below) | Ticket | `Priority_Level`, `Resolution_Time_Hours` |

## Assumed handle-time SLAs (KPI-10)

These are **project assumptions**, not CloudDesk policy. Textbook targets (Critical 4h / High 8h) do not fit this extract: Critical already averages **12.1 hours** and High **24.5 hours**, so those targets would mark almost every ticket as a breach.

| Priority | Handle-time target | Why this bar |
| --- | --- | --- |
| Critical | 24 hours | Above the Critical mean (~12h), still flags the slow tail |
| High | 48 hours | Above the High mean (~25h) |
| Medium | 72 hours | Dataset max is 120h; 72h catches the long tail |
| Low | 72 hours | Same as Medium; Low mean is already ~45h |

V1 can ship **without** KPI-10 on the dashboard. Mean vs median (KPI-02/03) already shows the long tail. Add breach % only after Postgres is loaded and the rate is not ~100%.

## Headline numbers from the 20,000-row extract

| KPI | Result |
| --- | --- |
| Volume | 20,000 |
| Mean / median hours | 39.23 / 27.00 |
| CSAT | 3.72 / 5 |
| High + Critical share | 23.6% (4,714 tickets) |
| Lowest CSAT category | Billing 2.98 |
| Fastest category | Fraud 15.8h (100% High or Critical) |
| Slowest category | General Inquiry 43.2h |
