# AI evaluation method

Ground truth for this pass is `evaluation/eval_tickets.csv`. It has 30 tickets, one for each distinct customer sentence in the extract. I assigned `expected_category`, `expected_priority`, and `expected_sentiment` by reading that sentence. No model labeled those three columns.

The score key is those three columns. `source_issue_category` and `source_priority_level` are the original extract values. They are there for a later comparison. They are not sent to the model, and they are not the score.

## How a row was labeled

The description starts with `Hi Support,` and one real request. The rest of the description is filler. The label comes from the request sentence.

The subject is often a different issue. `ambiguous` is `yes` when the subject stem points at a different category than the sentence. Example: subject `Password reset` with the sentence `How do I upgrade to the Enterprise plan?` is an Account question, so `ambiguous` is `yes`.

| Customer sentence | Category | Priority | Sentiment |
| --- | --- | --- | --- |
| I cannot log into my account even after resetting the password. | Authentication | High | Frustrated |
| I lost my phone and cannot pass the 2FA check. | Authentication | High | Frustrated |
| I am not receiving the password reset email. | Authentication | High | Frustrated |
| How do I upgrade to the Enterprise plan? | Account | Low | Neutral |
| Please help me change the email address associated with my account. | Account | Medium | Neutral |
| I want to permanently delete my account and data. | Account | Medium | Neutral |
| My profile picture is not updating. | Account | Low | Frustrated |
| Can you send me the invoice for transaction #99283? | Billing | Medium | Neutral |
| I requested a refund 5 days ago, where is it? | Billing | High | Frustrated |
| I noticed a double charge on my statement for last month. | Billing | High | Frustrated |
| Why is my bill higher than the agreed amount? | Billing | Medium | Frustrated |
| My subscription renewed automatically, but I wanted to cancel. | Billing | Medium | Frustrated |
| I have been trying to update my payment method but it keeps failing. | Billing | High | Frustrated |
| How do I install the latest patch on Windows 11? | Technical | Low | Neutral |
| The application crashes every time I open the settings tab. | Technical | High | Frustrated |
| The dashboard is not loading any data, just a spinning wheel. | Technical | High | Frustrated |
| My data hasn't synced to the cloud for 24 hours. | Technical | High | Frustrated |
| We are receiving a 500 Internal Server Error on the API endpoint. | Technical | High | Frustrated |
| I think my account has been compromised. | Fraud | Critical | Concerned |
| Why is there a new device added to my trusted list? | Fraud | High | Concerned |
| Someone used my card to make a purchase on your site. | Fraud | Critical | Concerned |
| I received a suspicious email claiming to be support. | Fraud | High | Concerned |
| Lock my account immediately, I see transactions I didn't make. | Fraud | Critical | Urgent |
| I received a login alert from a device in Russia, which wasn't me. | Fraud | High | Concerned |
| Do you offer a discount for non-profits? | General Inquiry | Low | Neutral |
| Where is your headquarters located? | General Inquiry | Low | Neutral |
| How does the team pricing tier work? | General Inquiry | Low | Neutral |
| Is there a roadmap for new features this year? | General Inquiry | Low | Neutral |
| What are your support operating hours? | General Inquiry | Low | Neutral |
| I would like to request a demo for my team. | General Inquiry | Low | Neutral |

The login sentence is also the example in `docs/ai-contract.md`. That one row is not a blind item.

## What the scorer counts

`src/evaluate_ai.py` sends only the subject and description. It uses the same structured output as `src/ai_service.py`.

On valid JSON:

- Category exact match: `category` equals `expected_category`.
- Priority exact match: `priority` equals `expected_priority`.
- Sentiment exact match: `sentiment` equals `expected_sentiment`.

Rates use valid outputs only.

Invalid outputs are calls that raise, return nothing, or fall outside the allowed values. They are not given a category match.

## Error categories

A valid miss can have more than one label.

| Label | When it is applied |
| --- | --- |
| Ambiguous ticket | Category is wrong, and `ambiguous` is `yes`. The subject and the customer sentence disagree. |
| Wrong classification | Category is wrong, and the ticket is not ambiguous. |
| Over-escalation | Model priority ranks above the expected priority. Order: Low, Medium, High, Critical. |
| Under-escalation | Model priority ranks below the expected priority. |
| Unsupported recommendation | `recommended_action` is not the queue for the category the model chose. |
| Bad prompt | The summary, reason, or action says a refund was issued, a customer message was sent, or an incident is underway. |
| Invalid output | The call failed or the object broke the contract. |

Sentiment misses are in the sentiment exact-match rate. A sentiment-only miss does not also become "Wrong classification."
