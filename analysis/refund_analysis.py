#!/usr/bin/env python3
"""
Exploratory analysis behind memo/memo_to_arjun.md.

Not part of the pipeline. refund_tool.py is the single entry point for producing
outputs; this script answers the questions the memo makes claims about, and writes
every figure it quotes to analysis/memo_numbers.json so each one is traceable.

It imports load_data/prepare_tickets from refund_tool rather than re-implementing
de-duplication and the unit fix, so the memo and the pipeline cannot drift apart.

Usage:
    python analysis/refund_analysis.py --data-dir data --out analysis/memo_numbers.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from refund_tool import load_data, prepare_tickets  # noqa: E402

REPL_COST_UPLIFT = 340  # policy s5: reverse pickup + forward shipping
GOODWILL_CAP = 500      # policy s5
NEG = (r"not applicable|out of stock|rfnd only|refund only|explained policy|"
       r"declined|no replacement|replacement not")
SENT = (r"replacement sent|replacement raised|replacement dispatched|replacement issued|"
        r"replacement appoved|replacement approved|rplc (?:raised|sent|dispatched|appoved|approved)|"
        r"new unit|new piece|fresh pair|unit sent")


def q(x) -> float:
    """18 months -> per quarter."""
    return float(x) * 3 / 18


def section(title: str) -> None:
    print("\n" + "=" * 70 + f"\n{title}\n" + "=" * 70)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=Path("data"))
    ap.add_argument("--out", type=Path, default=Path("analysis/memo_numbers.json"))
    a = ap.parse_args()

    data = load_data(a.data_dir)
    raw = data["tickets"]
    t = prepare_tickets(raw)
    products = data["products"].set_index("sku")
    orders = data["orders"].copy()
    orders["order_date"] = pd.to_datetime(orders["order_date"], errors="coerce")

    r = t[t["refund_amount_rupees"].notna()].copy()
    note = r["agent_notes"].fillna("").str.lower()
    N: dict = {}

    # ------------------------------------------------------------------
    section("1. THE UNIT FIX, PROVED ON DUPLICATE PAIRS")
    # The 638 duplicated tickets are a natural experiment: the same ticket in
    # both systems. If legacy is a different unit, the ratio is constant.
    dup = raw[raw["ticket_id"].duplicated(keep=False)]
    h = dup[dup.source_system == "helpdesk"].set_index("ticket_id")
    l = dup[dup.source_system == "legacy_fd"].set_index("ticket_id")
    common = h.index.intersection(l.index)
    ratio = (l.loc[common, "refund_amount_inr"] / h.loc[common, "refund_amount_inr"]).dropna()
    N["dup_pairs"] = int(len(common))
    N["paired_refunds"] = int(len(ratio))
    N["paired_ratio_mean"] = float(ratio.mean())
    N["paired_ratio_sd"] = float(ratio.std())
    N["naive_total_if_unfixed"] = round(float(raw["refund_amount_inr"].sum()))
    print(f"  duplicate pairs           {N['dup_pairs']}")
    print(f"  of which carry a refund   {N['paired_refunds']}")
    print(f"  legacy/helpdesk ratio     {N['paired_ratio_mean']:.2f}  (SD {N['paired_ratio_sd']:.4f})")
    print(f"  18-month total uncorrected  Rs {N['naive_total_if_unfixed']:,}")

    # ------------------------------------------------------------------
    section("2. DID THE REFUND RATE ACTUALLY RISE?  (the client's premise)")
    t["m"] = t["created_at"].dt.to_period("M")
    m = t.groupby("m").agg(tickets=("ticket_id", "size"),
                           refunds=("refund_amount_rupees", "count"),
                           spend=("refund_amount_rupees", "sum"))
    m["rate_pct"] = (m.refunds / m.tickets * 100).round(1)
    print(m.to_string())

    early, late = m.iloc[:3], m.iloc[-3:]
    N["tix_early"] = round(float(early.tickets.mean()))
    N["tix_late"] = round(float(late.tickets.mean()))
    N["spend_early"] = round(float(early.spend.mean()))
    N["spend_late"] = round(float(late.spend.mean()))
    N["rate_early"] = round(float(early.refunds.sum() / early.tickets.sum() * 100), 1)
    N["rate_late"] = round(float(late.refunds.sum() / late.tickets.sum() * 100), 1)
    N["spend_growth_x"] = round(N["spend_late"] / N["spend_early"], 1)
    N["rate_min"] = float(m.rate_pct.min())
    N["rate_max"] = float(m.rate_pct.max())
    print(f"\n  tickets/month   {N['tix_early']} -> {N['tix_late']}")
    print(f"  spend/month     Rs {N['spend_early']:,} -> Rs {N['spend_late']:,}  ({N['spend_growth_x']}x)")
    print(f"  REFUND RATE     {N['rate_early']}% -> {N['rate_late']}%   (18-mo range {N['rate_min']}-{N['rate_max']}%)")
    print("  => spend rose because volume rose. The rate is flat.")

    # ------------------------------------------------------------------
    section("3. THE GW-OTHER BUCKET")
    N["tickets_raw_rows"] = int(len(raw))
    N["tickets_dedup"] = int(len(t))
    N["refund_tickets"] = int(len(r))
    N["refund_total"] = round(float(r.refund_amount_rupees.sum()))
    N["quarters"] = int(r["created_at"].dt.to_period("Q").nunique())
    N["refund_per_qtr"] = round(N["refund_total"] / N["quarters"])
    gw = r[r.refund_reason_code == "GW-OTHER"]
    N["gw_tickets"] = int(len(gw))
    N["gw_rs"] = round(float(gw.refund_amount_rupees.sum()))
    N["gw_pct_tickets"] = round(len(gw) / len(r) * 100, 1)
    N["gw_pct_spend"] = round(float(gw.refund_amount_rupees.sum() / r.refund_amount_rupees.sum() * 100), 1)
    print(f"  refund tickets {N['refund_tickets']:,}  |  total Rs {N['refund_total']:,}  "
          f"|  per quarter Rs {N['refund_per_qtr']:,}")
    print(f"  GW-OTHER  {N['gw_tickets']} tickets = {N['gw_pct_tickets']}% of refunds, "
          f"Rs {N['gw_rs']:,} = {N['gw_pct_spend']}% of spend")

    # ------------------------------------------------------------------
    section("4. GENUINE GOODWILL, AND THE Rs 500 CAP")
    # Match the pipeline's definition: whatever refund_tool leaves as GW-OTHER.
    audit_path = Path("outputs/refund_recode_audit.csv")
    if audit_path.exists():
        audit = pd.read_csv(audit_path, dtype={"ticket_id": str})
        kept = audit[(audit.refund_reason_code == "GW-OTHER") &
                     (audit.final_reason_code == "GW-OTHER")]
        src = "outputs/refund_recode_audit.csv"
    else:
        kept = gw[gw.agent_notes.fillna("").str.lower()
                  .str.contains(r"goodwill|one[- ]time gesture|released the money as well")]
        kept = kept.rename(columns={"refund_amount_rupees": "refund_amount_rupees"})
        src = "fallback regex (run refund_tool.py first for the authoritative figure)"
    amt = kept["refund_amount_rupees"]
    excess = float((amt - GOODWILL_CAP).clip(lower=0).sum())
    N["goodwill_n"] = int(len(kept))
    N["goodwill_rs"] = round(float(amt.sum()))
    N["goodwill_over_cap_n"] = int((amt > GOODWILL_CAP).sum())
    N["goodwill_excess_18m"] = round(excess)
    N["goodwill_excess_qtr"] = round(q(excess))
    N["goodwill_median"] = float(amt.median())
    print(f"  source: {src}")
    print(f"  genuine goodwill        {N['goodwill_n']} tickets, Rs {N['goodwill_rs']:,}")
    print(f"  above the Rs 500 cap    {N['goodwill_over_cap_n']} of {N['goodwill_n']}  "
          f"(median refund Rs {N['goodwill_median']:,.0f})")
    print(f"  EXCESS over cap         Rs {N['goodwill_excess_18m']:,} / 18mo "
          f"= Rs {N['goodwill_excess_qtr']:,} per quarter")
    print("  NB excess = sum(amount - 500), not the total refunded. Easy to conflate.")

    # ------------------------------------------------------------------
    section("5. REFUND *AND* REPLACEMENT  (policy s5: must never happen)")
    flag = r.replacement_issued.eq("Y")
    said_sent = note.str.contains(SENT, regex=True)
    negated = note.str.contains(NEG, regex=True)
    text_only = said_sent & ~negated & ~flag

    both = r[flag | (said_sent & ~negated)].copy()
    both["repl_cost"] = both.product_sku.map(products.unit_cost_inr) + REPL_COST_UPLIFT

    N["dblcomp_flag_only"] = int(flag.sum())
    N["dblcomp_text_adds"] = int(text_only.sum())
    N["dblcomp_n"] = int(len(both))
    N["dblcomp_per_month"] = round(len(both) / 18, 1)
    N["dblcomp_refund_18m"] = round(float(both.refund_amount_rupees.sum()))
    N["dblcomp_replcost_18m"] = round(float(both.repl_cost.sum()))
    N["dblcomp_refund_qtr"] = round(q(both.refund_amount_rupees.sum()))
    N["dblcomp_replcost_qtr"] = round(q(both.repl_cost.sum()))
    N["dblcomp_in_gw"] = int((both.refund_reason_code == "GW-OTHER").sum())
    N["dblcomp_in_gw_pct"] = round(float((both.refund_reason_code == "GW-OTHER").mean() * 100))
    N["dblcomp_notes_negated"] = int((said_sent & negated).sum())

    print(f"  structured flag = Y                     {N['dblcomp_flag_only']}")
    print(f"  + note says a unit was sent (flag = N)  {N['dblcomp_text_adds']}")
    print(f"  = total                                 {N['dblcomp_n']}  "
          f"(~{N['dblcomp_per_month']} per month)")
    print(f"  notes excluded by a negation phrase     {N['dblcomp_notes_negated']}  "
          "('not applicable', 'out of stock', 'refund only')")
    print(f"\n  refunds paid on these            Rs {N['dblcomp_refund_18m']:,} "
          f"= Rs {N['dblcomp_refund_qtr']:,}/qtr")
    print(f"  replacement cost (unit + {REPL_COST_UPLIFT})   Rs {N['dblcomp_replcost_18m']:,} "
          f"= Rs {N['dblcomp_replcost_qtr']:,}/qtr")
    print(f"  => Rs {N['dblcomp_replcost_qtr']:,}-{N['dblcomp_refund_qtr']:,} per quarter, "
          "depending which side was the error")
    print(f"  {N['dblcomp_in_gw']} of {N['dblcomp_n']} ({N['dblcomp_in_gw_pct']}%) were tagged GW-OTHER "
          "-- the mis-tagging is what hid this")

    # ------------------------------------------------------------------
    section("6. WHY NO AGENT LEAGUE TABLE  (policy s6)")
    ag = data["agents"].drop_duplicates("agent_id").set_index("agent_id")
    g = (t.groupby("agent_id")
           .agg(tickets=("ticket_id", "size"), refunds=("refund_amount_rupees", "count"),
                spend=("refund_amount_rupees", "sum"))
           .join(ag[["name", "team", "tier"]]))
    g["refund_rate_pct"] = (g.refunds / g.tickets * 100).round(1)
    top = g.sort_values("spend", ascending=False).head(8)
    print(top[["name", "team", "tier", "tickets", "refunds", "spend", "refund_rate_pct"]].to_string())
    N["top_agent_team"] = str(top.iloc[0]["team"])
    N["top_agent_rate"] = float(top.iloc[0]["refund_rate_pct"])
    print(f"\n  Top of the table is {N['top_agent_team']} at {N['top_agent_rate']}%.")
    print("  Policy s6: Returns Desk processes the large majority of refunds BY DESIGN,")
    print("  and Tier 2 must not be compared with Tier 1 on volume. A raw ranking would")
    print("  punish people for their job description. Not published as a leaderboard.")

    # ------------------------------------------------------------------
    section("7. DATA QUALITY -- fields the memo does not rely on")
    j = t.merge(orders[["order_id", "order_date"]], on="order_id", how="left")
    j["days"] = (j.created_at.dt.normalize() - j.order_date).dt.days
    N["tickets_no_order_match"] = int(j.order_date.isna().sum())
    N["tickets_no_order_match_pct"] = round(float(j.order_date.isna().mean() * 100), 1)
    N["impossible_order_dates"] = int((j.days < 0).sum())
    N["impossible_worst_days"] = int(j.days.min()) if j.days.notna().any() else 0
    print(f"  tickets that do not join to an order   {N['tickets_no_order_match']:,} "
          f"({N['tickets_no_order_match_pct']}%)")
    print(f"  tickets created BEFORE their order     {N['impossible_order_dates']} "
          f"(worst: {N['impossible_worst_days']} days)")

    # Timestamp check: policy s9 warns of a UTC/IST mismatch on migrated tickets.
    offs = []
    for c in ["created_at", "first_response_at", "resolved_at"]:
        hh = pd.to_datetime(h.loc[common, c], errors="coerce")
        ll = pd.to_datetime(l.loc[common, c], errors="coerce")
        offs.append(float(((ll - hh).dt.total_seconds() / 3600).abs().max()))
    N["max_timestamp_offset_hours"] = max(offs)
    print(f"  max timestamp offset across {len(common)} duplicate pairs   "
          f"{N['max_timestamp_offset_hours']:.2f} h")
    print("  => no UTC/IST offset in this export. Applying the documented +5:30")
    print("     'fix' would inject a 5.5h error into every migrated handle time.")

    short = gw.agent_notes.fillna("").str.replace(r"\s*(~\s*\w+|//\s*\w+)\s*$", "", regex=True).str.strip(" -.|")
    N["gw_notes_under_30_chars"] = int((short.str.len() <= 30).sum())
    N["gw_notes_under_30_pct"] = round(float((short.str.len() <= 30).mean() * 100), 1)
    print(f"  GW-OTHER notes <=30 chars              {N['gw_notes_under_30_chars']} "
          f"({N['gw_notes_under_30_pct']}%) -- abstention is necessary")

    # Refund chases: same order refunded more than once at the same amount.
    vc = r.order_id.value_counts()
    sub = r[r.order_id.isin(vc[vc > 1].index)]
    rep = sub.groupby(["order_id", "refund_amount_rupees"]).size()
    rep = rep[rep > 1]
    N["orders_with_multiple_refund_tickets"] = int((vc > 1).sum())
    N["repeat_amount_extra_tickets"] = int((rep - 1).sum())
    N["repeat_amount_value"] = round(float(sum((n - 1) * amt for (_, amt), n in rep.items())))
    print(f"  orders with >1 refund ticket           {N['orders_with_multiple_refund_tickets']}")
    print(f"  identical order+amount repeats         {N['repeat_amount_extra_tickets']} tickets, "
          f"~Rs {N['repeat_amount_value']:,} (~{N['repeat_amount_value']/N['refund_total']*100:.1f}% of spend)")
    print("  Flagged, not netted out: 'same economic refund' is a rule Finance should set.")

    # ------------------------------------------------------------------
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(N, indent=1), encoding="utf-8")
    section("MEMO NUMBERS WRITTEN")
    print(f"  {a.out}  ({len(N)} figures)")
    print("  Every number quoted in memo/memo_to_arjun.md is a key in this file.")


if __name__ == "__main__":
    main()
