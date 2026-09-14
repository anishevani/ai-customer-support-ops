# Current-state process

How CloudDesk support works **today**, inferred from the ticket extract and a standard Tier 1/2 queue. There is no live ticketing API in this project; this is the as-is operations story the dashboard is meant to expose.

```text
Customer
   ↓
Creates ticket (Chat / Email / Web Form)
   ↓
Ticket lands in a shared queue
   ↓
Agent reads the full thread
   ↓
Agent sets category and priority (already present on every row in this extract)
   ↓
Ticket is assigned (five agents, almost even load)
   ↓
Investigation / reply loop
   ↓
Escalation only if the agent chooses to (no automation)
   ↓
Resolution (handle time stored as Resolution_Time_Hours)
   ↓
Customer survey (Satisfaction_Score 1–5)
```

## Problems this extract actually supports

| Symptom in the process | Evidence in the data |
| --- | --- |
| Leadership has no trusted view | 20,000 rows, 0% missing — but KPIs lived in ad-hoc Python until they were defined |
| Billing customers leave unhappy | Billing CSAT **2.98 / 5** vs ~**4.04** for Technical, Account, General Inquiry |
| “We are slow” is partly a long tail | Median handle time **27h**, mean **39h**; 31% of tickets take more than 48h |
| Unstructured questions sit in queue | General Inquiry averages **43h**; Fraud averages **16h** and is 100% High/Critical |
| Priority is used, but not evenly | Critical mean **12h**, Low mean **45h** — the queue respects Critical; it does not drain General Inquiry |
| Agent coaching is the wrong first lever | Five agents each handle ~4,000 tickets with CSAT ~3.72 |

## What we cannot claim yet

- Inconsistent **manual** categorization: the file already has a category on every ticket and no “original vs final” field.
- Slow **first response**: no first-response timestamp.
- Channel as the CSAT driver: Chat, Email, and Web Form all average ~3.7.

## Why this matters

Managers are reacting after CSAT arrives. They cannot see Billing vs Technical, or mean vs median, without exporting CSV again. V1 does not change how agents work; it changes **what leadership can see** so the next process change (Billing, self-service for General Inquiry) is based on a shared number.
