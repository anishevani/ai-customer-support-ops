# Requirements

IDs stay stable. **V1** is ingest + trusted KPIs + a dashboard on SQL. AI and workflow are later, even though they appear in the architecture sketch.

## Functional requirements — V1 (now)

| ID | Requirement |
| --- | --- |
| FR-01 | The system shall ingest customer-support ticket data from CSV. |
| FR-02 | The system shall calculate ticket volume by category. |
| FR-03 | The system shall calculate average and median handle time in hours. |
| FR-04 | The system shall identify high-priority tickets (High, Critical, or Urgent). |
| FR-05 | The system shall calculate CSAT overall and by category. |
| FR-06 | The system shall expose the same KPIs from PostgreSQL views that Python reports. |
| FR-07 | The system shall provide a management dashboard (Power BI) on those views. |

## Functional requirements — later (not V1)

| ID | Requirement |
| --- | --- |
| FR-08 | The system shall use an LLM to summarize ticket descriptions. |
| FR-09 | The system shall use an LLM to recommend or refine ticket category (starting with Billing sub-reasons). |
| FR-10 | The system shall use an LLM to estimate urgency from ticket text. |
| FR-11 | The system shall support escalation workflows (n8n or similar). |
| FR-12 | High-impact automated actions shall support human approval. |

## Nonfunctional requirements

| ID | Area | Requirement |
| --- | --- | --- |
| NFR-01 | Security | API credentials and database passwords shall not be stored in source control (`.env` is gitignored). |
| NFR-02 | Explainability | AI-generated recommendations shall include a short reason (applies when FR-08–10 ship). |
| NFR-03 | Auditability | Automated escalation decisions shall be logged (applies when FR-11–12 ship). |
| NFR-04 | Maintainability | ETL, analytics, and AI code shall stay in separate modules. |
| NFR-05 | Data quality | Rows shall be validated (types, allowed priorities, non-negative hours) before they load into PostgreSQL. |
| NFR-06 | Reproducibility | KPI rules shall live in code and SQL, not only in a slide or notebook. |

## Out of scope

- Real CloudDesk / customer deployment
- 24×7 production operations
- First-response SLA (no first-response timestamp in the extract)
- Automatic customer refunds
- Replacing support agents
- Fine-tuning a proprietary model
- n8n or human-approval workflows before the warehouse KPIs match Python
