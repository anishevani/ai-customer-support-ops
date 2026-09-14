-- Small demo dataset matching sql/01_schema.sql
-- Run after the schema:
--   psql -d support_ops -f sql/03_seed.sql

INSERT INTO customers (customer_id, customer_name, customer_email) VALUES
    (1, 'Ada Lovelace', 'ada@example.com'),
    (2, 'Alan Turing', 'alan@example.com'),
    (3, 'Grace Hopper', 'grace@example.com'),
    (4, 'Katherine Johnson', 'kj@example.com'),
    (5, 'Linus Torvalds', 'linus@example.com')
ON CONFLICT (customer_id) DO NOTHING;

INSERT INTO agents (agent_id, agent_name) VALUES
    (1, 'Anya Sharma'),
    (2, 'Ben Carter'),
    (3, 'Chloe Adams'),
    (4, 'David Kim'),
    (5, 'Elena Rodriguez')
ON CONFLICT (agent_id) DO NOTHING;

INSERT INTO tickets (
    ticket_id,
    customer_id,
    agent_id,
    ticket_subject,
    ticket_description,
    issue_category,
    priority_level,
    ticket_channel,
    submission_date,
    resolution_time_hours,
    satisfaction_score
) VALUES
    ('TKT-101', 1, 1, 'Login failed', 'Cannot sign in after password reset.', 'Technical', 'High', 'Email', '2025-01-01', 5.00, 4),
    ('TKT-102', 2, 2, 'Invoice error', 'Customer charged twice for the same month.', 'Billing', 'Low', 'Chat', '2025-01-02', 20.00, 2),
    ('TKT-103', 3, 3, 'Locked account', 'Password reset loop on web form.', 'Account', 'Medium', 'Web Form', '2025-01-03', 8.00, 5),
    ('TKT-104', 4, 4, 'Suspicious login', 'Unknown device signed in overnight.', 'Fraud', 'Critical', 'Email', '2025-01-04', 2.00, 3),
    ('TKT-105', 5, 5, 'Hours of operation', 'Where is headquarters located?', 'General Inquiry', 'High', 'Chat', '2025-01-05', 12.00, 4),
    ('TKT-106', 1, 1, 'App crash', 'Settings tab crashes on open.', 'Technical', 'High', 'Web Form', '2025-01-06', 41.00, 5),
    ('TKT-107', 2, 2, 'Refund delay', 'Promised refund not posted.', 'Billing', 'Medium', 'Email', '2025-01-07', 36.00, 1),
    ('TKT-108', 3, 4, '2FA loop', 'Authenticator code never accepted.', 'Account', 'Low', 'Chat', '2025-01-08', 15.00, 4),
    ('TKT-109', 4, 3, 'Phishing report', 'Customer forwarded a fake invoice.', 'Fraud', 'Critical', 'Phone', '2025-01-09', 1.50, 4),
    ('TKT-110', 5, NULL, 'Feature question', 'Does the mobile app support dark mode?', 'General Inquiry', 'Low', 'Web Form', '2025-01-10', NULL, NULL)
ON CONFLICT (ticket_id) DO NOTHING;

SELECT setval('customers_customer_id_seq', (SELECT MAX(customer_id) FROM customers));
SELECT setval('agents_agent_id_seq', (SELECT MAX(agent_id) FROM agents));
