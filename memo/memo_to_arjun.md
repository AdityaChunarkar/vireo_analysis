# Refunds: what the data says, and the one number worth acting on

**To:** Arjun Mehta, Finance Controller
**Re:** Monthly refunds by reason code and by agent
**Period:** Jan 2025 – Jun 2026 (18 months, 11,600 tickets, 2,340 refunds, Rs 6.71M)

---

## Refunds have gone up. The refund *rate* has not.

Refund spend roughly doubled — from about Rs 203,000 a month in early 2025 to about Rs 427,000 a month in Q2 2026, a factor of 2.1. Over the same period, support tickets went from about 351 a month to about 759. Tickets more than doubled.

The share of tickets ending in a refund barely moved: **20.1% then, 20.8% now.**

Refunds are up because the business is bigger, not because the desk got looser. That is the honest answer to "why have refunds gone up", and it means a crackdown on refund volume would be aimed at the wrong target.

There is a real problem in the data. It is smaller than the headline, and more fixable.

## The reason codes don't explain anything

Every refund is tagged with a reason code from a dropdown. **42.4% of refunds — Rs 2.91M, or 43.3% of all refund spend — are tagged `GW-OTHER` ("Goodwill / Other").**

Reading the agents' own closing notes, most of these are not goodwill at all. They are duplicate payments, cancellations before dispatch, completed returns, and price-adjustment cases — each of which has its own proper code. `GW-OTHER` is the path of least resistance in the dropdown, not a category of spend.

This is why the existing reason breakdown cannot go in a board pack: nearly half of it says "other".

Only **42 refunds in 18 months have closing notes that actually describe a goodwill gesture**, totalling Rs 158,165. Policy caps goodwill at Rs 500 per ticket; all 42 exceed it, by Rs 137,165 in total — about **Rs 22,861 a quarter.** Real, but small.

## The number worth acting on: paying twice for the same order

**257 refunds also had a replacement sent for the same order** — about 14 a month, every month, across the whole period. (166 are flagged as such in the export; the other 91 are only visible in the agent's own closing note, where the structured flag says no replacement was sent.) Policy is explicit that a customer should never receive both, and that any instance must be escalated to the Team Lead and Finance the same day. None of these appear to have been.

The cost depends on which half was the error:

| | 18 months | Per quarter |
|---|---|---|
| Refunds paid where a replacement was also sent | Rs 918,923 | **Rs 153,154** |
| Replacements sent where a refund was also paid (at policy cost) | Rs 472,220 | **Rs 78,703** |

So **Rs 79,000–153,000 a quarter, or roughly Rs 315,000–610,000 a year, is going out twice for the same order.**

The two problems are connected: **150 of the 257 (58%) were tagged `GW-OTHER`.** The mis-tagging is what kept this invisible.

## Recommendation

1. **Block the double payment at source.** A refund and a replacement on the same order should require Team Lead sign-off before either is released. Target: from ~14 a month to zero. Worth Rs 79,000–153,000 a quarter.
2. **Make the dropdown mean something.** Remove `GW-OTHER` as a freely selectable option, or require a one-line justification when it is chosen. Target: below 5% of refunds, from 42.4%. This is a reporting fix, not a cash saving — but without it you cannot see item 1.
3. **Restate goodwill as a policy question, not a leak.** Rs 22,861 a quarter above the Rs 500 cap suggests the cap is either unenforced or unrealistic. Decide which.

## What I have not given you

You asked for a breakdown by agent as well as by reason, to see "who is giving away money". **I have produced the by-agent table, but I would not use it as a performance ranking, and I would not put it in the board pack as one.**

Vireo's own policy says the Returns Desk processes the large majority of refunds by design, and that Tier 2 agents are not to be compared with Tier 1 on volume metrics. A raw ranking of refund spend by agent would put the people doing their assigned job at the top of a list that looks like a leak. The policy-breach view above — double compensation, and goodwill above the cap — is the defensible way to ask the same question, and it points at process, not people.

## Two things to know about the numbers

- **Refund amounts from the old helpdesk were stored in paise, not rupees.** Uncorrected, the 18-month total reads Rs 230M instead of Rs 6.71M. 638 tickets exist in both systems and, on the 125 that carry a refund, the old value is exactly 100× the new one with no variation. That is the basis for the correction.
- **Those same 638 tickets are duplicated in the export.** Counted twice, they inflate every total by about 5%.

Both are corrected in the attached figures. Neither was flagged in the export itself.

---

*Figures derived from the support export, orders file and the Support Operating Policy v3.2. Every number in this memo is reproducible from the attached tool and the audit CSVs.*
