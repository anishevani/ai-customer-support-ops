# Customer Support Operations Analytics

Python + pandas + PostgreSQL + Power BI on **20,000 customer support tickets**. Metric definitions stay the same from the CSV, through validation, into SQL, and into the Power BI model.

This is an MIS internship portfolio project. The CSV analysis, the PostgreSQL load, the SQL analysis, and the Power BI import are in the repo. The AI enrichment and workflow tables are created and left empty.

## Highlights

- **20,000 tickets**, 12 fields, 25 months of submissions
- **0 missing values**, **0 duplicate** rows
- High + Critical = **23.6%** of volume
- Mean handle time **39.2 hours** vs median **27 hours** (long-tail delays, not a typical ticket)
- **Billing CSAT 2.98 / 5** vs ~**4.04** for Technical and Account. Similar handle times still show the gap
- **Illustrative SLA breach 20.5%** (4,102 of 20,000), using the project assumptions in [KPIs](docs/kpis.md): Critical 24 hours, High 48, Medium and Low 72. That is not a company policy stored in the extract

Project docs: [data profile](docs/data-profile.md) · [data model](docs/data-model.md) · [business problem](docs/business-problem.md) · [KPIs](docs/kpis.md) · [architecture](docs/architecture.md) · [analytics findings](docs/analytics-findings.md) · [Power BI model](docs/powerbi-model.md) · [dashboard guide](docs/dashboard-guide.md) · [AI contract](docs/ai-contract.md) · [AI evaluation](docs/ai-evaluation-method.md) · [backlog](docs/backlog.md)

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
        │
        ▼
   fact_tickets + dimensions     sql/20_powerbi_model.sql
        │
        ▼
   Power BI                      dashboard/customer_support_dashboard.pbix
```

The loader connects to the database named by `DB_NAME` in `.env`. For this project that database is `mis_support`. Tables:

| Table | Role |
| --- | --- |
| `stg_support_tickets` | Every extracted row, stored as text |
| `support_tickets` | Accepted rows after validation |
| `ai_ticket_enrichment` | AI labels. `src/ai_service.py --store` fills it. Source category and priority stay on `support_tickets` |
| `workflow_events` | Later approval log. The loader does not fill it |

`sql/01_schema.sql`, `sql/03_seed.sql`, and `sql/02_analytics.sql` build the reporting model (`customers`, `agents`, `tickets`, and the KPI views) in a database such as `support_ops`.

## Repository layout

| Path | Role |
| --- | --- |
| `src/etl.py` | CSV to staging to `support_tickets` |
| `src/ai_test.py` | One Responses API call |
| `src/ai_service.py` | Structured ticket classification and enrichment upsert |
| `src/evaluate_ai.py` | Scores the model against `evaluation/eval_tickets.csv` |
| `src/validate_pipeline.py` | Reconciliation report |
| `src/db.py` | PostgreSQL connection from `.env` |
| `src/logger.py` | Shared log setup |
| `src/analyze.py` | CSV profile and KPI report |
| `tests/` | pytest for KPI rules and ETL rejection rules |
| `sql/03_schema.sql` | Staging, clean tickets, AI, and workflow tables |
| `sql/10_business_analysis.sql` | Aggregation, CTE, window, and illustrative SLA queries |
| `sql/20_powerbi_model.sql` | `fact_tickets`, `dim_date`, `dim_category`, `dim_priority`, `dim_channel` |
| `sql/01_schema.sql` | Earlier normalized reporting schema |
| `data/raw/` | Full extract locally; `sample_tickets.csv` is committed |
| `data/processed/` | `rejected_rows.csv` (gitignored) |
| `docs/analytics-findings.md` | Five findings and the presentation script |
| `docs/powerbi-model.md` | Star schema, relationships, and DAX measures |
| `docs/` | Business problem, KPIs, data model, process, architecture |
| `automation/` | Shell entry point for the analysis job |
| `dashboard/customer_support_dashboard.pbix` | Power BI import of the five views |

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
OPENAI_API_KEY=
OPENAI_MODEL=
```

