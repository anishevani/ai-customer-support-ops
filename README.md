# Customer Support Operations Analytics

Python + pandas + PostgreSQL analytics on **20,000 customer support tickets**. The goal is a leadership-ready view of volume, priority, resolution time, and CSAT — with metric definitions that stay consistent from CSV to SQL to a future Power BI dashboard.

This is an MIS internship portfolio project. The Python and SQL layers are runnable today. Power BI and an LLM enrichment step are the designed next layer, not fake features.

## Highlights

- **20,000 tickets**, 12 fields, 25 months of submissions
- **0 missing values**, **0 duplicate** rows
- High + Critical = **23.6%** of volume
- Mean handle time **39.2 hours** vs median **27 hours** (long-tail delays, not a typical ticket)
- **Billing CSAT 2.98 / 5** vs ~**4.04** for Technical and Account — agents and channels do not explain the gap

Project docs: [data profile](docs/data-profile.md) · [business problem](docs/business-problem.md) · [KPIs](docs/kpis.md) · [architecture](docs/architecture.md) · [backlog](docs/backlog.md)

## Architecture

```text
data/raw/*.csv
        │
        ▼
   src/analyze.py          pytest  (tests/)
   CSV + pandas KPIs
        │
        ▼
   PostgreSQL              sql/01_schema.sql
   customers · agents      sql/02_analytics.sql
   tickets + views         sql/03_seed.sql
        │
        ├── Power BI  (next)
        └── LLM text tags (next)
```

## Repository layout

| Path | Role |
| --- | --- |
| `src/` | Runnable Python: load, profile, KPI report |
| `tests/` | pytest coverage for the business rules |
| `sql/` | PostgreSQL schema, KPI views, demo seed |
| `data/raw/` | Full extract locally; `sample_tickets.csv` is committed |
| `docs/` | Business problem, KPIs, process, architecture, backlog |
| `automation/` | Shell entry point for the analysis job |
| `dashboard/` | Placeholder for the Power BI file |
| `notebooks/` | Placeholder for exploration notebooks |

## Setup

Python 3.9+ recommended. From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` if you later connect Python to PostgreSQL. Do not commit `.env`.

## Run the analysis

The scripts look for `data/raw/customer_support_tickets.csv` first, then fall back to the committed sample file.

```bash
python -m src.analyze              # profile + CSV metrics + pandas report
python -m src.fundamentals
python -m src.pandas_analysis
python -m src.profile_data
pytest
```

Or: `bash automation/run_analysis.sh`

## PostgreSQL (optional)

```bash
createdb support_ops
psql -d support_ops -f sql/01_schema.sql
psql -d support_ops -f sql/03_seed.sql
psql -d support_ops -f sql/02_analytics.sql
psql -d support_ops -c "SELECT * FROM vw_ticket_kpis;"
```

`vw_ticket_kpis` is the grain a Power BI report should use: tickets, high-priority count, average and median handle time, and CSAT by category.

## Metric rules (Python and SQL share these)

- **High priority** means High, Critical, or Urgent, ignoring letter case and extra spaces. This extract uses High and Critical, not Urgent.
- **Average resolution time** skips blank, negative, and non-numeric cells. If nothing is usable, the report prints `n/a` instead of `0.0`.
- **Blank categories** are counted as `Unknown`.
- **value_counts** in the pandas report keep missing labels so row counts can be reconciled.

## What the 20k-ticket file showed

| Question | Result |
| --- | --- |
| Are we slow? | Typical ticket ~27h; average 39h because of a long tail |
| Where is CSAT weak? | Billing (2.98), not agent or channel mix |
| Does priority work? | Critical ~12h, Fraud ~16h; General Inquiry ~43h |

## GitHub notes

The full 20,000-row CSV stays out of Git (see `.gitignore`) so clones stay small. `data/raw/sample_tickets.csv` is enough to run every script. Keep customer extracts and `.env` off GitHub.
