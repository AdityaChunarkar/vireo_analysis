# Screen recording script — 3 minutes hard cap

**Format:** phone recording of your screen is explicitly fine. No slides. Talk over what's on screen.
**Cover exactly three things:** the prompts you used, what changed between versions, what you threw away.
**Do not:** re-explain the analysis. They read the memo. This is about *how you worked*.

Rehearse once, record once, keep the second take only if the first runs long.

---

## 0:00–0:25 — What you're looking at

> "Vireo's refund export, 12,000 rows. I'll show you three decisions: the prompt I wrote, what I changed, and what I deleted."

**On screen:** `tickets.csv` open, scrolled to the `refund_amount_inr` column with legacy rows visible.

> "First thing I did was not write a prompt. I looked at the money column. Legacy rows say 224,900 rupees on a pair of earbuds that retails for 2,499. That's paise. Uncorrected, refunds read as 230 million instead of 6.7 million."

**Why this opens the video:** it proves you read the data before you prompted anything. Strongest 25 seconds available to you.

---

## 0:25–1:15 — The prompts

**On screen:** `prompts/classify_v1.md`, scrolled to the RULES block.

> "The AI job I defined was narrow: 42% of refunds are tagged GW-OTHER, a dropdown catch-all. Re-code those 991 tickets from the agent's closing note."

Point at three specific lines as you say them:

> "Three things in the prompt I'd defend. One — the model never sees agent ID or the replacement flag, so agent-level reporting isn't contaminated and the flag stays an independent check. Two — it must quote verbatim evidence; if it can't quote, it abstains. Three — all arithmetic happens in Python, not in the model. The model extracts facts, code decides money."

**Then scroll to rule 7.**

> "And this one is the most important line in the file: days-since-order is context only, never a threshold. The policy's dead-on-arrival window runs from delivery date, which this export doesn't have — and 3% of order dates are *after* the ticket was created. That rule exists because I checked."

---

## 1:15–2:15 — What changed between versions

**On screen:** `classify_v1.md` and `classify_v2.md` side by side, or a diff.

> "v1 to v2 was wording, not architecture. UNCLEAR got redefined as an abstain state rather than a ninth reason. The refund-chase flag became an annotation — the model never gets to deduplicate money, code does that. And the threshold warning got the real reason attached."

**Then switch to the tool.**

> "The bigger version change is that v1 was an LLM-per-ticket classifier and I shipped a local TF-IDF model instead. Not on cost — I costed it, 242 tickets a month is about 60 rupees on Haiku. I dropped it because the brief says it has to run from the README on a clean machine. A local model has no keys, no network, no per-run variance."

**Run the tool. Let the terminal output be visible.**

> "That's the whole run. No API calls, no credentials."

---

## 2:15–2:50 — What you threw away

Say these fast, one line each, with the file or figure on screen:

> "Four things I deleted.
> A broad 'true refund driver' classifier — too vague to validate in the time.
> A headline that said 2.4 million rupees breached the goodwill cap. It was wrong: most GW-OTHER refunds aren't goodwill, so no cap applies. Real goodwill is 38 tickets in 18 months.
> A per-agent leaderboard. Policy says the Returns Desk processes most refunds by design and Tier 2 isn't comparable to Tier 1 — so a raw ranking punishes people for doing their job.
> And a timezone correction the policy document told me to make. I checked it against 638 duplicate tickets: timestamps match to the second. Applying the documented fix would have put a five-and-a-half hour error into every migrated handle time."

---

## 2:50–3:00 — Close

> "The number: 166 refunds also got a replacement for the same order, which policy says must never happen. Fifty to ninety-six thousand rupees a quarter. Sixty percent of them were hiding under GW-OTHER."

Stop recording. Do not add a summary.

---

## Checklist before you hit record

- [ ] Terminal font large enough to read on a phone screen
- [ ] The run actually works — do a dry run first, a failed demo is worse than no demo
- [ ] Close Slack, email, anything with notifications
- [ ] Time the rehearsal. If it's over 3:00, cut from section 3, not section 1
- [ ] Say numbers out loud as you point at them — don't make them squint

## If you overrun

Cut in this order:
1. The v1→v2 wording detail (0:15 saved)
2. The three prompt design choices, down to one (0:20 saved)
3. The timezone item from "what I threw away" (0:12 saved)

Never cut the paise opener or the final number.
