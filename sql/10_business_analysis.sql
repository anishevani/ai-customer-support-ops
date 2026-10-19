-- Business analysis on the clean ticket table.
-- Database: the DB_NAME in .env (this project uses mis_support).
-- Grain: one row in support_tickets.
-- Handle time is submission to close. There is no first-response timestamp.
--
-- Run after sql/03_schema.sql and the ETL load:
--   psql -d mis_support -f sql/10_business_analysis.sql
--
-- Sunday Sep 13 questions are comments only. Queries start Monday.


-- =============================================================================
-- Sunday Sep 13 — Business questions (no queries yet)
-- =============================================================================
--
-- Operational
--  1. Which category generates the most tickets?
--  2. Which category has the longest average resolution time?
--  3. Which channel carries the most tickets?
--  4. Is agent workload even, or is one person carrying the queue?
--
-- Customer experience
--  5. Which channels have the lowest satisfaction?
--  6. Are certain categories associated with disproportionately poor CSAT?
--  7. Do slower tickets have lower satisfaction than faster ones?
--  8. Which category and priority combinations sit below the company CSAT?
--
-- Management
--  9. Does higher priority associate with faster resolution?
-- 10. Which categories sit above the company-average resolution time?
-- 11. Do agents differ on CSAT, or only on the mix of work?
-- 12. Where do high volume and poor CSAT overlap, so a manager knows where to look first?
--
-- SLA  (illustrative project assumptions, not a policy from the extract)
-- 13. What is the overall breach rate under those assumptions?
-- 14. Which categories contribute the most tickets to those breaches?
-- 15. Which priority has the highest breach rate?
-- 16. Which channel has the highest breach rate?
--
-- Trend
-- 17. Is monthly ticket volume rising, flat, or falling?
-- 18. Is monthly CSAT rising, flat, or falling?
-- 19. Is monthly average handle time rising, flat, or falling?
-- 20. How does each month's volume compare with the prior month?


-- =============================================================================
-- Monday Sep 14 — Aggregations
-- COUNT, AVG, MIN, MAX, GROUP BY, HAVING, CASE
-- =============================================================================

-- Business question: How big is the extract, and what are the extremes of handle time and date?
-- Why management cares: Sets the baseline before any category comparison. Mean versus min/max shows whether a few slow tickets can distort the average.
SELECT
    COUNT(*) AS tickets,
    MIN(submission_date) AS first_submission,
    MAX(submission_date) AS last_submission,
    MIN(resolution_time_hours) AS fastest_hours,
    MAX(resolution_time_hours) AS slowest_hours,
    ROUND(AVG(resolution_time_hours), 2) AS avg_hours,
    ROUND(AVG(satisfaction_score), 2) AS avg_csat
FROM support_tickets;


-- Business question: Which category generates the most tickets?
-- Why management cares: Staffing and process work should start where the volume actually is.
SELECT
    issue_category,
    COUNT(*) AS tickets,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS volume_pct
FROM support_tickets
GROUP BY issue_category
ORDER BY tickets DESC;


-- Business question: Which category has the longest resolution time, and which is fastest?
-- Why management cares: A long average with a much smaller median means a slow tail, not a typical ticket.
SELECT
    issue_category,
    COUNT(*) AS tickets,
    MIN(resolution_time_hours) AS min_hours,
    MAX(resolution_time_hours) AS max_hours,
    ROUND(AVG(resolution_time_hours), 2) AS avg_hours,
    ROUND(
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY resolution_time_hours)::numeric,
        2
    ) AS median_hours
FROM support_tickets
GROUP BY issue_category
ORDER BY avg_hours DESC;


-- Business question: Which channel carries the most tickets, and which has the lowest satisfaction?
-- Why management cares: If CSAT is flat across channels, the channel is not the lever. If one channel is both large and unhappy, it is.
SELECT
    ticket_channel,
    COUNT(*) AS tickets,
    ROUND(AVG(resolution_time_hours), 2) AS avg_hours,
    MIN(satisfaction_score) AS min_csat,
    MAX(satisfaction_score) AS max_csat,
    ROUND(AVG(satisfaction_score), 2) AS avg_csat
