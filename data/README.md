# Source data

The five client CSVs go here. They are **not** committed to this repository.

```
tickets.csv     18 months of support tickets (Jan 2025 - Jun 2026)
agents.csv      roster, one row per assignment
orders.csv      reference
customers.csv   reference
products.csv    reference (unit_cost_inr is used for replacement costing)
```

Place them in this directory, then run from the repository root:

```bash
python refund_tool.py --data-dir data --out-dir outputs
```
