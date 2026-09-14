-- Reporting views and KPI queries Power BI (or pandas) can sit on top of.
-- Run after 01_schema.sql and 03_seed.sql:
--   psql -d support_ops -f sql/02_analytics.sql

CREATE OR REPLACE VIEW vw_tickets_with_names AS
SELECT
    t.ticket_id,
    c.customer_name,
    c.customer_email,
    t.ticket_subject,
    t.issue_category,
    t.priority_level,
    t.ticket_channel,
    t.submission_date,
    t.resolution_time_hours,
    a.agent_name AS assigned_agent,
    t.satisfaction_score,
    CASE
        WHEN lower(t.priority_level) IN ('high', 'critical', 'urgent') THEN TRUE
        ELSE FALSE
    END AS is_high_priority
FROM tickets AS t
JOIN customers AS c ON c.customer_id = t.customer_id
LEFT JOIN agents AS a ON a.agent_id = t.agent_id;

CREATE OR REPLACE VIEW vw_ticket_kpis AS
SELECT
    issue_category,
    COUNT(*) AS ticket_count,
    COUNT(*) FILTER (
        WHERE lower(priority_level) IN ('high', 'critical', 'urgent')
    ) AS high_priority_count,
    ROUND(AVG(resolution_time_hours), 2) AS avg_resolution_hours,
    ROUND(
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY resolution_time_hours)::numeric,
        2
    ) AS median_resolution_hours,
    ROUND(AVG(satisfaction_score), 2) AS avg_satisfaction
FROM tickets
GROUP BY issue_category;

-- Example internship-style questions (run these in psql or a SQL client)

-- Q1. Volume and CSAT by category
-- SELECT * FROM vw_ticket_kpis ORDER BY avg_satisfaction;

-- Q2. Which agents handle the most high-priority work?
-- SELECT
--     a.agent_name,
--     COUNT(*) AS tickets,
--     COUNT(*) FILTER (
--         WHERE lower(t.priority_level) IN ('high', 'critical', 'urgent')
--     ) AS high_priority_tickets,
--     ROUND(AVG(t.satisfaction_score), 2) AS avg_satisfaction
-- FROM tickets t
-- JOIN agents a ON a.agent_id = t.agent_id
-- GROUP BY a.agent_name
-- ORDER BY high_priority_tickets DESC;

-- Q3. Tickets still slow despite high priority
-- SELECT ticket_id, issue_category, priority_level, resolution_time_hours
-- FROM vw_tickets_with_names
-- WHERE is_high_priority
--   AND resolution_time_hours > 10
-- ORDER BY resolution_time_hours DESC;

-- Q4. Assumed handle-time SLA (see docs/kpis.md). Not first-response.
-- Critical 24h, High 48h, Medium/Low 72h.
-- SELECT
--     priority_level,
--     COUNT(*) AS tickets,
--     COUNT(*) FILTER (
--         WHERE resolution_time_hours > CASE lower(priority_level)
--             WHEN 'critical' THEN 24
--             WHEN 'high' THEN 48
--             ELSE 72
--         END
--     ) AS sla_breaches,
--     ROUND(
--         100.0 * COUNT(*) FILTER (
--             WHERE resolution_time_hours > CASE lower(priority_level)
--                 WHEN 'critical' THEN 24
--                 WHEN 'high' THEN 48
--                 ELSE 72
--             END
--         ) / COUNT(*),
--         1
--     ) AS breach_pct
-- FROM tickets
-- GROUP BY priority_level;