FROM support_tickets
GROUP BY ticket_channel
ORDER BY avg_csat ASC;


-- Business question: Does higher priority associate with faster resolution?
-- Why management cares: If Critical is not faster than Low, the priority label is not changing the queue.
SELECT
    priority_level,
    COUNT(*) AS tickets,
    ROUND(AVG(resolution_time_hours), 2) AS avg_hours,
    MIN(resolution_time_hours) AS min_hours,
    MAX(resolution_time_hours) AS max_hours,
    ROUND(AVG(satisfaction_score), 2) AS avg_csat,
    CASE
        WHEN lower(priority_level) IN ('high', 'critical', 'urgent') THEN 'High priority'
        ELSE 'Standard priority'
    END AS priority_band
FROM support_tickets
GROUP BY priority_level
ORDER BY avg_hours ASC;


-- Business question: Are high-priority tickets, as a group, faster and happier than standard tickets?
-- Why management cares: One comparison a director can remember, using the same High / Critical / Urgent rule as the Python KPIs.
SELECT
    CASE
        WHEN lower(priority_level) IN ('high', 'critical', 'urgent') THEN 'High priority'
        ELSE 'Standard priority'
    END AS priority_band,
    COUNT(*) AS tickets,
    ROUND(AVG(resolution_time_hours), 2) AS avg_hours,
    ROUND(AVG(satisfaction_score), 2) AS avg_csat
FROM support_tickets
GROUP BY priority_band
ORDER BY avg_hours ASC;


-- Business question: Which categories combine meaningful volume with CSAT under 3.5?
-- Why management cares: A tiny category with a low score is a different problem from a large category under 3.5. The 3.5 line is a management screen, not the company average.
SELECT
    issue_category,
    COUNT(*) AS tickets,
    ROUND(AVG(satisfaction_score), 2) AS avg_csat,
    ROUND(AVG(resolution_time_hours), 2) AS avg_hours
FROM support_tickets
GROUP BY issue_category
HAVING COUNT(*) >= 1000
   AND AVG(satisfaction_score) < 3.5
ORDER BY avg_csat ASC;


-- Business question: Is agent workload even?
-- Why management cares: An even split argues against starting with a "bad agent" explanation.
SELECT
    assigned_agent,
    COUNT(*) AS tickets,
    ROUND(AVG(resolution_time_hours), 2) AS avg_hours,
    ROUND(AVG(satisfaction_score), 2) AS avg_csat,
    MIN(satisfaction_score) AS min_csat,
    MAX(satisfaction_score) AS max_csat
FROM support_tickets
GROUP BY assigned_agent
ORDER BY tickets DESC;


-- Business question: Do slower tickets have lower satisfaction?
-- Why management cares: If CSAT only drops after a long handle time, speed is part of the experience story. The 48-hour cut is a description of this file, not an SLA.
SELECT
    CASE
        WHEN resolution_time_hours <= 24 THEN '01. Within 24h'
        WHEN resolution_time_hours <= 48 THEN '02. 25 to 48h'
        WHEN resolution_time_hours <= 72 THEN '03. 49 to 72h'
        ELSE '04. Over 72h'
    END AS handle_time_band,
    COUNT(*) AS tickets,
    ROUND(AVG(resolution_time_hours), 2) AS avg_hours,
    ROUND(AVG(satisfaction_score), 2) AS avg_csat
FROM support_tickets
WHERE resolution_time_hours IS NOT NULL
GROUP BY handle_time_band
ORDER BY handle_time_band;


-- Business question: Is monthly intake rising, flat, or falling?
-- Why management cares: A rising queue needs capacity. A flat queue with a CSAT problem needs a process change, not more people by default.
SELECT
    DATE_TRUNC('month', submission_date)::date AS month_start,
    COUNT(*) AS tickets,
    ROUND(AVG(resolution_time_hours), 2) AS avg_hours,
    ROUND(AVG(satisfaction_score), 2) AS avg_csat,
    MIN(submission_date) AS first_day,
    MAX(submission_date) AS last_day
