#!/usr/bin/env python3
"""
Scores the tool's GW-OTHER re-coding against a hand-labelled gold set.

Reports three things separately, because they measure different things:
  1. Reason-code agreement vs. human labels  (the headline number)
  2. Replacement extraction vs. human labels, AND vs. the structured flag
  3. Where it fails -- confusion pairs and per-stratum breakdown

Deliberately reports a confidence interval. At n=40 the interval is roughly
+/-10 points, and a single number would overstate what the sample supports.

Usage:
    python validation/validate.py \
        --gold validation/gold_sample.csv \
        --audit outputs/refund_recode_audit.csv
"""
import argparse, sys
import pandas as pd
import numpy as np

# Column names in the audit file. Override from the CLI if the tool uses others.
DEFAULTS = dict(pred_code="final_reason_code",
                pred_repl="replacement_given",
                pred_conf="confidence")


def wilson(k, n, z=1.96):
    """Wilson score interval -- honest at small n, unlike the normal approximation."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z**2 / n
    c = (p + z**2 / (2*n)) / d
    h = z * np.sqrt(p*(1-p)/n + z**2/(4*n**2)) / d
    return (max(0.0, c-h), min(1.0, c+h))


def band(k, n, label):
    lo, hi = wilson(k, n)
    return f"{label}: {k}/{n} = {k/n*100:.1f}%  (95% CI {lo*100:.1f}-{hi*100:.1f}%)" if n else f"{label}: no rows"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", default="validation/gold_sample.csv")
    ap.add_argument("--audit", default="outputs/refund_recode_audit.csv")
    ap.add_argument("--pred-code", default=DEFAULTS["pred_code"])
    ap.add_argument("--pred-repl", default=DEFAULTS["pred_repl"])
    ap.add_argument("--pred-conf", default=DEFAULTS["pred_conf"])
    ap.add_argument("--fewshot", default="prompts/fewshot_ids_exclude_from_validation.txt")
    a = ap.parse_args()

    gold = pd.read_csv(a.gold, dtype={"ticket_id": str})
    audit = pd.read_csv(a.audit, dtype={"ticket_id": str})

    if "true_code" not in gold.columns:
        sys.exit(f"ERROR: {a.gold} has no 'true_code' column. Label it by hand first.")
    unlabelled = gold.true_code.isna().sum() + (gold.true_code.astype(str).str.strip() == "").sum()
    if unlabelled:
        sys.exit(f"ERROR: {unlabelled} of {len(gold)} gold rows are unlabelled. "
                 "Label every row before scoring -- a partial gold set silently biases the result.")

    # Contamination guard: few-shot/example tickets must not be scored.
    try:
        excl = set(open(a.fewshot).read().split())
        overlap = set(gold.ticket_id) & excl
        if overlap:
            sys.exit(f"ERROR: {len(overlap)} gold tickets are also prompt examples: {sorted(overlap)}. "
                     "Remove them -- scoring on them inflates the result.")
    except FileNotFoundError:
        print(f"[warn] {a.fewshot} not found; skipping contamination check.", file=sys.stderr)

    if a.pred_code not in audit.columns:
        sys.exit(f"ERROR: '{a.pred_code}' not in {a.audit}. Columns: {list(audit.columns)}\n"
                 "Pass the right one with --pred-code.")

    m = gold.merge(audit, on="ticket_id", how="left", suffixes=("", "_audit"))
    missing = m[a.pred_code].isna().sum()
    if missing:
        print(f"[warn] {missing} gold tickets absent from the audit file -- counted as errors.\n")

    print("=" * 66)
    print("VALIDATION REPORT")
    print("=" * 66)
    print(f"gold set : {a.gold}  (n={len(gold)})")
    print(f"tool out : {a.audit}")
    print("\nThis is a manual validation sample, not a precision estimate.\n")

    # --- 1. reason code -------------------------------------------------
    print("-" * 66)
    print("1. REASON CODE AGREEMENT")
    print("-" * 66)
    ok = (m[a.pred_code].fillna("__MISSING__").str.strip().str.upper()
          == m.true_code.str.strip().str.upper())
    print(band(int(ok.sum()), len(m), "  exact agreement"))

    # Abstention is a feature, so separate "wrong" from "declined".
    pred_unclear = m[a.pred_code].fillna("").str.strip().str.upper().eq("UNCLEAR")
    true_unclear = m.true_code.str.strip().str.upper().eq("UNCLEAR")
    decided = ~pred_unclear
    if decided.sum():
        print(band(int(ok[decided].sum()), int(decided.sum()),
                   "  agreement where the tool committed to a code"))
    print(f"  tool abstained: {int(pred_unclear.sum())}  |  human judged unclear: {int(true_unclear.sum())}")
    over = int((pred_unclear & ~true_unclear).sum())
    under = int((~pred_unclear & true_unclear).sum())
    print(f"  over-abstention (tool unsure, human sure): {over}   <- costs coverage, not correctness")
    print(f"  under-abstention (tool sure, human unsure): {under}  <- the dangerous direction")

    if (~ok).any():
        print("\n  confusion pairs (true -> predicted):")
        for (t, p), n in (m[~ok].groupby([m.true_code, m[a.pred_code].fillna("MISSING")])
                          .size().sort_values(ascending=False).items()):
            print(f"    {str(t):>14s} -> {str(p):<14s} {n}")

    if "stratum" in m.columns:
        print("\n  by stratum (the sample oversamples hard cases on purpose):")
        for s, g in m.groupby("stratum"):
            print("    " + band(int(ok[g.index].sum()), len(g), f"{s:<14s}"))

    if a.pred_conf in m.columns:
        print("\n  by tool confidence (high should beat low -- if not, confidence is noise):")
        for c, g in m.groupby(m[a.pred_conf]):
            print("    " + band(int(ok[g.index].sum()), len(g), f"{str(c):<14s}"))

    # --- 2. replacement -------------------------------------------------
    print("\n" + "-" * 66)
    print("2. REPLACEMENT EXTRACTION")
    print("-" * 66)
    if "true_replacement_given" in m.columns and a.pred_repl in m.columns:
        t = m.true_replacement_given.astype(str).str.strip().str.lower()
        p = m[a.pred_repl].astype(str).str.strip().str.lower()
        v = t.isin(["yes", "no", "unclear"])
        print(band(int((t[v] == p[v]).sum()), int(v.sum()), "  tool vs human"))

        if "replacement_issued" in m.columns:
            flag = m.replacement_issued.astype(str).str.strip().str.upper().map({"Y": "yes", "N": "no"})
            vf = v & flag.notna()
            print(band(int((t[vf] == flag[vf]).sum()), int(vf.sum()), "  structured flag vs human"))
            print("\n  The structured flag is an independent signal, NOT ground truth:")
            print(f"    flag=N but human says a replacement was given: {int(((flag=='no') & (t=='yes')).sum())}")
            print(f"    flag=Y but human says none was given:          {int(((flag=='yes') & (t=='no')).sum())}")
    else:
        print("  skipped -- needs 'true_replacement_given' in gold and "
              f"'{a.pred_repl}' in the audit file.")

    # --- 3. chase -------------------------------------------------------
    print("\n" + "-" * 66)
    print("3. REFUND-CHASE ANNOTATION")
    print("-" * 66)
    chase_col = next((c for c in ("is_refund_chase", "refund_chase") if c in m.columns), None)
    if "true_is_chase" in m.columns and chase_col:
        norm = lambda s: s.astype(str).str.strip().str.lower().map(
            {"true": "yes", "yes": "yes", "y": "yes", "1": "yes",
             "false": "no", "no": "no", "n": "no", "0": "no"})
        t, p = norm(m.true_is_chase), norm(m[chase_col])
        v = t.notna() & p.notna()
        print(band(int((t[v] == p[v]).sum()), int(v.sum()), "  tool vs human"))
        print("  Annotation only -- it never nets money out of a total.")
    else:
        print("  skipped -- needs 'true_is_chase' in gold and a chase column in the audit file.")

    print("\n" + "=" * 66)
    print("Report all three numbers separately. A single headline accuracy")
    print("figure hides which of the three is actually weak.")
    print("=" * 66)


if __name__ == "__main__":
    main()
