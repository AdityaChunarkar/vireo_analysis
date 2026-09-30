# Submission form — Vireo Audio refund analysis

> **How to use this draft.** Every figure below is reproducible from the raw export (see `memo_numbers.json`).
> Anything in **[[ ]]** is a blank only you can fill — links, hours, and claims about your tool that I could not verify.
> Delete this block before submitting.

---

**1. What did you build, and what business outcome does it move? State the number and the money.**

A refund-analysis tool that takes the raw helpdesk export and produces a board-ready refund view: monthly refunds by reason code, by agent, and by agent × reason, plus two control reports — a refund-plus-replacement detector and a goodwill-cap check — with a full per-ticket audit trail.

The export cannot be summarised as-is. Three defects had to be corrected first: refund amounts from the legacy helpdesk are stored in paise (uncorrected, the 18-month total reads Rs 230M instead of Rs 6.71M); 638 tickets appear in both source systems and are double-counted; and 42.4% of refunds are tagged `GW-OTHER` ("Goodwill / Other"), which is a dropdown default rather than a reason. The tool re-codes the `GW-OTHER` bucket from the agent's closing note into the eight reason codes the policy defines.

**The number:** 257 refunds over 18 months (~14 a month) also had a replacement issued for the same order, which Vireo's policy §5 says must never happen and must be escalated to Finance the same day. That is Rs 918,923 in refunds paid, or Rs 472,220 in replacement cost at the policy's own costing (unit cost + Rs 340). **Worth Rs 79,000–153,000 a quarter, Rs 315,000–610,000 a year.** 150 of the 257 (58%) were tagged `GW-OTHER`, which is why it was invisible. Only 166 carry the structured `replacement_issued` flag; the other 91 are visible only in the agent's closing note.

**Target:** drive refund-plus-replacement from ~14 a month to zero; drive `GW-OTHER` from 42.4% of refunds to below 5% so the board pack's reason breakdown means something.

---

**2. What does one run cost, and what would a month cost at Vireo's volume (~650 tickets/week)? Show the arithmetic. If you used no paid calls, say so.**

**One run costs Rs 0. No paid API calls were made by the tool.** Classification is a local TF-IDF + logistic-regression model with a rule layer; the run is **[[wall-clock seconds]]** on a laptop, no network, no keys.

At 650 tickets/week:

| | Week | Month (×4.33) |
|---|---|---|
| Tickets | 650 | 2,814 |
| Refund tickets @ 20.0% | 130 | 563 |
| `GW-OTHER` needing re-coding @ 42.9% of refunds | 56 | 242 |

I costed the LLM alternative before discarding it, so the zero is a choice rather than an accident. At ~2,500 input and ~60 output tokens per ticket, 242 tickets/month is about **$0.67/month (Rs ~59) on Haiku 4.5** or **$2.02/month (Rs ~178) on Sonnet 4.5**; the one-off 18-month backfill of 991 tickets is $2.77–$8.31. Prompt caching cuts that to roughly a third.

**So cost was never the reason I dropped the LLM** — at Rs 59/month it would have been trivially affordable. I dropped it for reproducibility: the brief requires the tool to start from the README on a clean machine, and a local model has no keys, no network dependency and no per-run variance.

*Volume note:* the export runs at ~178 tickets/week over the last six months (4,638 across 26 weeks), not 650. I assumed **[[the export is a sample / 650 counts contacts rather than tickets — pick one]]** and scaled the per-ticket arithmetic accordingly. The per-ticket cost is unaffected.

---

**3. How do you know it works? Sample size, how you checked, error rate, the kind of case it gets wrong.**

Three independent checks:

**a) The unit correction is proved, not estimated.** 638 tickets exist in both source systems; 125 of those carry a refund. The legacy value is exactly 100× the helpdesk value on all 125, standard deviation 0.00. Timestamps on all 638 pairs match to the second, and agent and reason fields agree on every pair — so the pairs are genuine duplicates and the ratio is not coincidence.

**b) Re-coding accuracy — manual blind audit.** **[[n]]** `GW-OTHER` tickets, sampled stratified to oversample hard cases (short notes, notes with no obvious keyword), labelled by hand **before** the tool's output was seen, with all few-shot/example tickets excluded. Result: **[[x/n]]** exact agreement on reason code. At n=40 the 95% confidence interval is roughly ±10 points, so this is a **manual validation sample, not a precision estimate**.