FROM support_tickets
GROUP BY DATE_TRUNC('month', submission_date)
ORDER BY month_start;


-- =============================================================================
-- Tuesday Sep 15 — CTEs
-- =============================================================================
--
-- Interview drill: Why use a CTE rather than one huge nested query?
-- A CTE names a step (company baseline, then category comparison) so a reader
-- can check that step on its own. The same baseline can be reused instead of
-- pasting a subquery twice. In current PostgreSQL a CTE is often inlined, so
-- it is not automatically faster or slower than a nested query. Use it for
-- clarity and reuse, then look at the plan if the query is slow.


-- Business question: Which categories sit above the company-average resolution time?
-- Why management cares: "Above average" is only meaningful against the company number, not against a guess.
WITH company AS (
    SELECT AVG(resolution_time_hours) AS company_avg_hours
    FROM support_tickets
    WHERE resolution_time_hours IS NOT NULL
),
category_stats AS (
    SELECT
        issue_category,
        COUNT(*) AS tickets,
        AVG(resolution_time_hours) AS avg_hours
    FROM support_tickets
    WHERE resolution_time_hours IS NOT NULL
    GROUP BY issue_category
)
SELECT
    category_stats.issue_category,
    category_stats.tickets,
    ROUND(category_stats.avg_hours, 2) AS avg_hours,
    ROUND(company.company_avg_hours, 2) AS company_avg_hours,
    ROUND((category_stats.avg_hours - company.company_avg_hours)::numeric, 2) AS hours_vs_company
FROM category_stats
CROSS JOIN company
WHERE category_stats.avg_hours > company.company_avg_hours
ORDER BY hours_vs_company DESC;


-- Business question: Which category and priority combinations sit below the company CSAT?
-- Why management cares: A low score on Critical Fraud is a different conversation from a low score on Low Billing.
WITH company AS (
    SELECT AVG(satisfaction_score) AS company_avg_csat
    FROM support_tickets
    WHERE satisfaction_score IS NOT NULL
),
combo_stats AS (
    SELECT
        issue_category,
        priority_level,
        COUNT(*) AS tickets,
        AVG(satisfaction_score) AS avg_csat
    FROM support_tickets
    WHERE satisfaction_score IS NOT NULL
    GROUP BY issue_category, priority_level
)
SELECT
    combo_stats.issue_category,
    combo_stats.priority_level,
    combo_stats.tickets,
    ROUND(combo_stats.avg_csat, 2) AS avg_csat,
    ROUND(company.company_avg_csat, 2) AS company_avg_csat
FROM combo_stats
CROSS JOIN company
WHERE combo_stats.avg_csat < company.company_avg_csat
ORDER BY combo_stats.avg_csat ASC, combo_stats.tickets DESC;


-- Business question: Are certain categories associated with disproportionately poor CSAT?
-- Why management cares: Volume share times the CSAT gap shows who moves the company score, not just who has a small unhappy pocket.
WITH company AS (
    SELECT
        AVG(satisfaction_score) AS company_avg_csat,
        COUNT(*) AS company_tickets
    FROM support_tickets
    WHERE satisfaction_score IS NOT NULL
),
category_stats AS (
    SELECT
        issue_category,
        COUNT(*) AS tickets,
        AVG(satisfaction_score) AS avg_csat
    FROM support_tickets
    WHERE satisfaction_score IS NOT NULL
    GROUP BY issue_category
)
SELECT
    category_stats.issue_category,
    category_stats.tickets,
    ROUND(100.0 * category_stats.tickets / company.company_tickets, 1) AS volume_pct,
    ROUND(category_stats.avg_csat, 2) AS avg_csat,
    ROUND(company.company_avg_csat, 2) AS company_avg_csat,
    ROUND((category_stats.avg_csat - company.company_avg_csat)::numeric, 2) AS csat_vs_company
