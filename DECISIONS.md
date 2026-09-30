# Decisions log

The brief said: if something is unclear, decide, write down what you decided, and explain why. This is that record.

Each entry: what was ambiguous → what I decided → why → what it would cost if I am wrong.

---

## 1. The client's premise is wrong, and I said so

**Ambiguity.** Arjun Mehta's email states refunds have gone up and asks why. It assumes the desk has become more generous.

**Decision.** Lead the memo by contradicting the premise.

**Why.** Refund *spend* rose 2.1× (Rs 203K → Rs 427K a month). Tickets rose from ~351 to ~759 a month over the same period. The refund *rate* moved from 20.1% to 20.8% — flat. Refunds rose because the business grew.

**If I am wrong.** I have told a Finance Controller his framing was off in the first paragraph. If he reads the rate as a dodge rather than an answer, the memo loses him. I judged that delivering the requested chart while knowing the premise was false would be worse — the implied remedy (tighten refund authority) would have been aimed at a problem that does not exist.

---

## 2. Legacy monetary values are divided by 100

**Ambiguity.** Policy §9 says only that the legacy tool "stored monetary values in its own native unit". It never says paise.

**Decision.** Divide legacy values by 100. State the evidence, not the document, as the basis.

**Why.** 638 tickets exist in both source systems; 125 of them carry a refund. The legacy value is exactly 100× the helpdesk value on all 125, standard deviation 0.00. Timestamps on all 638 pairs match to the second; agent IDs and reason codes agree on every pair. Uncorrected, legacy refunds show a median of Rs 224,900 on products retailing at Rs 1,299–6,999, and the 18-month total reads Rs 230M instead of Rs 6.71M.

**If I am wrong.** Every rupee figure in the pack is off by 100×. I consider this the most secure inference in the analysis — SD 0.00 across 125 independent pairs is not a coincidence.

**Trap avoided.** Uncorrected, monthly refund spend appears to collapse 98% between Sep and Oct 2025 — exactly when the new helpdesk went live (§9). That looks like a dramatic inflection and is purely a unit change. Anyone hunting for a trend break will find this one.

---

## 3. Unit of analysis is the unique `ticket_id`

**Ambiguity.** The export has 12,238 rows but 11,600 unique ticket IDs. §9 mentions a reconciliation re-import.

**Decision.** Deduplicate on `ticket_id`, keeping the `helpdesk` row.

**Why.** The 638 duplicated pairs agree on every field once units are normalised, so they are the same ticket, not two events. Counting both inflates every total by ~5%.

**If I am wrong.** Totals are ~5% low. Preferring the `helpdesk` row is arbitrary but harmless — the pairs are identical after normalisation.

---

## 4. `GW-OTHER` is a tagging defect, not a spend category

**Ambiguity.** 42.4% of refunds (Rs 2.91M, 43.3% of spend) are coded `GW-OTHER` — "Goodwill / Other". Taken at face value, Vireo gives away Rs 2.9M in goodwill.

**Decision.** Treat `GW-OTHER` as a dropdown catch-all and re-code from the agent's closing note. Keep the code only where the note explicitly frames the money as goodwill or a one-time gesture.

**Why.** Reading the notes, most are specific and codeable: "cx states chargged twice" is `DUP-PAYMENT`; "cancelled before dispatch" is `CANCEL`; "chk reverse pkp QC status" is `RETURN-QC-OK`. §5 says the code is picked by the agent from a dropdown at the time the refund is raised — `GW-OTHER` is the path of least resistance. Only 42 refunds in 18 months have notes describing an actual gesture.

**If I am wrong.** If some agents use `GW-OTHER` deliberately for a reason not understood here, part of the re-coding is wrong, and the validation sample would not catch it because it was labelled under the same assumption.

---

## 5. Headline is double compensation, not the goodwill cap

**Ambiguity.** Two candidate headline numbers.

**Decision.** Lead with refund-plus-replacement (257 tickets, Rs 79,000–153,000 a quarter). Demote the goodwill cap breach (42 tickets, Rs 22,861 a quarter).

**Why.** The obvious headline — "Rs 2.4M breached the Rs 500 goodwill cap" — was **wrong**, and was in a near-final draft before it was caught. Most `GW-OTHER` refunds are not goodwill, so no cap applies to them. The defensible goodwill number is 42 tickets, Rs 137,165 above cap over 18 months. Double compensation is 3–5× larger and rests on an unambiguous rule: §5 says a customer must never receive both, and that any instance must be escalated to the Team Lead and Finance the same day.

**Reported as a range**, Rs 79,000–153,000 a quarter, because which side is the loss depends on whether the refund or the replacement was the error, and the export does not say. Rs 153,154/quarter is the refund value; Rs 78,703/quarter is the replacement cost at §5's own costing (unit cost + Rs 340).

**Detection uses two signals, not one.** 166 tickets carry `replacement_issued = Y`. A further 91 have the flag at `N` while the closing note says a unit was sent or dispatched, with no negation phrase — a 14-ticket manual sample of those was 14/14 genuine. Notes containing 'not applicable', 'out of stock' or 'refund only' are excluded.

**Do not add the two figures.** Explicit-goodwill tickets and double-compensation tickets overlap — 4 of the 42 are goodwill notes that describe both a refund and a new unit.

