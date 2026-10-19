-- Star schema for Power BI, built as views on support_tickets.
-- Run after the ETL load:
--   psql -d mis_support -f sql/20_powerbi_model.sql
--
--               dim_date
--                   |
-- dim_category — fact_tickets — dim_channel
--                   |
--              dim_priority
--
-- One row in fact_tickets is one ticket. Attributes live on the dimensions.
-- Views follow support_tickets, so the next ETL reload shows up on refresh.
--
-- Illustrative SLA hours on dim_priority are the project assumptions in
-- docs/kpis.md (Critical 24, High/Urgent 48, Medium/Low 72). They are not
-- a policy from the extract.

DROP VIEW IF EXISTS fact_tickets;
DROP VIEW IF EXISTS dim_date;
DROP VIEW IF EXISTS dim_category;
DROP VIEW IF EXISTS dim_priority;
DROP VIEW IF EXISTS dim_channel;

CREATE VIEW dim_date AS
WITH bounds AS (
    SELECT
        MIN(submission_date) AS first_date,
        MAX(submission_date) AS last_date
    FROM support_tickets
)
SELECT
    TO_CHAR(day_date::date, 'YYYYMMDD')::integer AS date_key,
    day_date::date AS full_date,
    EXTRACT(YEAR FROM day_date)::integer AS calendar_year,
    EXTRACT(QUARTER FROM day_date)::integer AS calendar_quarter,
    EXTRACT(MONTH FROM day_date)::integer AS month_number,
    TO_CHAR(day_date, 'FMMonth') AS month_name,
    DATE_TRUNC('month', day_date)::date AS month_start,
    TO_CHAR(day_date, 'YYYY-MM') AS year_month,
    EXTRACT(DAY FROM day_date)::integer AS day_of_month
FROM bounds
CROSS JOIN LATERAL generate_series(
    bounds.first_date,
    bounds.last_date,
    INTERVAL '1 day'
) AS day_date;

CREATE VIEW dim_category AS
SELECT
    DENSE_RANK() OVER (ORDER BY issue_category)::integer AS category_key,
    issue_category AS category_name
FROM (
    SELECT DISTINCT issue_category
    FROM support_tickets
) AS categories;

CREATE VIEW dim_priority AS
SELECT
    CASE lower(priority_level)
        WHEN 'critical' THEN 1
        WHEN 'urgent' THEN 2
        WHEN 'high' THEN 3
        WHEN 'medium' THEN 4
        WHEN 'low' THEN 5
        ELSE 9
    END AS priority_key,
    CASE lower(priority_level)
        WHEN 'critical' THEN 'Critical'
        WHEN 'urgent' THEN 'Urgent'
        WHEN 'high' THEN 'High'
        WHEN 'medium' THEN 'Medium'
        WHEN 'low' THEN 'Low'
        ELSE priority_level
    END AS priority_name,
    CASE
        WHEN lower(priority_level) IN ('high', 'critical', 'urgent') THEN 'High priority'
        ELSE 'Standard priority'
    END AS priority_band,
    CASE lower(priority_level)
        WHEN 'critical' THEN 24
        WHEN 'high' THEN 48
        WHEN 'urgent' THEN 48
        ELSE 72
    END AS illustrative_sla_hours
FROM support_tickets
GROUP BY priority_level;

CREATE VIEW dim_channel AS
SELECT
    DENSE_RANK() OVER (ORDER BY ticket_channel)::integer AS channel_key,
    ticket_channel AS channel_name
FROM (
    SELECT DISTINCT ticket_channel
    FROM support_tickets
) AS channels;

CREATE VIEW fact_tickets AS
SELECT
    tickets.ticket_id,
    dates.date_key,
    categories.category_key,
    priorities.priority_key,
    channels.channel_key,
    tickets.resolution_time_hours,
    tickets.satisfaction_score,
    CASE
        WHEN priorities.priority_band = 'High priority' THEN 1
        ELSE 0
    END AS is_high_priority,
    CASE
        WHEN tickets.resolution_time_hours IS NULL THEN NULL
        WHEN tickets.resolution_time_hours > priorities.illustrative_sla_hours THEN 1
        ELSE 0
    END AS sla_breach
FROM support_tickets AS tickets
JOIN dim_date AS dates
    ON dates.full_date = tickets.submission_date
JOIN dim_category AS categories
    ON categories.category_name = tickets.issue_category
JOIN dim_priority AS priorities
    ON lower(priorities.priority_name) = lower(tickets.priority_level)
JOIN dim_channel AS channels
    ON channels.channel_name = tickets.ticket_channel;
