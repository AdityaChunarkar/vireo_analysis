# validation/

`gold_sample_blank.csv` — the blind worksheet. 40 GW-OTHER tickets, stratified to oversample
hard cases (12 short notes, 16 with no obvious keyword, 12 clear), shuffled so the strata are
not visible while labelling. Contains no reason code and no tool output.

**Label this before running the tool on it.** Fill `true_code`, `true_replacement_given` and
`true_is_chase`, then save as `gold_sample.csv`.

`gold_sample.csv` — the labelled version. Scored against, never trained on.

`validate.py` — scores tool output against the gold set:

    python validation/validate.py --gold validation/gold_sample.csv --audit outputs/refund_recode_audit.csv

It refuses to run if any gold row is unlabelled, or if a gold ticket also appears in
`prompts/fewshot_ids_exclude_from_validation.txt`. Both would inflate the result silently.

If your audit file uses different column names, pass `--pred-code`, `--pred-repl`, `--pred-conf`.