FROM category_stats
CROSS JOIN company
ORDER BY csat_vs_company ASC;


-- Business question: Which categories are both slower than the company and large enough to matter?
-- Why management cares: Combines the speed gap with a volume floor so a tiny slow category does not outrank a large one.
WITH company AS (
    SELECT AVG(resolution_time_hours) AS company_avg_hours
    FROM support_tickets
    WHERE resolution_time_hours IS NOT NULL
),
category_stats AS (
    SELECT
        issue_category,
        COUNT(*) AS tickets,
        AVG(resolution_time_hours) AS avg_hours,
        AVG(satisfaction_score) AS avg_csat
    FROM support_tickets
    GROUP BY issue_category
)
SELECT
    category_stats.issue_category,
    category_stats.tickets,
    ROUND(category_stats.avg_hours, 2) AS avg_hours,
    ROUND(company.company_avg_hours, 2) AS company_avg_hours,
    ROUND(category_stats.avg_csat, 2) AS avg_csat
FROM category_stats
CROSS JOIN company
WHERE category_stats.tickets >= 1000
  AND category_stats.avg_hours > company.company_avg_hours
ORDER BY category_stats.avg_hours DESC;


-- Business question: Do any agents sit below the company CSAT?
-- Why management cares: If nobody does, agent coaching is the wrong first project.
WITH company AS (
    SELECT AVG(satisfaction_score) AS company_avg_csat
    FROM support_tickets
    WHERE satisfaction_score IS NOT NULL
),
agent_stats AS (
    SELECT
        assigned_agent,
        COUNT(*) AS tickets,
        AVG(satisfaction_score) AS avg_csat,
        AVG(resolution_time_hours) AS avg_hours
    FROM support_tickets
    GROUP BY assigned_agent
)
SELECT
    agent_stats.assigned_agent,
    agent_stats.tickets,
    ROUND(agent_stats.avg_csat, 2) AS avg_csat,
    ROUND(company.company_avg_csat, 2) AS company_avg_csat,
    ROUND((agent_stats.avg_csat - company.company_avg_csat)::numeric, 2) AS csat_vs_company,
    ROUND(agent_stats.avg_hours, 2) AS avg_hours
FROM agent_stats
CROSS JOIN company
ORDER BY agent_stats.avg_csat ASC;


-- =============================================================================
-- Wednesday Sep 16 — Window functions
-- ROW_NUMBER, RANK, DENSE_RANK, AVG() OVER, SUM() OVER, LAG
-- =============================================================================

-- Business question: How do categories rank on volume, and would ties change the rank?
-- Why management cares: ROW_NUMBER always breaks ties. RANK skips, DENSE_RANK does not. With five different volumes the three numbers match; they would not if two categories tied.
WITH category_volume AS (
    SELECT
        issue_category,
        COUNT(*) AS tickets
    FROM support_tickets
    GROUP BY issue_category
)
SELECT
    issue_category,
    tickets,
    ROW_NUMBER() OVER (ORDER BY tickets DESC) AS volume_row_number,
    RANK() OVER (ORDER BY tickets DESC) AS volume_rank,
    DENSE_RANK() OVER (ORDER BY tickets DESC) AS volume_dense_rank
FROM category_volume
ORDER BY tickets DESC;


-- Business question: How do categories rank on average resolution time?
-- Why management cares: Rank 1 here is the slowest category, which is the operational problem, not a prize.
WITH category_speed AS (
    SELECT
        issue_category,
        COUNT(*) AS tickets,
        AVG(resolution_time_hours) AS avg_hours
    FROM support_tickets
    WHERE resolution_time_hours IS NOT NULL
    GROUP BY issue_category
)
SELECT
    issue_category,
    tickets,
    ROUND(avg_hours, 2) AS avg_hours,
    RANK() OVER (ORDER BY avg_hours DESC) AS slowest_rank,
    DENSE_RANK() OVER (ORDER BY avg_hours ASC) AS fastest_dense_rank
FROM category_speed
ORDER BY avg_hours DESC;