**c) Replacement extraction vs the structured flag.** The tool reads replacement evidence from note text; the export also has a `replacement_issued` column. These are compared as two independent signals — **the column is not treated as ground truth**, because 91 refund tickets have the flag at `N` while the note says a unit was sent. Disagreements go to `replacement_double_comp_candidates.csv` for human review rather than being silently resolved.

**Known failure modes:**
- **Refund chases.** "Where is my money" tickets restate an earlier refund and often state no reason. The tool abstains rather than guessing.
- **Very short notes.** 68 of 991 `GW-OTHER` notes (6.9%) are ≤30 characters — `cx ok`, `see prev`, `as discussed`, `closed`. These are genuinely unclassifiable from text.
- **Fault cases.** Dead-on-arrival vs warranty buy-back is the hardest boundary; both look like "product broken" in free text, and the policy distinguishes them by delivery date, which the export does not contain.
- **Cross-validation caveat.** The 5-fold CV figure of **[[x%]]** measures agreement with the agents' *original dropdown picks* on non-`GW-OTHER` refunds. Those picks are the thing I am arguing is unreliable, so this is a sanity check that the text carries signal — **not an accuracy figure for the re-coding task.**

---

**4. Did you change, narrow, or push back on the client's ask?**

Three times.

**I contradicted the premise.** Arjun's email says refunds have gone up and he can't see why. Refund *spend* has gone up 2.1× — but the refund *rate* is flat: 20.1% of tickets in Q1 2025, 20.8% in Q2 2026. Tickets went from ~351/month to ~759/month. Refunds rose because the business grew. Saying so mattered more than producing the requested chart, because the implied remedy — tighten up refunds — would have been aimed at a problem that isn't there.

**I declined to rank agents on refund spend.** He asked "who is giving away money". I built the by-agent table he asked for, but refused to present it as a performance ranking: Vireo's own policy §6 says the Returns Desk processes the large majority of refunds *by design*, and that Tier 2 agents must not be compared with Tier 1 on volume metrics. A raw ranking would have put people doing their assigned job at the top of a list that reads as a leak. I substituted a policy-breach view — double compensation, goodwill above cap — which answers the same question defensibly.

**I moved the headline.** The obvious story was "Rs 2.4M breached the Rs 500 goodwill cap". It was wrong: most `GW-OTHER` refunds are not goodwill, so no cap applies. Only 42 refunds in 18 months are genuine goodwill, Rs 137,165 above cap total. I replaced it with the refund-plus-replacement finding, which is 3–5× larger and rests on an unambiguous policy rule.

---

**5. What is wrong with what you are handing us?**

- **The CV number is the weakest thing in the pack.** See Q3 — it validates against labels I argue are unreliable. It should be read as "the text carries signal", nothing more.
- **The manual audit is small.** **[[n]]** tickets on a 991-ticket bucket. Directionally sound, not a precision claim.
- **`days_since_order` is unreliable and I do not use it for any decision.** 222 tickets (3% of those that join to an order) were created *before* their order date — median 9 days before, worst case 448. Customer IDs match and order IDs are unique, so it is not a join error. The field is context only.
- **34% of tickets (3,899 of 11,600) do not join to an order at all**, so anything order-derived covers two-thirds of the data.
- **The Rs 79,000–153,000 quarterly figure is a range, not a point.** Which side is the loss depends on whether the refund or the replacement was the error, and the export does not say. I did not pick a number I could not defend.
- **I have not verified that the 257 double-compensation cases were never escalated.** The export has no escalation field. Policy requires same-day escalation; I am asserting the events happened, not that nobody acted on them.
- **Agents' `GW-OTHER` picks are treated as noise throughout.** If some agents use it deliberately for a reason I have not understood, part of the re-coding is wrong in a way my validation would not catch.
- **[[Any bug you know about in the tool — put it here. This box can only raise your score.]]**

---

**6. What did you deliberately leave out, and why that rather than something else?**

