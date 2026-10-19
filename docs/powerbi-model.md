# Power BI model

Power BI should read this star schema, not `support_tickets` and not the CSV. The SQL is `sql/20_powerbi_model.sql`. The objects are views, so a refresh after `src/etl.py` picks up the latest load.

```text
               dim_date
                   |
dim_category — fact_tickets — dim_channel
                   |
              dim_priority
```

`fact_tickets` is one row per ticket. Category, priority, channel, and date attributes stay on the dimensions. Power BI filters flow from each dimension into the fact.

## Grain and source

| Object | Grain | Rows come from |
| --- | --- | --- |
| `fact_tickets` | One ticket | `support_tickets` |
| `dim_date` | One calendar day from the first submission date through the last | `submission_date` |
| `dim_category` | One issue category | Distinct `issue_category` |
| `dim_priority` | One priority label | Distinct `priority_level` |
| `dim_channel` | One channel | Distinct `ticket_channel` |

Customer name, email, subject, description, and agent are not in this model. Agent is not a dimension here. Staging and the AI tables stay out of the report.

## Columns

**fact_tickets**

| Column | Use in the report |
| --- | --- |
| `ticket_id` | Ticket count. Hide it on visuals that only need a number. |
| `date_key`, `category_key`, `priority_key`, `channel_key` | Relationship keys. Hide them. |
| `resolution_time_hours` | Average and median handle time. Blanks stay blank. They are not zero. |
| `satisfaction_score` | Average CSAT on the 1–5 scale. |
| `is_high_priority` | 1 when the priority is High, Critical, or Urgent. Same rule as `src/config.py`. |
| `sla_breach` | 1 when hours exceed that priority's illustrative target, 0 when they do not, blank when hours are missing. |

**dim_date.** `date_key` is `YYYYMMDD`. `full_date` is the date column to mark as a date table in Power BI. Also year, quarter, month number, month name, month start, `year_month` (`2024-01`), and day of month. Days with no tickets are still in the dimension, so a month axis does not skip them.

**dim_category.** `category_key`, `category_name`.

**dim_channel.** `channel_key`, `channel_name`.

**dim_priority.** `priority_key` is also the sort order: Critical 1, Urgent 2, High 3, Medium 4, Low 5. `priority_band` is High priority or Standard priority. `illustrative_sla_hours` is the project assumption from `docs/kpis.md`:

| Priority | Illustrative target |
| --- | --- |
| Critical | 24 hours |
| High, Urgent | 48 hours |
| Medium, Low | 72 hours |

Those hours are not a policy stored in the extract. Do not label a breach visual as a company SLA.

## Relationships

Create these in Model view. Cardinality is many tickets to one dimension row. Filter direction is single, from the dimension to `fact_tickets`.

| From | To |
| --- | --- |
| `fact_tickets.date_key` | `dim_date.date_key` |
| `fact_tickets.category_key` | `dim_category.category_key` |
| `fact_tickets.priority_key` | `dim_priority.priority_key` |
| `fact_tickets.channel_key` | `dim_channel.channel_key` |

Mark `dim_date` as a date table on `full_date`. Sort `priority_name` by `priority_key`, and `month_name` by `month_number`.

## Measures to put on the page

Use the columns above. Do not retype the high-priority rule or the SLA hours in DAX.

- Ticket volume: count of `ticket_id`
- Average handle time: average of `resolution_time_hours`
- Average CSAT: average of `satisfaction_score`
- High-priority tickets: sum of `is_high_priority`
- Illustrative breach %: sum of `sla_breach` divided by the count of rows where `sla_breach` is not blank

Title the breach visual **Illustrative project SLA**, with the 24 / 48 / 72 hour targets in the subtitle.

## Load

```bash
psql -d mis_support -f sql/20_powerbi_model.sql
```

Connect Power BI to `mis_support` and import the five views only.
