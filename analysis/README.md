# analysis/

`refund_analysis.py` — the exploratory pass behind the memo. Not part of the pipeline;
`refund_tool.py` at the repo root is the single entry point for producing outputs.

`memo_numbers.json` — every figure quoted in `memo/memo_to_arjun.md`, regenerated in one
pass from the raw CSVs. If a number in the memo is questioned, it is here with the same key.
Regenerate with:

    python analysis/refund_analysis.py --data-dir data --out analysis/memo_numbers.json

## Run order

`refund_analysis.py` reads `outputs/refund_recode_audit.csv` for the goodwill figure so the
memo matches the pipeline exactly. Run the tool first:

    python refund_tool.py --data-dir data --out-dir outputs
    python analysis/refund_analysis.py --data-dir data --out analysis/memo_numbers.json

Without the audit file it falls back to a regex and says so in the output.
