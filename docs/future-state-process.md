# Future-state process

Two hops. Do not skip to n8n before the warehouse and dashboard exist.

## Hop A — V1 (reporting)

Same agent workflow as today. New path is **data**, not automation.

```text
Customer ticket (CSV extract)
      ↓
Python validate / KPI job  (src/analyze.py)
      ↓
PostgreSQL  (customers, agents, tickets, views)
      ↓
Power BI on vw_ticket_kpis
      ↓
VP / Support Manager decisions
      (Billing process, General Inquiry deflection, staffing)
```

Success for Hop A: SQL CSAT by category matches Python (Billing ~2.98). One dashboard page, not a new queue.

## Hop B — later (AI assist, still human-owned)

After Hop A numbers are trusted, use ticket **text** to explain Billing CSAT.

```text
Ticket description
      ↓
LLM: Billing sub-reason (refund / double charge / plan change)
      + short summary, optional urgency hint
      ↓
Write labels back to PostgreSQL
      ↓
Dashboard slices CSAT by sub-reason
      ↓
Agent still sets official category and talks to the customer
```

## Hop C — only after B (workflow)

```text
High-impact suggestion (e.g. escalate Fraud)
      ↓
n8n / workflow engine
      ↓
Human approval
      ↓
Existing support tool
```

Hop C is out of V1. There is no live ticketing system to write back to.

## What does not change

Agents are not replaced. Refunds are not auto-issued. Official priority in V1 remains the field already on the ticket; the LLM may *suggest* urgency later, with a reason (NFR-02).
