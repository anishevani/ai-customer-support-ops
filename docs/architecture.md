# Architecture

## V1 (in scope now)

CSV is the source. Python validates and computes KPIs. PostgreSQL is the system of record for reporting. Power BI reads views, not the raw file.

```text
Customer support CSV
        │
        ▼
Python ETL / KPI layer
src/analyze.py
validate · transform · pytest
        │
        ▼
PostgreSQL
customers · agents · tickets
vw_ticket_kpis · vw_tickets_with_names
        │
        ▼
Power BI (or Tableau)
one management page
```

| Piece | Where it lives | Status |
| --- | --- | --- |
| Extract | `data/raw/` (full file local; sample committed) | Done |
| KPI rules | `src/config.py`, `src/pandas_analysis.py` | Done |
| Tests | `tests/` | Done |
| Schema + views | `sql/01_schema.sql`, `sql/02_analytics.sql` | Draft (not yet loaded with the 20k file) |
| Load job | Python → Postgres | Next |
| Dashboard | `dashboard/` | Not started |

## Later (not V1)

```text
PostgreSQL tickets
        │
        ▼
AI service (LLM API)
classify · summary · urgency
        │
        ▼
Labels stored on the ticket row
        │
        ├── back to Power BI
        └── optional workflow engine (n8n)
                 │
                 ▼
            Human approval
```

AI and n8n depend on trusted warehouse KPIs. They are FR-08–12, not FR-01–07.

## Design rules

- One definition of high priority and of handle time, shared by Python and SQL.
- Secrets stay in `.env`, never in Git.
- The dashboard does not re-implement KPI math in DAX if the view already has it.
- The 20,000-row CSV never goes on GitHub.
