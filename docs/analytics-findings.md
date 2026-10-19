# Analytics findings

Source: `support_tickets` in `mis_support`, loaded from the 20,000-row extract. Queries: `sql/10_business_analysis.sql`. Grain is one ticket. Handle time is hours from submission to close.

Company baseline from those queries: **20,000 tickets**, **2 January 2024 through 1 January 2026**, mean handle time **39.23 hours**, median **27 hours**, mean CSAT **3.72 / 5**.

The SLA figures use the **illustrative project assumptions** in `docs/kpis.md` (Critical 24 hours, High 48 hours, Medium and Low 72 hours). They are not a policy printed on the extract. Textbook targets such as Critical within 4 hours were not used.

---

## 1. Billing is associated with much lower satisfaction, and it is a large share of the queue

**Finding.** Billing averages **2.98 / 5**, which is **0.74 points below** the company average of 3.72. Technical, Account, and General Inquiry sit at **4.04 to 4.05**. Billing is **5,036 tickets, 25.2% of volume**.

**Evidence.** Category CSAT query (Tuesday). The only category-priority combinations below the company CSAT are Billing Low (2.97, 2,524 tickets), Billing Medium (2.97, 1,962), Billing High (3.10, 550), Fraud Critical (3.03, 716), and Fraud High (3.03, 324). There is no Billing Critical row in this extract.

**Possible explanation.** Billing High averages **24.71 hours**, almost the same as Technical High at **24.15 hours**, but Technical High scores **4.04**. Account Low and Billing Low are both about **45 hours**, and Account Low scores **4.06** against Billing Low at **2.97**. The gap shows up inside the same priority and a similar handle time, so "Billing is slower" does not account for it. The text of the tickets (refunds, duplicate charges, plan changes) is a plausible place to look. This file cannot show which of those is responsible.

**Business implication.** A one-point CSAT gap on a quarter of the queue moves the company score. A manager looking only at the 3.72 average will miss where the average comes from.

**Recommended next investigation.** Read a sample of Billing ticket text and tag refund, duplicate charge, and plan change. Compare CSAT inside those tags before changing the billing process.

**Limitation.** This is an association in one extract. It does not show that the Billing category causes the score. Category is the label already on the ticket, not a diagnosis.

---

## 2. Faster resolution is not associated with higher satisfaction in this file

**Finding.** Tickets closed within 24 hours average **3.73** CSAT. Tickets over 72 hours, at a mean of **102 hours**, average **3.71**. Fraud is the fastest category (**15.76 hours**, median **11**) and still scores **3.03**.

**Evidence.** Handle-time band query (Monday) and the category speed and CSAT queries (Monday and Tuesday).

**Possible explanation.** Customers may be scoring the outcome (a refund that did not arrive, a fraud worry that is still open in their mind) rather than the clock. Fraud is also entirely High or Critical, so its low score is mixed with priority. Technical Critical is just as fast (**12.61 hours**) and scores **4.06**, which fits an outcome story better than a speed story. That is a hypothesis, not a result.

**Business implication.** A project whose only goal is to shave hours off Billing or Fraud should not promise a CSAT lift. Speed still matters for the queue. It is a weak explanation of the score gap in this extract.

**Recommended next investigation.** Hold category and priority fixed and test CSAT against hours again on a later extract, or tag whether the customer's request was actually resolved.

**Limitation.** The 24/48/72 hour bands are cuts chosen for this report. They are not the SLA. A different cut could move the averages slightly. It will not turn 3.71 into 2.98.

---

## 3. Higher priority is associated with faster resolution. It is not associated with higher CSAT

**Finding.** Critical averages **12.07 hours**, High **24.52**, Medium **44.47**, Low **45.17**. High-priority tickets as a group (High, Critical, or Urgent) average **21.09 hours** against **44.82** for everyone else. Critical CSAT is **3.49**, the lowest of the four priority labels. High is **3.79**.

**Evidence.** Priority aggregation (Monday). Fraud is **716 of 1,298** Critical tickets (about 55%) and those Fraud Critical rows score **3.03**. Technical Critical scores **4.06**.

**Possible explanation.** The queue appears to work Critical and High tickets sooner. Critical's lower CSAT is consistent with mix: more than half of Critical volume is Fraud, which scores about 3.0 at every priority it appears in. Priority itself is not shown to make customers happier.

**Business implication.** Priority is doing a speed job. It is a poor dashboard for satisfaction. Reporting "Critical CSAT" without the category mix will send a manager after the wrong process.

**Recommended next investigation.** Keep reporting handle time by priority. Report CSAT by category inside each priority, which the category-priority query already starts.

**Limitation.** "Higher priority, faster resolution" is a comparison of group averages, not a correlation coefficient, and not evidence that the priority label caused the speed. Staff may be using other signals that happen to match the label.

---

## 4. Under the illustrative SLA, about one ticket in five is past the target. Channel does not matter

