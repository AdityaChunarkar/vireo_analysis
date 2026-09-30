# Vireo Audio — Refund Analysis Tool

Turns the raw helpdesk export into a board-ready refund view: monthly refunds by reason code, by agent, and by agent × reason, plus two policy-control reports and a per-ticket audit trail.

**The headline finding is in [`memo/memo_to_arjun.md`](memo/memo_to_arjun.md). Read that first if you are not running the code.**

---

## Why this tool exists rather than a pivot table

The export cannot be summarised as-is. Three defects have to be corrected before any total is meaningful:

| Defect | Effect if uncorrected |
|---|---|
| Legacy refund amounts stored in **paise**, not rupees | 18-month refund total reads **Rs 230M** instead of **Rs 6.71M** |
| **638 tickets duplicated** across both source systems | Every total inflated by ~5% |
| **42.4% of refunds tagged `GW-OTHER`** ("Goodwill / Other") | Nearly half the reason breakdown says "other" |

The first two are deterministic fixes. The third is the part that needs a model: `GW-OTHER` is a dropdown catch-all, and the real reason is only in the agent's free-text closing note.

---

## Clean-machine run

Requires Python 3.9+.

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate
# Windows PowerShell
.venv\Scripts\Activate.ps1

python -m pip install -r requirements.txt
```

Place the five source CSVs in `data/` (they are **not** in this repo — client data):

```
data/tickets.csv
data/agents.csv
data/orders.csv
data/customers.csv
data/products.csv
```

Then:

```bash
python refund_tool.py --data-dir data --out-dir outputs
```

No API keys. No network access. No credentials of any kind.

### Outputs written to `outputs/`

| File | Contents |
|---|---|
| `refund_monthly_by_reason.csv` | Monthly totals by final reason code |
| `refund_monthly_by_agent.csv` | Monthly totals by agent and final reason |
| `refund_agent_reason.csv` | Agent × reason board-pack table |
| `refund_reason_summary.csv` | Overall reason summary |
| `refund_recode_audit.csv` | Every refund ticket: original reason, final reason, confidence, source text |
| `replacement_double_comp_candidates.csv` | Refund + replacement cases for human review |
| `qa_summary.md` / `qa_summary.json` | Control totals and model checks |
| `agent_roster.csv` | Roster copy for filtering |

---

## Repository layout

```
vireo-refund-analysis/
├── README.md                      you are here
├── DECISIONS.md                   every judgment call, with the reason
├── refund_tool.py                 the pipeline (single entry point)
├── requirements.txt
├── .gitignore
│
├── memo/
│   └── memo_to_arjun.md           the one-page memo — the actual deliverable
│
├── analysis/
│   ├── refund_analysis.py         exploratory analysis behind the memo
│   └── memo_numbers.json          every figure in the memo, machine-readable
│
├── prompts/
│   ├── classify_v1.md             DISCARDED LLM classifier — kept as evidence
│   ├── classify_v2.md             DISCARDED, revised — see DECISIONS.md §6
│   └── fewshot_ids_exclude_from_validation.txt
│
├── validation/
│   ├── gold_sample_blank.csv      blind worksheet: 40 tickets, no labels
│   ├── gold_sample.csv            the same 40, hand-labelled
│   └── validate.py                scores tool output against the gold set
│
├── outputs/                       generated — sample_report.csv committed as an example
└── data/                          source CSVs go here (gitignored)
```

---

## Decisions that change the numbers

Full reasoning in [`DECISIONS.md`](DECISIONS.md). The four that matter most:

1. **Unit of analysis is the unique `ticket_id`,** keeping the `helpdesk` row where a ticket exists in both systems. 638 tickets are affected.

2. **Legacy monetary values are divided by 100.** The policy says only that the legacy tool stored values in "its own native unit" — it does not say paise. The correction rests on evidence, not on the document: across the 125 duplicated tickets that carry a refund, the legacy value is **exactly 100× the helpdesk value, standard deviation 0.00**. Timestamps on all 638 pairs match to the second and agent and reason fields agree on every pair, so the pairs are genuine duplicates.

3. **`GW-OTHER` is treated as a dropdown default, not a spend category.** Tickets whose notes explicitly say "goodwill" or "one-time gesture" keep the code. The rest are re-coded from text.

4. **No agent performance ranking is produced.** Policy §6 states the Returns Desk processes the large majority of refunds *by design* and that Tier 2 agents are not to be compared with Tier 1 on volume metrics. The agent × reason table exists; it is deliberately not a leaderboard.

### Fields the tool does not trust

- **`days_since_order`** — context only, never a threshold. The policy's DOA window runs from *delivery* date, which this export does not contain; and 222 tickets (3% of those that join to an order) were created **before** their order date, worst case 448 days. Customer IDs match and order IDs are unique, so this is not a join defect.
- **`replacement_issued`** — an independent structured signal, **not ground truth**. 91 refund tickets carry `N` while the closing note says a unit was sent or dispatched, so the flag alone under-reports double compensation by 35% (166 flagged vs 257 detected).
- **Migrated timestamps** — policy §9 warns these were reconstructed from a UTC event log. Checked against the 638 duplicate pairs: they match to the second, with no offset. **No correction is applied.** Applying the documented +5:30 "fix" would inject a 5.5-hour error into every migrated handle time.

---

## Validation

```bash
python validation/validate.py --gold validation/gold_sample.csv --audit outputs/refund_recode_audit.csv
```

Three independent checks, reported separately because they measure different things:

1. **Unit correction** — proved on the 125 paired refunds (exact 100×, SD 0.00). Deterministic, not estimated.
2. **Re-coding agreement** — 40 `GW-OTHER` tickets, stratified to oversample hard cases (notes ≤30 characters, notes with no obvious keyword), hand-labelled **before** the tool's output was seen, with all few-shot example IDs excluded. At n=40 the 95% interval is roughly ±10 points, so this is a **manual validation sample, not a precision estimate**.
3. **Replacement extraction** — compared against the `replacement_issued` column as two independent signals. Disagreements are written to `replacement_double_comp_candidates.csv` for human review, never silently resolved.

**The cross-validation figure is the weakest number in this repo.** It measures agreement with the agents' *original dropdown picks* on non-`GW-OTHER` refunds — the very labels this tool argues are unreliable. Read it as "the text carries signal", not as accuracy.

**Before any policy or personnel decision:** inspect the low-confidence rows in `refund_recode_audit.csv` and every row of `replacement_double_comp_candidates.csv` by hand.

---

## AI use and cost

| Tool | Used for |
|---|---|
| **Claude (Opus 5; Sonnet 5.5 for part of the session)** | Data forensics and challenge — found the paise bug, the 638 duplicates, the flat refund rate, the `GW-OTHER` mis-tagging, the 222 impossible order dates, and the negation problem in replacement detection. Caught two wrong figures in a near-final draft. |
| **ChatGPT (GPT-5.6)** | Analysis, code drafting, review of the classifier design |
| **scikit-learn (local)** | The shipped TF-IDF + logistic-regression classifier |

**The tool makes no API calls. One run costs Rs 0.**

The LLM alternative was costed before being discarded: ~2,500 input + ~60 output tokens per ticket, 242 `GW-OTHER` tickets a month at 650 tickets/week ≈ **$0.67/month on Haiku 4.5** or **$2.02/month on Sonnet 4.5**. Cost was never the reason it was dropped — reproducibility was. A local model runs from this README on a clean machine with no keys and no per-run variance.

**Discarded:** the LLM-per-ticket classifier (`prompts/classify_v1.md`, `classify_v2.md`, kept deliberately), a broad open-ended "true refund driver" classifier, a keyword-only baseline (left 359 of 991 notes uncoded — kept as the comparison floor), and a "Rs 2.4M breached the goodwill cap" headline that turned out to be wrong.

---

## Known limitations

- 34% of tickets (3,899 of 11,600) do not join to an order, so order-derived fields cover two-thirds of the data.
- The quarterly figure for double compensation is a **range** (Rs 79,000–153,000), because the export does not say whether the refund or the replacement was the error.
- The export has no escalation field, so the tool cannot confirm whether the 166 double-compensation cases were escalated as policy requires.
- Agents' `GW-OTHER` picks are treated as noise throughout. If some agents use the code deliberately for a reason not understood here, part of the re-coding is wrong in a way the validation would not catch.
