-- Layered support-ops schema from docs/data-model.md.
-- Separate from the V1 normalized schema in sql/01_schema.sql.
-- Run from the project root:
--   psql -d support_ops -f sql/03_schema.sql
--
-- stg_support_tickets    raw CSV landing (text, no foreign keys)
-- support_tickets        validated business rows
-- ai_ticket_enrichment   one AI result per ticket
-- workflow_events        many workflow rows per ticket

DROP TABLE IF EXISTS workflow_events;
DROP TABLE IF EXISTS ai_ticket_enrichment;
DROP TABLE IF EXISTS support_tickets;
DROP TABLE IF EXISTS stg_support_tickets;

-- Raw-ish import of customer_support_tickets.csv.
-- Types stay text so a bad row can land before validation.
-- Surrogate key so a duplicate or blank Ticket_ID does not fail the load.
CREATE TABLE stg_support_tickets (
    stg_ticket_id           BIGSERIAL PRIMARY KEY,
    ticket_id               TEXT,
    customer_name           TEXT,
    customer_email          TEXT,
    ticket_subject          TEXT,
    ticket_description      TEXT,
    issue_category          TEXT,
    priority_level          TEXT,
    ticket_channel          TEXT,
    submission_date         TEXT,
    resolution_time_hours   TEXT,
    assigned_agent          TEXT,
    satisfaction_score      TEXT,
    loaded_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_stg_support_tickets_ticket_id
    ON stg_support_tickets (ticket_id);

-- Clean, validated ticket grain. One row per Ticket_ID.
CREATE TABLE support_tickets (
    ticket_id               VARCHAR(20) PRIMARY KEY,
    customer_name           VARCHAR(120) NOT NULL,
    customer_email          VARCHAR(255) NOT NULL,
    ticket_subject          TEXT,
    ticket_description      TEXT,
    issue_category          VARCHAR(50) NOT NULL,
    priority_level          VARCHAR(20) NOT NULL,
    ticket_channel          VARCHAR(30) NOT NULL,
    submission_date         DATE NOT NULL,
    resolution_time_hours   NUMERIC(6, 2) CHECK (
        resolution_time_hours IS NULL
        OR resolution_time_hours >= 0
    ),
    assigned_agent          VARCHAR(120),
    satisfaction_score      SMALLINT CHECK (
        satisfaction_score IS NULL
        OR satisfaction_score BETWEEN 1 AND 5
    )
);

CREATE INDEX idx_support_tickets_category
    ON support_tickets (issue_category);
CREATE INDEX idx_support_tickets_priority
    ON support_tickets (priority_level);
CREATE INDEX idx_support_tickets_submitted
    ON support_tickets (submission_date);

-- One current AI pass per ticket. Reprocessing updates this row.
CREATE TABLE ai_ticket_enrichment (
    ticket_id               VARCHAR(20) PRIMARY KEY
                            REFERENCES support_tickets (ticket_id),
    ai_category             VARCHAR(80),
    ai_priority             VARCHAR(20),
    sentiment               VARCHAR(30),
    summary                 TEXT,
    recommended_action     TEXT,
    reason                  TEXT,
    model_used              VARCHAR(120),
    processed_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Audit log for later workflow / human approval (many events per ticket).
CREATE TABLE workflow_events (
    workflow_event_id       BIGSERIAL PRIMARY KEY,
    ticket_id               VARCHAR(20) NOT NULL
                            REFERENCES support_tickets (ticket_id),
    action                  VARCHAR(80) NOT NULL,
    approval_status         VARCHAR(30) NOT NULL,
    event_timestamp         TIMESTAMPTZ NOT NULL DEFAULT now(),
    result                  TEXT
);

CREATE INDEX idx_workflow_events_ticket
    ON workflow_events (ticket_id);
