#!/usr/bin/env python3
"""Vireo Audio refund analysis tool.

Scope deliberately stays narrow:
1) de-duplicate tickets and fix the known legacy paise-unit mismatch;
2) re-code GW-OTHER using a local TF-IDF + logistic-regression classifier trained
   on the already-coded refund reasons, with a small rule layer for high-signal
   phrases and explicit goodwill;
3) flag possible refund+replacement double compensation from structured data and
   strong free-text evidence;
4) produce monthly / agent / reason summaries and a validation report.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import FeatureUnion


KNOWN_CODES = [
    "GW-OTHER",
    "DOA-REPL",
    "LOST-TRANSIT",
    "DUP-PAYMENT",
    "CANCEL",
    "PRICE-ADJ",
    "RETURN-QC-OK",
    "WTY-BUYBACK",
]
NON_GW_CODES = [c for c in KNOWN_CODES if c != "GW-OTHER"]


@dataclass
class Config:
    review_threshold: float = 0.55
    goodwill_patterns: tuple[str, ...] = (
        r"\bgoodwill\b",
        r"\bone[- ]time gesture\b",
        r"\breleased the money as well\b.*\bnew (?:unit|set)\b",
        r"\bsent a new unit\b.*\bin tears\b",
    )


def load_data(data_dir: Path) -> dict[str, pd.DataFrame]:
    files = {
        "tickets": data_dir / "tickets.csv",
        "agents": data_dir / "agents.csv",
        "orders": data_dir / "orders.csv",
        "customers": data_dir / "customers.csv",
        "products": data_dir / "products.csv",
    }
    missing = [str(p) for p in files.values() if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing files: " + ", ".join(missing))
    return {k: pd.read_csv(v) for k, v in files.items()}


def prepare_tickets(tickets: pd.DataFrame) -> pd.DataFrame:
    t = tickets.copy()
    for c in ["created_at", "first_response_at", "resolved_at"]:
        t[c] = pd.to_datetime(t[c], errors="coerce")
    t["refund_amount_inr"] = pd.to_numeric(t["refund_amount_inr"], errors="coerce")
    t["source_rank"] = t["source_system"].map({"helpdesk": 0, "legacy_fd": 1}).fillna(9)

    # Duplicate ticket IDs are migrated / re-imported pairs. Prefer the current
    # helpdesk copy because it stores rupees; legacy copies use the native unit.
    t = t.sort_values(["ticket_id", "source_rank"]).drop_duplicates("ticket_id", keep="first")
    legacy_only = t["source_system"].eq("legacy_fd")
    t["refund_amount_rupees"] = t["refund_amount_inr"]
    t.loc[legacy_only, "refund_amount_rupees"] = t.loc[legacy_only, "refund_amount_inr"] / 100.0
    t["refund_month"] = t["created_at"].dt.to_period("M").astype(str)
    t["text"] = t["customer_message"].fillna("") + "\n" + t["agent_notes"].fillna("")
    return t


def audit_duplicates(raw: pd.DataFrame) -> dict:
    dup = raw[raw["ticket_id"].duplicated(keep=False)].sort_values(["ticket_id", "source_system"])
    pair_ids = dup["ticket_id"].nunique()
    pairs = []
    for tid, g in dup.groupby("ticket_id"):
        if len(g) != 2:
            continue
        rows = {r["source_system"]: r for _, r in g.iterrows()}
        a = g.iloc[0]
        b = g.iloc[1]
        def eq_nan(x, y):
            if pd.isna(x) and pd.isna(y):
                return True
            return x == y
        ratio = None
        if "legacy_fd" in rows and "helpdesk" in rows:
            legacy_amt = rows["legacy_fd"]["refund_amount_inr"]
            helpdesk_amt = rows["helpdesk"]["refund_amount_inr"]
            if pd.notna(legacy_amt) and pd.notna(helpdesk_amt) and float(helpdesk_amt) != 0:
                ratio = float(legacy_amt) / float(helpdesk_amt)
        pairs.append({
            "ticket_id": tid,
            "created_equal": eq_nan(a["created_at"], b["created_at"]),
            "first_response_equal": eq_nan(a["first_response_at"], b["first_response_at"]),
            "resolved_equal": eq_nan(a["resolved_at"], b["resolved_at"]),
            "refund_ratio_legacy_to_helpdesk": ratio,
        })
    pair_df = pd.DataFrame(pairs)
    refund_pairs = pair_df[pair_df["refund_ratio_legacy_to_helpdesk"].notna()] if not pair_df.empty else pd.DataFrame()
    return {
        "duplicate_ticket_pairs": int(pair_ids),
        "timestamp_pairs_equal_all_non_null": bool(
            pair_df.empty or (
                pair_df[["created_equal", "first_response_equal", "resolved_equal"]]
                .fillna(True).all(axis=None)
            )
        ),
        "refund_pairs": int(len(refund_pairs)),
        "refund_ratio_unique": sorted(refund_pairs["refund_ratio_legacy_to_helpdesk"].unique().tolist()) if not refund_pairs.empty else [],
    }


def build_model(train_df: pd.DataFrame):
    vec = FeatureUnion([
        ("word", TfidfVectorizer(ngram_range=(1, 2), min_df=1, max_features=30000, sublinear_tf=True)),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2, max_features=30000, sublinear_tf=True)),
    ])
    X = vec.fit_transform(train_df["text"])
    clf = LogisticRegression(max_iter=2000, class_weight="balanced")
    clf.fit(X, train_df["refund_reason_code"])
    return vec, clf


def explicit_goodwill(text: str, cfg: Config) -> bool:
    return any(re.search(p, text.lower(), flags=re.DOTALL) for p in cfg.goodwill_patterns)


def rule_override(message: str, note: str, predicted: str, cfg: Config) -> tuple[str, str]:
    m = str(message or "")
    n = str(note or "")
    s = (m + "\n" + n).lower()

    if explicit_goodwill(s, cfg):
        return "GW-OTHER", "explicit_goodwill"
    if re.search(r"\b(charged twice|charged two times|double payment|duplicate payment|payment debited.*no order|amount deducted without order|paid twice|payment went through.*no order|no order.*payment|duplicate txn)\b", s):
        return "DUP-PAYMENT", "high_signal_rule"
    if re.search(r"\b(cancel|cancellation|cancelled|canceled)\b", s):
        return "CANCEL", "high_signal_rule"
    if re.search(r"\b(coupon|promo code|price adjustment|discount|price difference|offer code)\b", s):
        return "PRICE-ADJ", "high_signal_rule"
    # Refund-delay / pickup chases are RETURN-QC unless the note also describes
    # an underlying substantive product issue.
    if re.search(r"\b(refund delay|refund pending|refund not credited|refund not received|refund reprocessed|reverse pickup|pickup not done|pickup missed|refund confirmed credited)\b", s):
        if not re.search(r"\b(wrong (?:item|product|variant)|incorrect product|damaged|transit damage|strap|pairing|battery|mic|audio|charging case.*(?:dead|not charging)|no audio|not working|fault)\b", n):
            return "RETURN-QC-OK", "high_signal_rule"
    if re.search(r"\b(not delivered|not received|haven't received|hasn'?t received|shipment not|delivery delayed|delivery delay|lost in transit|rto confirmed|rto conf|not rcvd|not recieved)\b", s):
        return "LOST-TRANSIT", "high_signal_rule"
    # Do not over-weight an agent's use of the string 'under DOA'; use the actual
    # product symptom to separate damage / wrong item from warranty-like faults.
    if re.search(r"\b(wrong (?:item|product|variant)|incorrect product|damaged (?:product|in transit|item)|transit damage|received damaged)\b", s):
        return "DOA-REPL", "high_signal_rule"
    if re.search(r"\b(warranty|strap|pairing|battery backup|battery drain|mic issue|mic not|one side|no audio|charging case.*(?:dead|not charging)|case no led|not working|defective|rma|repair)\b", s):
        return "WTY-BUYBACK", "high_signal_rule"
    if re.search(r"\b(refund (?:not|pending|delay|delayed|received)|refund not credited|refund not received|money.*return|return.*money|reverse pickup|refund pending|pickup not done|pickup missed)\b", s):
        return "RETURN-QC-OK", "high_signal_rule"
    return predicted, "model"


def add_recode_columns(t: pd.DataFrame, cfg: Config) -> tuple[pd.DataFrame, dict]:
    refunds = t[t["refund_amount_rupees"].notna()].copy()
    known = refunds[refunds["refund_reason_code"].isin(NON_GW_CODES)].copy()
    gw = refunds[refunds["refund_reason_code"].eq("GW-OTHER")].copy()
    if known.empty or gw.empty:
        raise ValueError("Need both known-coded refunds and GW-OTHER refunds to train the re-coder")

    # Holdout validation on known labels.
    Xtr, Xte, ytr, yte = train_test_split(
        known["text"], known["refund_reason_code"], test_size=0.25, random_state=42, stratify=known["refund_reason_code"]
    )
    hold_vec = FeatureUnion([
        ("word", TfidfVectorizer(ngram_range=(1, 2), min_df=1, max_features=30000, sublinear_tf=True)),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2, max_features=30000, sublinear_tf=True)),
    ])
    hold_Xtr = hold_vec.fit_transform(Xtr)
    hold_Xte = hold_vec.transform(Xte)
    hold_clf = LogisticRegression(max_iter=2000, class_weight="balanced")
    hold_clf.fit(hold_Xtr, ytr)
    hold_pred = hold_clf.predict(hold_Xte)
    hold_acc = float(accuracy_score(yte, hold_pred))

    # Five-fold cross-validation on known labels.
    pipe_vec = FeatureUnion([
        ("word", TfidfVectorizer(ngram_range=(1, 2), min_df=1, max_features=30000, sublinear_tf=True)),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2, max_features=30000, sublinear_tf=True)),
    ])
    X = pipe_vec.fit_transform(known["text"])
    cv_clf = LogisticRegression(max_iter=2000, class_weight="balanced")
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(cv_clf, X, known["refund_reason_code"], cv=cv, scoring="accuracy", n_jobs=-1)

    # Train full model and predict GW-OTHER.
    vec, clf = build_model(known)
    gw_X = vec.transform(gw["text"])
    probs = clf.predict_proba(gw_X)
    classes = clf.classes_
    gw["model_reason"] = classes[np.argmax(probs, axis=1)]
    gw["model_confidence"] = np.max(probs, axis=1)
    recodes = [rule_override(m, n, p, cfg) for m, n, p in zip(gw["customer_message"], gw["agent_notes"], gw["model_reason"])]
    gw["recode_reason"] = [r[0] for r in recodes]
    gw["recode_source"] = [r[1] for r in recodes]
    gw["needs_review"] = gw["model_confidence"] < cfg.review_threshold

    out = t.copy()
    out["final_reason_code"] = out["refund_reason_code"]
    mapping = gw.set_index("ticket_id")[["recode_reason", "model_confidence", "recode_source", "needs_review"]]
    mask = out["refund_reason_code"].eq("GW-OTHER")
    out.loc[mask, "final_reason_code"] = out.loc[mask, "ticket_id"].map(mapping["recode_reason"])
    out.loc[mask, "recode_confidence"] = out.loc[mask, "ticket_id"].map(mapping["model_confidence"])
    out.loc[mask, "recode_source"] = out.loc[mask, "ticket_id"].map(mapping["recode_source"])
    out.loc[mask, "recode_needs_review"] = out.loc[mask, "ticket_id"].map(mapping["needs_review"])
    out.loc[~mask, "recode_confidence"] = 1.0
    out.loc[~mask, "recode_source"] = "original_code"
    out.loc[~mask, "recode_needs_review"] = False

    metrics = {
        "known_label_holdout_accuracy": hold_acc,
        "known_label_cv_accuracy_mean": float(cv_scores.mean()),
        "known_label_cv_accuracy_std": float(cv_scores.std()),
        "gw_other_tickets": int(len(gw)),
        "gw_other_reclassified": int((gw["recode_reason"] != "GW-OTHER").sum()),
        "gw_other_kept_as_goodwill": int((gw["recode_reason"] == "GW-OTHER").sum()),
        "manual_audit_sample_note": "See gold_sample.csv: 40 hand-labeled GW-OTHER tickets used as a simple audit set.",
    }
    gold_path = Path(__file__).resolve().parent / "gold_sample.csv"
    if gold_path.exists():
        gold = pd.read_csv(gold_path)
        merged = gold.merge(gw[["ticket_id", "recode_reason"]], on="ticket_id", how="inner")
        if not merged.empty:
            metrics["manual_audit_accuracy"] = float((merged["gold_reason"] == merged["recode_reason"]).mean())
            metrics["manual_audit_n"] = int(len(merged))
    return out, metrics


def replacement_flag(t: pd.DataFrame) -> pd.DataFrame:
    refunds = t[t["refund_amount_rupees"].notna()].copy()
    n = refunds["agent_notes"].fillna("").str.lower()
    strong_text = (
        n.str.contains(r"\bboth (?:refund|rfnd) (?:and|&) (?:replacement|rplc)\b", regex=True)
        | n.str.contains(r"\brefund\s*\+\s*(?:rplc|replacement)\b", regex=True)
        | n.str.contains(r"\b(?:refund|rfnd) (?:done|processed|issued)\b.*\b(?:new unit|new piece|fresh pair|replacement unit|replacement dispatched)\b", regex=True)
        | n.str.contains(r"\b(?:new unit|new piece|fresh pair|replacement unit|replacement dispatched)\b.*\b(?:refund|rfnd)\b", regex=True)
        | n.str.contains(r"\b(?:sent a new unit|sent a new set)\b.*\breleased the money\b", regex=True)
    )
    flags = refunds["replacement_issued"].eq("Y") | strong_text
    out = refunds[["ticket_id", "refund_month", "agent_id", "refund_amount_rupees", "replacement_issued", "agent_notes"]].copy()
    out["text_evidence"] = strong_text
    out["replacement_double_comp_candidate"] = flags
    out["review_reason"] = np.where(
        refunds["replacement_issued"].eq("Y") & strong_text, "structured + text",
        np.where(refunds["replacement_issued"].eq("Y"), "structured flag", np.where(strong_text, "text evidence", ""))
    )
    return out


def write_outputs(t: pd.DataFrame, data: dict[str, pd.DataFrame], metrics: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    refunds = t[t["refund_amount_rupees"].notna()].copy()
    refunds["month"] = refunds["created_at"].dt.to_period("M").astype(str)
    by_reason = refunds.groupby(["month", "final_reason_code"]).agg(
        refund_tickets=("ticket_id", "nunique"),
        refund_spend_inr=("refund_amount_rupees", "sum"),
    ).reset_index()
    by_reason.to_csv(out_dir / "refund_monthly_by_reason.csv", index=False)

    by_agent = refunds.groupby(["month", "agent_id", "final_reason_code"]).agg(
        refund_tickets=("ticket_id", "nunique"),
        refund_spend_inr=("refund_amount_rupees", "sum"),
    ).reset_index()
    by_agent.to_csv(out_dir / "refund_monthly_by_agent.csv", index=False)

    agent_reason = refunds.groupby(["agent_id", "final_reason_code"]).agg(
        refund_tickets=("ticket_id", "nunique"),
        refund_spend_inr=("refund_amount_rupees", "sum"),
    ).reset_index()
    agent_reason.to_csv(out_dir / "refund_agent_reason.csv", index=False)

    audit_cols = [
        "ticket_id", "refund_month", "customer_id", "order_id", "agent_id", "assigned_team",
        "refund_amount_rupees", "refund_reason_code", "final_reason_code", "recode_confidence",
        "recode_source", "recode_needs_review", "customer_message", "agent_notes", "source_system"
    ]
    t[t["refund_amount_rupees"].notna()][audit_cols].to_csv(out_dir / "refund_recode_audit.csv", index=False)

    rep = replacement_flag(t)
    rep.to_csv(out_dir / "replacement_double_comp_candidates.csv", index=False)

    # Agent roster is included so the summary can be filtered without rejoining source data.
    data["agents"].to_csv(out_dir / "agent_roster.csv", index=False)

    totals = refunds.groupby("final_reason_code").agg(
        refund_tickets=("ticket_id", "nunique"),
        refund_spend_inr=("refund_amount_rupees", "sum"),
    ).sort_values("refund_spend_inr", ascending=False)
    totals["spend_share"] = totals["refund_spend_inr"] / totals["refund_spend_inr"].sum()
    totals.to_csv(out_dir / "refund_reason_summary.csv")

    # Business-control numbers supported by the policy + export.
    explicit_gw = refunds[refunds["final_reason_code"].eq("GW-OTHER")]
    overcap = explicit_gw[explicit_gw["refund_amount_rupees"] > 500]
    gw_bucket = refunds[refunds["refund_reason_code"].eq("GW-OTHER")]
    qtr_savings = float(max(0, (overcap["refund_amount_rupees"] - 500).sum()) * 3 / 18)

    qa = {
        "raw_ticket_rows": int(len(data["tickets"])),
        "unique_tickets_after_dedup": int(len(t)),
        "refund_tickets_after_dedup": int(len(refunds)),
        "refund_spend_inr_after_dedup_and_unit_fix": float(refunds["refund_amount_rupees"].sum()),
        "raw_gw_other_ticket_share": float(len(gw_bucket) / len(refunds)),
        "raw_gw_other_spend_share": float(gw_bucket["refund_amount_rupees"].sum() / refunds["refund_amount_rupees"].sum()),
        "final_goodwill_tickets": int(len(explicit_gw)),
        "final_goodwill_spend_inr": float(explicit_gw["refund_amount_rupees"].sum()),
        "goodwill_overcap_tickets": int(len(overcap)),
        "goodwill_overcap_excess_inr_18m": float(max(0, (overcap["refund_amount_rupees"] - 500).sum())),
        "goodwill_overcap_excess_inr_quarter_run_rate": qtr_savings,
        "unexplained_gw_bucket_spend_reclassified_inr": float(gw_bucket["refund_amount_rupees"].sum() - explicit_gw["refund_amount_rupees"].sum()),
    }
    (out_dir / "qa_summary.json").write_text(json.dumps({**metrics, **qa}, indent=2), encoding="utf-8")

    lines = [
        "# Vireo refund analysis QA",
        "",
        f"- Raw ticket rows: **{qa['raw_ticket_rows']:,}**",
        f"- Unique tickets after duplicate-pair collapse: **{qa['unique_tickets_after_dedup']:,}**",
        f"- Refund tickets after de-duplication: **{qa['refund_tickets_after_dedup']:,}**",
        f"- Normalized refund spend: **Rs {qa['refund_spend_inr_after_dedup_and_unit_fix']:,.0f}**",
        f"- Raw GW-OTHER share: **{qa['raw_gw_other_ticket_share']:.1%} of refund tickets / {qa['raw_gw_other_spend_share']:.1%} of refund spend**",
        f"- Final explicit-goodwill share: **{qa['final_goodwill_tickets']/qa['refund_tickets_after_dedup']:.1%} of refund tickets**",
        f"- Explicit goodwill spend: **Rs {qa['final_goodwill_spend_inr']:,.0f}**",
        f"- Over-cap explicit-goodwill tickets (> Rs 500): **{qa['goodwill_overcap_tickets']}**",
        f"- Excess above a Rs 500 cap: **Rs {qa['goodwill_overcap_excess_inr_18m']:,.0f} over 18 months (~Rs {qa['goodwill_overcap_excess_inr_quarter_run_rate']:,.0f}/quarter at the same run rate)**",
        f"- Previously opaque GW-OTHER spend reclassified into a reason: **Rs {qa['unexplained_gw_bucket_spend_reclassified_inr']:,.0f}**",
        "",
        "## Model checks",
        f"- Held-out known-code accuracy: **{metrics['known_label_holdout_accuracy']:.1%}**",
        f"- 5-fold CV accuracy on known codes: **{metrics['known_label_cv_accuracy_mean']:.1%} +/- {metrics['known_label_cv_accuracy_std']:.1%}**",
        f"- Manual GW-OTHER audit: **{metrics.get('manual_audit_accuracy', float('nan')):.1%} on n={metrics.get('manual_audit_n', 0)}**",
        f"- GW-OTHER tickets reclassified by the tool: **{metrics['gw_other_reclassified']:,}/{metrics['gw_other_tickets']:,}**",
        f"- GW-OTHER tickets kept as explicit goodwill: **{metrics['gw_other_kept_as_goodwill']:,}**",
        "",
        "## Important interpretation",
        "The tool treats total refund spend as a reporting measure, not an agent-performance score. The policy states that Returns Desk processes the large majority of refunds and that Tier 2 agents should not be compared with Tier 1 on volume metrics.",
    ]
    (out_dir / "qa_summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser(description="Vireo refund analysis")
    p.add_argument("--data-dir", type=Path, default=Path("data"))
    p.add_argument("--out-dir", type=Path, default=Path("outputs"))
    args = p.parse_args()

    data = load_data(args.data_dir)
    duplicate_audit = audit_duplicates(data["tickets"])
    t = prepare_tickets(data["tickets"])
    t, metrics = add_recode_columns(t, Config())
    metrics["duplicate_audit"] = duplicate_audit
    write_outputs(t, data, metrics, args.out_dir)
    print(json.dumps(metrics, indent=2))
    print(f"\nWrote outputs to {args.out_dir.resolve()}")


if __name__ == "__main__":
    main()