**Finding.** **4,102 of 20,000** scored tickets are past the illustrative target, **20.5%**. No ticket was missing hours, so none were left unscored. Breach rates by channel are **20.6% Email, 20.6% Web Form, 20.4% Chat**.

By priority, against that priority's own target: Low **23.0%** (1,774 breaches), Medium **22.5%** (1,703), High **13.7%** (467), Critical **12.2%** (158).

By category, breach *counts* follow volume: Technical **1,102** (26.9% of all breaches, rate 18.6%), Billing **1,095** (26.7%, rate 21.7%), Account **894** (21.8%, rate 21.9%), General Inquiry **883** (21.5%, rate 22.5%), Fraud **128** (3.1%, rate 12.3%).

**Evidence.** Thursday SLA queries. Targets are the documented assumptions: Critical 24 hours, High 48 hours, Medium and Low 72 hours.

**Possible explanation.** Low and Medium use a 72-hour bar and their typical ticket is already near 45 hours, so the long tail crosses 72 hours often. Critical uses a stricter 24-hour bar and still breaches less often, because those tickets close sooner. Fraud's low breach rate fits its short handle time, not a special channel.

**Business implication.** A channel program will not move this breach rate. The breach pile is the slow tail of ordinary Low and Medium work, spread across the four large categories. Fraud is not where the missed targets sit.

**Recommended next investigation.** Only if leadership adopts a real target. Until then, keep mean and median handle time as the speed metrics, and treat 20.5% as a what-if.

**Limitation.** These percentages are not operational failures against a company policy. A 4-hour Critical target would call almost everything a breach and would describe the assumption, not the queue.

---

## 5. Across two years, volume and CSAT do not trend. Agents do not separate

**Finding.** Full months run from about **734 to 864** tickets. Monthly CSAT stays between **3.64 and 3.79**. Monthly mean handle time stays in the high 30s, with ordinary up-and-down months. **1 January 2026 is 18 tickets on a single day.** It is not a collapsed month. The five agents each handle about **3,970 to 4,025** tickets, and their CSAT sits between **3.71 and 3.74**.

**Evidence.** Monthly aggregation, running total, and month-to-month `LAG` (Monday and Wednesday). Agent query (Monday and Tuesday). Running intake reaches **19,982** by December 2025 and **20,000** after the partial January day.

**Possible explanation.** The extract looks like a stable intake process. Agent scores match so closely that a staffing or coaching story is unlikely to be the first explanation of the Billing gap. A month-to-month chart that includes January 2026 will look like a crash because the prior month had 852 tickets.

**Business implication.** Do not add headcount or launch an agent-quality program on the back of this file. Do not brief January 2026 as a deterioration.

**Recommended next investigation.** Drop any month that does not cover a full set of days before reading `LAG`. If a later extract shows a real drift, then reopen capacity.

**Limitation.** Submission month is when the ticket arrived, not when it closed. The running total is cumulative intake, not an open backlog. Agent CSAT is not adjusted for category mix. In this file the agent scores are too close for mix to be hiding a large agent effect, but the query does not prove the mixes are identical.

---

## Five-minute presentation

Say this before showing any query. About five minutes.

I identified three things management should pay attention to.

First, satisfaction is not a company-wide problem. The average is 3.72 out of 5. Billing is 2.98, and Billing is a quarter of the tickets. Technical, Account, and General Inquiry are all about 4.04. Fraud is also low, about 3.03, but it is only 5 percent of volume. When I hold the clock roughly still, the gap remains. Billing High and Technical High both take about 25 hours. Technical scores 4.04. Billing scores 3.10. I am not saying the Billing label causes the score. I am saying this is where a process review should start, and the ticket text is the next sample to read.

Second, the priority label is associated with speed, and it is not associated with happier customers. Critical tickets average 12 hours. Low tickets average 45. That is the queue doing what priority is for. Critical satisfaction is the weakest of the four labels, at 3.49, and more than half of Critical volume is Fraud. Faster tickets overall are not happier either. Tickets closed within a day score 3.73. Tickets that take more than 72 hours score 3.71. A program that only shortens handle time should not be sold as a satisfaction program.

Third, do not staff from the trend line, and do not treat the illustrative SLA as a policy we missed. Month to month, volume stays near 800 tickets and satisfaction stays in a band of about 3.64 to 3.79. The five agents each have about 4,000 tickets and the same score. January 2026 is 18 tickets on one day. It is not a collapse. Using the project's assumed targets, Critical within 24 hours, High within 48, Medium and Low within 72, about 20 percent of tickets sit past the bar. Email, chat, and web form are the same. The misses pile up in ordinary Low and Medium work, not in a broken Critical process and not in one channel.

What I would do next is narrow. Sample Billing tickets and separate refunds, duplicate charges, and plan changes. Keep reporting speed by priority. Leave headcount and channel projects until a later extract shows something this one does not.