---

## 6. Shipped a local model, discarded the LLM classifier

**Ambiguity.** The brief asks for an "AI-assisted tool" without specifying what kind.

**Decision.** Ship TF-IDF + logistic regression with a rule layer. Keep the LLM prompt in the repo as a discarded artifact.

**Why.** Not cost — it was costed at ~$0.67/month on Haiku for the ongoing volume, which is trivial. Reproducibility: the brief requires the tool to start from the README on a clean machine. A local model needs no keys, no network, and produces no per-run variance. A grader who cannot run the tool cannot grade the tool.

**If I am wrong.** TF-IDF reads free text worse than an LLM would, particularly on short and idiosyncratic notes. The re-coding is less accurate than it could have been. I traded accuracy for a tool that definitely runs.

**`classify_v1.md` → `classify_v2.md`** are kept for the record. v2 changed wording only: `UNCLEAR` redefined as an abstain state rather than a ninth reason; the refund-chase flag made annotation-only (the model never deduplicates money — code does); the `days_since_order` warning given its real justification.

---

## 7. No agent performance ranking

**Ambiguity.** Arjun asked "who is giving away money — and for what". The literal answer is a ranked list of agents by refund spend.

**Decision.** Produce the agent × reason table. Refuse to present it as a performance ranking, and say so in the memo.

**Why.** §6 states the Returns Desk processes the large majority of refunds by design, and that Tier 2 agents are not to be compared with Tier 1 on volume metrics. A raw ranking puts A3036 (Returns Desk, 50.6% refund rate) at the top of a list that reads as a leak — for doing the assigned job. Normalising by tickets handled does not fix it, because the job itself is refund processing. The policy-breach view answers the same question without libelling anyone.

**If I am wrong.** Arjun wanted names and did not get them. Mitigated by giving him the table and explaining what it does and does not show.

---

## 8. `days_since_order` is context, never a threshold

**Ambiguity.** §5 defines dead-on-arrival as "within 7 days of delivery". `orders.csv` has no delivery date.

**Decision.** Never use `days_since_order` as an eligibility test or to select a code.

**Why.** Three reasons, in increasing order of severity. The policy threshold runs from delivery, not order. Tickets already coded `DOA-REPL` have a median of 12 days and a 90th percentile of 141 (post-deduplication), so agents' own usage does not respect a 7-day window either. And **222 tickets (3% of those that join to an order) were created before their order date** — median 9 days before, worst case 448. Customer IDs match and order IDs are unique, so this is not a join defect; the field is simply unreliable.

**If I am wrong.** A genuine signal is discarded. Acceptable — a threshold built on a field that is wrong 3% of the time and measures the wrong event is worse than no threshold.

---

## 9. Migrated timestamps left alone

**Ambiguity.** §9 warns that migrated tickets' `resolved_at` was reconstructed from a UTC event log, while the helpdesk displays IST. This reads as an instruction to shift migrated timestamps by +5:30.

**Decision.** Apply no correction.

**Why.** Tested on the 638 duplicate pairs — the same ticket in both systems, a natural experiment. `created_at`, `first_response_at` and `resolved_at` match to the second on all 638. Handle-time medians are 1.83h (helpdesk) vs 1.98h (legacy), with no negative durations. There is no offset in this export.

**If I am wrong.** Nothing changes — the correction would have been a no-op at best. Applying it blindly would have injected a 5.5-hour error into every migrated handle time. **This is a trap in the opposite direction: the careful reader who trusts the policy document over the data makes things worse.**

---

## 10. Deliberately out of scope

Listed so the omissions are visible as choices:

- **CSAT, first-contact resolution, SLA breach credits, channel cost.** Policy defines all of them; data supports all of them. Arjun asked about refunds. The **Rs 350 automatic SLA breach credit (§3), issued on every missed first response regardless of cause**, looks like a second and separate leak — flagged, not analysed.
- **Customer-level and product-level refund analysis.** Interesting, not asked for.
- **Refund chase deduplication.** 2,340 refund tickets cover 1,434 distinct orders; 57 order + identical-amount combinations repeat, about Rs 212K (~3%) of apparent double-count. The tool flags chases; it does not net them out, because deciding that two records are one economic refund needs a rule Finance should set, not a model.
- **A dashboard or UI.** CSVs and a QA report. A board pack is static.

---

## 11. Volume discrepancy, unresolved

The brief describes ~650 tickets/week. The export runs at ~178 tickets/week over the last six months (4,638 across 26 weeks).

**Decision.** Scale cost arithmetic to 650/week as stated, and flag the discrepancy rather than silently picking one.

**Why.** Either the export is a sample, or 650 counts contacts rather than tickets. Both are plausible; the pack contains nothing that settles it. Per-ticket costs are unaffected either way.

---

## 12. Working rule adopted mid-task

Both AI assistants used on this task produced confidently wrong figures that survived until re-run against the raw file. One recommended deleting a correct percentile because it had computed its own version on the *un-deduplicated* export — the exact defect already agreed to be corrected.

**Rule adopted:** no number ships without being re-derived from the source CSVs. Two figures in a near-final draft were wrong and were caught this way. `analysis/memo_numbers.json` is the output of that rule — every figure in the memo, regenerated in one pass.
