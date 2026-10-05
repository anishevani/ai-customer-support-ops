stg_support_tickets
support_tickets
ai_ticket_enrichment
workflow_events

Why?

stg_support_tickets

Raw-ish imported data.

support_tickets

Clean validated business data.

ai_ticket_enrichment

Later stores:

AI category
AI priority
sentiment
summary
recommended action
reason
model used
processed timestamp

workflow_events

Later stores:

ticket
action
approval status
timestamp
result

PK/FK relationships

Example:

support_tickets
       │
       ├──────── ai_ticket_enrichment
       │
       └──────── workflow_events