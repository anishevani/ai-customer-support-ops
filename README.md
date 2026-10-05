# Customer Support Operations Analytics

Python + pandas + PostgreSQL analytics on **20,000 customer support tickets**. The goal is a leadership-ready view of volume, priority, resolution time, and CSAT — with metric definitions that stay consistent from CSV to SQL to a future Power BI dashboard.

This is an MIS internship portfolio project. The CSV analysis and the PostgreSQL load are runnable today. Power BI and an LLM enrichment step are the designed next layer, not fake features.

## Highlights

- **20,000 tickets**, 12 fields, 25 months of submissions
- **0 missing values**, **0 duplicate** rows
- High + Critical = **23.6%** of volume
- Mean handle time **39.2 hours** vs median **27 hours** (long-tail delays, not a typical ticket)
- **Billing CSAT 2.98 / 5** vs ~**4.04** for Technical and Account — agents and channels do not explain the gap

Project docs: [data profile](docs/data-profile.md) · [data model](docs/data-model.md) · [business problem](docs/business-problem.md) · [KPIs](docs/kpis.md) · [architecture](docs/architecture.md) · [backlog](docs/backlog.md)

## Architecture

```text
data/raw/*.csv
        │
        ▼
   Pandas  (src/etl.py)
        │
        ▼
   stg_support_tickets          raw text landing
        │
        ▼
   validation
        │
        ├── support_tickets      accepted rows
        └── data/processed/rejected_rows.csv

src/validate_pipeline.py        source = loaded + rejected
src/analyze.py                  CSV KPIs (same metric rules)
```

The loader connects to the database named by `DB_NAME` in `.env`. For this project that database is `mis_support`. Tables:

| Table | Role |
| --- | --- |
| `stg_support_tickets` | Every extracted row, stored as text |
| `support_tickets` | Accepted rows after validation |
| `ai_ticket_enrichment` | Later AI labels. The loader does not fill it |
| `workflow_events` | Later approval log. The loader does not fill it |

`sql/01_schema.sql`, `sql/03_seed.sql`, and `sql/02_analytics.sql` build the reporting model (`customers`, `agents`, `tickets`, and the KPI views) in a database such as `support_ops`.

## Repository layout

| Path | Role |
| --- | --- |
| `src/etl.py` | CSV to staging to `support_tickets` |
| `src/validate_pipeline.py` | Reconciliation report |
| `src/db.py` | PostgreSQL connection from `.env` |
| `src/logger.py` | Shared log setup |
| `src/analyze.py` | CSV profile and KPI report |
| `tests/` | pytest for KPI rules and ETL rejection rules |
| `sql/03_schema.sql` | Staging, clean tickets, AI, and workflow tables |
| `sql/01_schema.sql` | Earlier normalized reporting schema |
| `data/raw/` | Full extract locally; `sample_tickets.csv` is committed |
| `data/processed/` | `rejected_rows.csv` (gitignored) |
| `docs/` | Business problem, KPIs, data model, process, architecture |
| `automation/` | Shell entry point for the analysis job |
| `dashboard/` | Placeholder for the Power BI file |

## Setup

Python 3.9+ recommended. From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the project root. `src/db.py` reads these names. Do not commit `.env`.

```text
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mis_support
DB_USER=mis_user
DB_PASSWORD=your_password
```

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

## Load into PostgreSQL

`src/etl.py` creates the four tables from `sql/03_schema.sql` when they are missing, then reloads staging and `support_tickets` from the CSV.

```bash
python3 src/db.py                  # confirm the .env connection
python3 src/etl.py                 # CSV -> staging -> support_tickets
python3 src/validate_pipeline.py   # print the reconciliation report
pytest
```

The load prints:

```text
Rows input:
Rows staging:
Rows accepted:
Rows rejected:
```

`src/validate_pipeline.py` checks that source rows equal loaded rows plus rejected rows. It also checks duplicate ticket ids, null required columns, category counts, priority counts, and the minimum and maximum submission dates. The command exits with an error when a check fails.

Rows are rejected for a missing or duplicate ticket id, an unknown priority, a missing required field, an invalid submission date, or a negative resolution time. A blank category is stored as `Unknown`. A satisfaction score outside 1–5 is cleared, and the ticket is still loaded.

Rejected rows, with a `rejection_reason` column, are written to `data/processed/rejected_rows.csv`. That file is gitignored.

## Earlier reporting schema

These commands build `customers`, `agents`, `tickets`, and the KPI views:

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
- **Average resolution time** skips blank, negative, and non-numeric cells. If nothing is usable, the report prints `n/a` instead of `0.0`. The loader rejects a negative resolution time instead of storing it.
- **Blank categories** are counted as `Unknown`.
- **value_counts** in the pandas report keep missing labels so row counts can be reconciled.

## What the 20k-ticket file showed

| Question | Result |
| --- | --- |
| Are we slow? | Typical ticket ~27h; average 39h because of a long tail |
| Where is CSAT weak? | Billing (2.98), not agent or channel mix |
| Does priority work? | Critical ~12h, Fraud ~16h; General Inquiry ~43h |

## GitHub notes

The full 20,000-row CSV stays out of Git (see `.gitignore`) so clones stay small. `data/raw/sample_tickets.csv` is enough to run every script. Keep customer extracts, `.env`, and `data/processed/rejected_rows.csv` off GitHub.
