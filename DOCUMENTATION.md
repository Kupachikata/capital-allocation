# Capital Allocation & Break-Even System — One-Page Overview

## What It Is

A **retail decision-support web app** that helps you:
- See **break-even** and profit projections from unit economics and fixed costs.
- **Allocate capital across product categories** using profit and turnover, so fast-moving lines get the right share of stock spend.
- **Recommend what to stock per branch** using a Pareto 80/20 rule so each store is stocked based on its own sales, not a single chain-wide list.

The app is built with **Streamlit** and **Plotly**, and reads from Excel and JSON configs in the project folder.

---

## Main Sections

| Section | Purpose |
|--------|---------|
| **Break-Even Analysis** | Input selling price, variable cost, expected units, fixed costs. Get break-even units/revenue, projected profit, and a revenue→profit Sankey. |
| **Capital Allocation Optimiser** | Allocate a total capital budget across categories. Weights use **Turnover-Adjusted GP** (GP contribution × turnover cycles) and optional **Target Space %**, so high-margin, fast-turning categories get more capital. You pick a **branch**; total shop floor space can auto-fill from the dataset. |
| **Pareto 80/20 Product Configurator** | Pick a **branch** and **category**. The app lists the products that contribute to **80% of that category’s sales at that branch**, with unit price, monthly volume, recommended order quantity, and capital needed. Stocking is **branch-specific**: what moves in one store may differ from another. |
| **Target-Based Capital Optimiser** | Same allocation logic as above but driven by **target** gross sales and target GP % per category (e.g. for planning or new formats). |

---

## Data Sources

- **`retail_pos_sales.xlsx`** — Aggregated POS by category (e.g. `Category`, `Total_Net_Amount`). Used to estimate **turnover cycles** per category when “Use POS” is on.
- **`products3.xlsx`** — Transaction-level or aggregated product data **by store**. Must include (or map to): store/branch name, category, product, quantity, price, date, and optionally total shop floor space per store. Used for branch dropdown, auto-fill of **Total Shop Floor Space**, and **branch-specific Pareto** recommendations.
- **`category_gp_config.json`** — Categories with gross sales, target GP %, and default turnover (used when POS is off or missing).
- **`category_targets_config.json`** — Target gross sales and target GP % per category for the Target-Based Optimiser.

Column names in the Excel files can differ (e.g. “Unit Selling Price (Incl VAT)”); the app maps them to the expected fields (price, quantity, category, store, etc.).

---

## Key Concepts

- **Turnover-Adjusted GP** — Allocation weight = (GP contribution × turnover cycles). Rewards categories that make money **over time** (margin × velocity), not just high margin per unit.
- **Pareto 80/20** — For the chosen branch and category, products are ranked by revenue; the list stops when cumulative revenue reaches 80% of that category’s total at that branch. Recommended order qty uses monthly volume and turnover (from the allocation section).
- **Branch-specific stocking** — Product list and quantities are filtered by the selected branch so each store gets recommendations based on its own sales in `products3.xlsx`.

---

## How to Run

1. **Install:** `pip install -r requirements.txt` (Streamlit, Plotly, pandas, openpyxl).
2. **Run:** From the project folder, `streamlit run app.py`.
3. **Open:** In the browser, go to `http://localhost:8501`.

Ensure `retail_pos_sales.xlsx`, `products3.xlsx`, and the two JSON config files are in the same folder as `app.py`. If a file or column is missing, the app shows warnings and falls back to manual inputs or assumed values where possible.
