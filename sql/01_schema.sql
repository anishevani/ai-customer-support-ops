-- Normalized support-ops schema for PostgreSQL.
-- Run from the project root:
--   psql -d support_ops -f sql/01_schema.sql

DROP VIEW IF EXISTS vw_ticket_kpis;
DROP VIEW IF EXISTS vw_tickets_with_names;
DROP TABLE IF EXISTS tickets;
DROP TABLE IF EXISTS agents;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    customer_id     SERIAL PRIMARY KEY,
    customer_name   VARCHAR(120) NOT NULL,
    customer_email  VARCHAR(255) NOT NULL UNIQUE
);

CREATE TABLE agents (
    agent_id    SERIAL PRIMARY KEY,
    agent_name  VARCHAR(120) NOT NULL UNIQUE
);

CREATE TABLE tickets (
    ticket_id               VARCHAR(20) PRIMARY KEY,
    customer_id             INTEGER NOT NULL REFERENCES customers (customer_id),
    agent_id                INTEGER REFERENCES agents (agent_id),
    ticket_subject          TEXT,
    ticket_description      TEXT,
    issue_category          VARCHAR(50) NOT NULL,
    priority_level          VARCHAR(20) NOT NULL,
    ticket_channel          VARCHAR(30) NOT NULL,
    submission_date         DATE NOT NULL,
    resolution_time_hours   NUMERIC(6, 2),
    satisfaction_score      SMALLINT CHECK (
        satisfaction_score IS NULL
        OR satisfaction_score BETWEEN 1 AND 5
    )
);

CREATE INDEX idx_tickets_category ON tickets (issue_category);
CREATE INDEX idx_tickets_priority ON tickets (priority_level);
CREATE INDEX idx_tickets_submitted ON tickets (submission_date);
CREATE INDEX idx_tickets_agent ON tickets (agent_id);
