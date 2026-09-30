# prompts/ — DISCARDED APPROACH

These are kept deliberately. They are **not** used by the shipped tool.

`classify_v1.md` — the original LLM-per-ticket classifier for re-coding the 991 GW-OTHER
tickets: system prompt plus nine few-shot examples taken verbatim from the export.

`classify_v2.md` — the same, revised. Wording only, no change to the schema or label set:
UNCLEAR redefined as an abstain state rather than a ninth reason; the refund-chase field made
annotation-only; the `days_since_order` warning given its real justification.

`fewshot_ids_exclude_from_validation.txt` — the nine example ticket IDs. They must never appear
in the gold set; `validate.py` enforces this.

**Why this was discarded:** not cost (~$0.67/month on Haiku at Vireo's volume). Reproducibility.
The brief requires the tool to run from the README on a clean machine, and a local model needs
no API keys, no network and has no per-run variance. See DECISIONS.md §6.