- **An LLM-per-ticket classifier.** Built the prompt, costed it, dropped it. It would have read the notes better than TF-IDF, but it needs API keys and a network, and the brief requires a clean-machine run from the README. I kept the prompt in the repo as a discarded artifact.
- **Anything about CSAT, first-contact resolution, SLA breach credits, or channel cost.** The policy defines all of them and the data supports all of them. Arjun asked about refunds. The Rs 350 SLA breach credit in particular looks like a second, separate leak — I flagged it (Q7) rather than analysing it.
- **Customer-level and product-level refund analysis.** Interesting, not asked for.
- **The timezone correction.** Policy §9 warns that migrated tickets' timestamps were reconstructed from a UTC event log. I checked it against the 638 duplicate pairs: they match to the second, with no offset. **Applying the documented +5:30 "fix" would have introduced a 5.5-hour error into every migrated handle time.** I left the timestamps alone and wrote down why.
- **A dashboard or UI.** CSV outputs plus a QA report. A board pack is a static artifact; a UI would have cost build time and delivered nothing Arjun asked for.

---

**7. Anything you built or found that nobody asked for?**

- **The paise bug.** Legacy refund amounts are in paise. Nobody flagged it; the export gives no hint. Uncorrected, refunds read as Rs 230M instead of Rs 6.71M — and the apparent 98% "collapse" in Oct 2025 is just the month the new helpdesk went live.
- **638 double-counted tickets** from the reconciliation re-import, inflating every total by ~5%.
- **The flat refund rate** — the answer to the actual question in Arjun's email, which was not what he asked me to produce.
- **222 impossible order dates** (ticket created before the order existed).
- **91 tickets where `replacement_issued = N` but the note says a unit was sent** — so the structured flag under-reports double compensation by 35%. Every one of a 14-ticket manual sample was a genuine case.
- **The Rs 350 SLA breach credit (policy §3) is issued automatically on every missed first response, regardless of cause.** Not analysed, but on this ticket volume it is worth a look as a separate piece of work.

---

**8. What did you use AI for? Which tools and models, where they helped, where they wasted your time, what you threw away.**

**[[Verify this against what you actually did — I can only see the Claude side of it.]]**

| Tool | Used for | Verdict |
|---|---|---|
| ChatGPT (GPT-5.6) | Analysis, code drafting, review of the classifier design | **[[your assessment]]** |
| Claude (Opus 5, and Sonnet 5.5 for part of the session) | Data forensics and challenge. Found the paise bug, the 638 duplicates, the flat refund rate, the `GW-OTHER` mis-tagging, the 222 impossible order dates, the negation problem in replacement detection. Also caught two wrong numbers in my own draft submission before it shipped. | **[[your assessment]]** |
| scikit-learn (local) | The shipped TF-IDF + logistic-regression classifier | No API calls, Rs 0 |

**Cost: Rs 0 in API spend for the tool itself. [[Add your subscription costs if you want to be thorough.]]**

**Where AI wasted time:** both assistants produced confidently wrong numbers that survived until I re-ran them. One told me to delete a correct percentile figure because it had computed its own version on the un-deduplicated export — the exact defect we had already agreed to correct. The working rule I ended up with: **any number either model hands you gets re-run against the raw file before it ships.** Two figures in my near-final draft were wrong for this reason and were caught this way.

**What I threw away:**
- The LLM-per-ticket classifier (prompt kept in repo, see Q6).
- A broad open-ended "true refund driver" classifier — too vague to validate inside the time budget. Narrowed to two concrete questions: re-code `GW-OTHER`, and detect refund-plus-replacement.
- A "Rs 2.4M breached the goodwill cap" headline, which was wrong (see Q4).
- A keyword-only rule baseline — kept as the comparison floor, not as the classifier. It left 359 of 991 notes uncoded.

**Screen recording:** **[[link]]**

---

**9. Your Public Google Drive Link**

**[[link — test it in a private browser window]]**

---

**10. Someone picks this up on Monday and you are unreachable. The three things they need to know.**

1. **Legacy refund amounts are in paise; divide by 100.** Proof, not assumption: on the 125 duplicate tickets carrying a refund, the legacy value is exactly 100× the helpdesk value, SD 0.00. Skip this and every refund total is 34× too high.
2. **Deduplicate on `ticket_id`, keeping the `helpdesk` row.** 638 tickets appear in both systems. The pairs agree on every field, so either row is fine, but they must not both be counted.
3. **`GW-OTHER` is a dropdown default, not a spend category.** 42.4% of refunds carry it, and most are duplicate payments, cancellations or completed returns. Do not report it as goodwill, and do not let anyone build a board narrative on it. Genuine goodwill is 38 tickets in 18 months.

---

**11. Honest hours spent.** **[[one number]]**

---

**12. GitHub Repo Link (Public)**

**[[link — open it logged out and confirm the README renders and the CSV paths are right]]**
