# Backlog

Status is based on what is in the repo, not on the original assignment checklist. Testing and docs started in Phase 1; they are not a final “Phase 6” after AI.

## Done

- [x] Environment (venv, `requirements.txt`, `.gitignore`)
- [x] Python / pandas KPI reports (`src/fundamentals.py`, `src/pandas_analysis.py`, `src/analyze.py`)
- [x] Dataset profile (`docs/data-profile.md`) on 20,000 tickets
- [x] pytest for priority rules, averages, and messy hours
- [x] Draft PostgreSQL schema, seed, and KPI views (`sql/`)
- [x] Business problem, KPIs, requirements, current/future process, architecture

## V1 remaining (do in this order)

- [ ] Load `sample_tickets.csv` (then the local 20k file) into PostgreSQL
- [ ] Validate rows before insert (types, allowed priorities, hours ≥ 0)
- [ ] Confirm SQL KPIs match Python (volume 20,000, Billing CSAT ~2.98, high-priority 4,714)
- [ ] Optional: handle-time SLA breach % using the targets in `docs/kpis.md`
- [ ] Power BI page on `vw_ticket_kpis` + screenshot in `dashboard/`
- [ ] Short demo script (run `python -m src.analyze`, then one SQL view)

## Later (after V1 dashboard)

- [ ] LLM Billing sub-reasons from ticket text, stored in Postgres
- [ ] Summaries and urgency hints with a written reason
- [ ] Simple quality check on LLM labels vs existing `Issue_Category`
- [ ] n8n + human approval (only if there is something to write back to)

## Explicitly not started, on purpose

- Live ticketing integration
- First-response SLA
- Agent-facing UI
- Fine-tuned models