The real API key belongs only in `.env`. `.env.example` keeps the key blank.

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

On the full extract the load recorded 20,000 input, 20,000 staging, 20,000 accepted, and 0 rejected.

## Classify tickets

The contract is [docs/ai-contract.md](docs/ai-contract.md). The model name and key come from `.env`.

```bash
python3 src/ai_test.py                 # one Responses API call
python3 -m src.ai_service              # structured output for 10 tickets
python3 -m src.ai_service --store      # write those 10 rows to ai_ticket_enrichment
python3 -m src.evaluate_ai             # score the 30-ticket sheet
```

`--store` updates `ai_ticket_enrichment` only. The evaluation method is [docs/ai-evaluation-method.md](docs/ai-evaluation-method.md).

## SQL analysis

`sql/10_business_analysis.sql` is the business-question set: aggregations, CTEs, window functions, and the illustrative SLA. The write-up is [docs/analytics-findings.md](docs/analytics-findings.md).

```bash
psql -d mis_support -f sql/10_business_analysis.sql
```

## Power BI model

`sql/20_powerbi_model.sql` builds views, so a refresh follows the latest `support_tickets` load. Power BI imports these five views only:

| View | Grain |
| --- | --- |
| `fact_tickets` | One ticket |
| `dim_date` | One calendar day from the first submission through the last |
| `dim_category` | One issue category |
| `dim_priority` | One priority label, with the illustrative hour target |
| `dim_channel` | One channel |

```bash
psql -d mis_support -f sql/20_powerbi_model.sql
```

The saved report is `dashboard/customer_support_dashboard.pbix`. It was loaded from PostgreSQL in Power BI Desktop. Power Query only selects the five views and keeps the column types. The report measures on `fact_tickets` are Total Tickets, Average Resolution Time, Median Resolution Time, Average Satisfaction, High Priority %, and SLA Breach %. They aggregate columns the views already calculated. Relationship keys are hidden. `dim_date` is the date table. Page-by-page decisions are in [docs/dashboard-guide.md](docs/dashboard-guide.md). Model details are in [docs/powerbi-model.md](docs/powerbi-model.md).

After a fresh load, row counts in the model should be fact 20,000, date 731, category 5, priority 4, and channel 3. Dates run from 2024-01-02 through 2026-01-01.

## Earlier reporting schema

These commands build `customers`, `agents`, `tickets`, and the KPI views:

```bash
createdb support_ops
psql -d support_ops -f sql/01_schema.sql
psql -d support_ops -f sql/03_seed.sql
psql -d support_ops -f sql/02_analytics.sql
psql -d support_ops -c "SELECT * FROM vw_ticket_kpis;"
```

`vw_ticket_kpis` belongs to that earlier `support_ops` model. The Power BI file uses the `mis_support` star schema above, not this view.

## Metric rules (Python and SQL share these)

- **High priority** means High, Critical, or Urgent, ignoring letter case and extra spaces. This extract uses High and Critical, not Urgent.
- **Average resolution time** skips blank, negative, and non-numeric cells. If nothing is usable, the report prints `n/a` instead of `0.0`. The loader rejects a negative resolution time instead of storing it.
- **Blank categories** are counted as `Unknown`.
- **value_counts** in the pandas report keep missing labels so row counts can be reconciled.

## What the 20k-ticket file showed

| Question | Result |
| --- | --- |
| Are we slow? | Typical ticket ~27h; average 39.23h because of a long tail |
| Where is CSAT weak? | Billing 2.98, against about 4.04 for Technical and Account. The gap remains when handle time is similar |
| Does priority track speed? | Critical averages 12.07h and Low averages 45.17h. Critical CSAT is the lowest of the four labels, largely because Fraud is most of Critical volume |
| What does the illustrative SLA say? | 20.5% of tickets are past the project target. Channel rates sit within 0.2 points of each other |

## GitHub notes

The full 20,000-row CSV stays out of Git (see `.gitignore`) so clones stay small. `data/raw/sample_tickets.csv` is enough to run every script. Keep customer extracts, `.env`, and `data/processed/rejected_rows.csv` off GitHub.