-- Business question: How does each category's handle time compare with the company average on the same row?
-- Why management cares: AVG() OVER () repeats the ticket-weighted company average beside every category. Averaging the five category averages would not.
WITH ticket_with_company AS (
    SELECT
        issue_category,
        resolution_time_hours,
        AVG(resolution_time_hours) OVER () AS company_avg_hours
    FROM support_tickets
    WHERE resolution_time_hours IS NOT NULL
)
SELECT
    issue_category,
    COUNT(*) AS tickets,
    ROUND(AVG(resolution_time_hours), 2) AS category_avg_hours,
    ROUND(MAX(company_avg_hours), 2) AS company_avg_hours,
    ROUND((AVG(resolution_time_hours) - MAX(company_avg_hours))::numeric, 2) AS hours_vs_company
FROM ticket_with_company
GROUP BY issue_category
ORDER BY hours_vs_company DESC;


-- Business question: What is the running ticket total across submission months?
-- Why management cares: This is cumulative intake, not an open backlog. It answers "how many tickets had arrived by this month?"
WITH monthly AS (
    SELECT
        DATE_TRUNC('month', submission_date)::date AS month_start,
        COUNT(*) AS tickets
    FROM support_tickets
    GROUP BY DATE_TRUNC('month', submission_date)
)
SELECT
    month_start,
    tickets,
    SUM(tickets) OVER (ORDER BY month_start) AS running_tickets
FROM monthly
ORDER BY month_start;


-- Business question: How does each month's volume, CSAT, and handle time compare with the prior month?
-- Why management cares: LAG shows the change. A single up month is not a trend.
WITH monthly AS (
    SELECT
        DATE_TRUNC('month', submission_date)::date AS month_start,
        COUNT(*) AS tickets,
        AVG(satisfaction_score) AS avg_csat,
        AVG(resolution_time_hours) AS avg_hours
    FROM support_tickets
    GROUP BY DATE_TRUNC('month', submission_date)
)
SELECT
    month_start,
    tickets,
    LAG(tickets) OVER (ORDER BY month_start) AS prior_month_tickets,
    tickets - LAG(tickets) OVER (ORDER BY month_start) AS volume_change,
    ROUND(avg_csat, 2) AS avg_csat,
    ROUND(
        (avg_csat - LAG(avg_csat) OVER (ORDER BY month_start))::numeric,
        2
    ) AS csat_change,
    ROUND(avg_hours, 2) AS avg_hours,
    ROUND(
        (avg_hours - LAG(avg_hours) OVER (ORDER BY month_start))::numeric,
        2
    ) AS hours_change
FROM monthly
ORDER BY month_start;


-- =============================================================================
-- Thursday Sep 17 — Illustrative project SLA assumptions
-- =============================================================================
--
-- These targets are project assumptions from docs/kpis.md. They are not
-- CloudDesk policy and they are not printed on the extract.
--   Critical 24 hours
--   High, and Urgent if it appears, 48 hours
--   Medium and Low 72 hours
-- Textbook bars (Critical 4h / High 8h) are not used. They would mark almost
-- every ticket as a breach and would not be a useful management report.
-- Tickets with no resolution hours are left unscored and dropped from the rate.

-- Business question: What is the overall illustrative breach rate?
-- Why management cares: One number for the assumed targets, with the unscored rows shown so the denominator is honest.
WITH targets AS (
    SELECT
        ticket_id,
        resolution_time_hours,
        CASE
            WHEN lower(priority_level) = 'critical' THEN 24
            WHEN lower(priority_level) IN ('high', 'urgent') THEN 48
            ELSE 72
        END AS sla_target_hours
    FROM support_tickets
),
scored AS (
    SELECT
        ticket_id,
        resolution_time_hours,
        sla_target_hours,
        CASE
            WHEN resolution_time_hours IS NULL THEN NULL
            WHEN resolution_time_hours > sla_target_hours THEN 1
            ELSE 0
        END AS sla_breach
    FROM targets
)
SELECT
    COUNT(*) AS tickets,
    COUNT(sla_breach) AS scored_tickets,
    COUNT(*) - COUNT(sla_breach) AS unscored_tickets,
    SUM(sla_breach) AS breaches,
    ROUND(100.0 * SUM(sla_breach) / NULLIF(COUNT(sla_breach), 0), 1) AS breach_pct
FROM scored;


-- Business question: Which categories contribute the most illustrative SLA failures?
-- Why management cares: Breach rate and breach count answer different questions. A small category can have a high rate and still be few tickets.
WITH targets AS (
    SELECT
        issue_category,
        resolution_time_hours,
        CASE
            WHEN lower(priority_level) = 'critical' THEN 24
            WHEN lower(priority_level) IN ('high', 'urgent') THEN 48
            ELSE 72
        END AS sla_target_hours
    FROM support_tickets
),
scored AS (
    SELECT
        issue_category,
        CASE
            WHEN resolution_time_hours IS NULL THEN NULL
            WHEN resolution_time_hours > sla_target_hours THEN 1
            ELSE 0
        END AS sla_breach
    FROM targets
)
SELECT
    issue_category,
    COUNT(sla_breach) AS scored_tickets,
    SUM(sla_breach) AS breaches,
    ROUND(100.0 * SUM(sla_breach) / NULLIF(COUNT(sla_breach), 0), 1) AS breach_pct,
    ROUND(
        100.0 * SUM(sla_breach) / NULLIF(SUM(SUM(sla_breach)) OVER (), 0),
        1
    ) AS share_of_all_breaches_pct
FROM scored
GROUP BY issue_category
ORDER BY breaches DESC;


-- Business question: Which priority has the highest illustrative breach rate?
-- Why management cares: The target is stricter for Critical. A high Critical breach rate means the 24-hour bar is being missed, not that Critical is the slowest group in raw hours.
WITH targets AS (
    SELECT
        priority_level,
        resolution_time_hours,
        CASE
            WHEN lower(priority_level) = 'critical' THEN 24
            WHEN lower(priority_level) IN ('high', 'urgent') THEN 48
            ELSE 72
        END AS sla_target_hours
    FROM support_tickets
),
scored AS (
    SELECT
        priority_level,
        sla_target_hours,
        CASE
            WHEN resolution_time_hours IS NULL THEN NULL
            WHEN resolution_time_hours > sla_target_hours THEN 1
            ELSE 0
        END AS sla_breach
    FROM targets
)
SELECT
    priority_level,
    MAX(sla_target_hours) AS illustrative_target_hours,
    COUNT(sla_breach) AS scored_tickets,
    SUM(sla_breach) AS breaches,
    ROUND(100.0 * SUM(sla_breach) / NULLIF(COUNT(sla_breach), 0), 1) AS breach_pct
FROM scored
GROUP BY priority_level
ORDER BY breach_pct DESC;


-- Business question: Which channel has the highest illustrative breach rate?
-- Why management cares: If channels are close, do not launch a channel project to fix an assumed SLA.
WITH targets AS (
    SELECT
        ticket_channel,
        priority_level,
        resolution_time_hours,
        CASE
            WHEN lower(priority_level) = 'critical' THEN 24
            WHEN lower(priority_level) IN ('high', 'urgent') THEN 48
            ELSE 72
        END AS sla_target_hours
    FROM support_tickets
),
scored AS (
    SELECT
        ticket_channel,
        CASE
            WHEN resolution_time_hours IS NULL THEN NULL
            WHEN resolution_time_hours > sla_target_hours THEN 1
            ELSE 0
        END AS sla_breach
    FROM targets
)
SELECT
    ticket_channel,
    COUNT(sla_breach) AS scored_tickets,
    SUM(sla_breach) AS breaches,
    ROUND(100.0 * SUM(sla_breach) / NULLIF(COUNT(sla_breach), 0), 1) AS breach_pct
FROM scored
GROUP BY ticket_channel
ORDER BY breach_pct DESC;
