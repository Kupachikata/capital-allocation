import streamlit as st
import math
import plotly.graph_objects as go
import plotly.express as px
import json
from pathlib import Path

# Page configuration
st.set_page_config(page_title="Break Even Analysis", layout="wide")

st.title("Break Even Analysis")

# Create two columns: 20% left, 80% right
left_col, right_col = st.columns([0.2, 0.8], gap="large")

# ============== LEFT SECTION - INPUT WIDGETS ==============
with left_col:
    st.subheader("Inputs")

    # Selling Price Per Unit
    selling_price = st.number_input(
        "Selling Price Per Unit",
        min_value=0.0,
        max_value=2.0,
        value=1.0,
        step=0.01,
        format="%.2f"
    )

    # Variable Cost Per Unit
    variable_cost = st.number_input(
        "Variable Cost Per Unit",
        min_value=0.0,
        max_value=2.0,
        value=0.5,
        step=0.01,
        format="%.2f"
    )

    # Expected Units Sold
    expected_units = st.number_input(
        "Expected Units Sold",
        min_value=0,
        value=1000,
        step=1
    )

    # Projected Fixed Costs
    fixed_costs = st.number_input(
        "Projected Fixed Costs",
        min_value=0.0,
        value=5000.0,
        step=100.0,
        format="%.2f"
    )

# ============== RIGHT SECTION - DISPLAY & ANALYSIS ==============
with right_col:
    # ---- TOP SECTION: ASSUMPTIONS ----
    st.subheader("📊 Assumptions")

    # Create three columns for the tiles
    assumption_col1, assumption_col2, assumption_col3 = st.columns(
        3, gap="small")

    with assumption_col1:
        st.metric(
            label="Selling Price Per Unit",
            value=f"${selling_price:.2f}"
        )

    with assumption_col2:
        st.metric(
            label="Variable Cost Per Unit",
            value=f"${variable_cost:.2f}"
        )

    with assumption_col3:
        st.metric(
            label="Expected Units Sold",
            value=f"{expected_units:,}"
        )

    # ---- MIDDLE SECTION: PROJECTIONS ----
    st.divider()
    st.subheader("📈 Projections")

    # Calculate break even
    contribution_margin_per_unit = selling_price - variable_cost

    if contribution_margin_per_unit > 0:
        break_even_units = math.ceil(
            fixed_costs / contribution_margin_per_unit)
        break_even_revenue = break_even_units * selling_price
    else:
        break_even_units = float('inf')
        break_even_revenue = float('inf')

    # Calculate expected profit
    total_revenue = expected_units * selling_price
    total_variable_costs = expected_units * variable_cost
    total_contribution = expected_units * contribution_margin_per_unit
    total_profit = total_contribution - fixed_costs

    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(
        4, gap="small")

    with metric_col1:
        st.metric(
            label="Fixed Costs",
            value=f"${fixed_costs:,.2f}"
        )

    with metric_col2:
        st.metric(
            label="Total Sales",
            value=f"${total_revenue:,.2f}"
        )

    with metric_col3:
        st.metric(
            label="Variable Cost",
            value=f"${total_variable_costs:,.2f}"
        )

    with metric_col4:
        profit_color = "🟢" if total_profit >= 0 else "🔴"
        st.metric(
            label="Net Profit",
            value=f"{profit_color} ${total_profit:,.2f}"
        )

    # ---- BOTTOM SECTION: PROFITABILITY ANALYSIS ----
    st.divider()
    #st.subheader("💰 Profitability Analysis")

    # Create two columns: left for metrics, right for visualization
    bottom_left_col, bottom_right_col = st.columns([0.25, 0.75], gap="medium")

    # Left column: Break Even metrics (stacked vertically)
    with bottom_left_col:
        st.metric(
            label="Break Even Units",
            value=f"{break_even_units:,}" if break_even_units != float(
                'inf') else "N/A"
        )
        st.metric(
            label="Break Even Revenue",
            value=f"${break_even_revenue:,.2f}" if break_even_revenue != float(
                'inf') else "N/A"
        )

    # Right column: Sankey visualization
    with bottom_right_col:
        st.markdown("**Revenue Flow Analysis:**")

        # Create Sankey diagram
        # Calculate contribution after variable costs
        contribution = total_revenue - total_variable_costs

        # Calculate percentages of sales
        var_cost_pct = (total_variable_costs / total_revenue *
                        100) if total_revenue > 0 else 0
        markup_pct = (contribution / total_revenue *
                      100) if total_revenue > 0 else 0
        fixed_cost_pct = (fixed_costs / total_revenue *
                          100) if total_revenue > 0 else 0
        profit_pct = (total_profit / total_revenue *
                      100) if total_revenue > 0 else 0

        # Create nodes and links for Sankey
        labels = [
            f"Sales<br>100%",
            f"Variable Costs<br>{var_cost_pct:.1f}%",
            f"Markup<br>{markup_pct:.1f}%",
            f"Fixed Costs<br>{fixed_cost_pct:.1f}%",
            f"{'Net Profit' if total_profit >= 0 else 'Net Loss'}<br>{profit_pct:.1f}%"
        ]

        # Create color mapping
        node_colors = [
            "rgba(76, 175, 80, 0.8)",      # Green for Sales
            "rgba(244, 67, 54, 0.8)",      # Red for Variable Costs
            "rgba(255, 193, 7, 0.8)",      # Gold for Markup
            "rgba(244, 67, 54, 0.8)",      # Red for Fixed Costs
            # Green or Red for Profit/Loss
            "rgba(76, 175, 80, 0.8)" if total_profit >= 0 else "rgba(244, 67, 54, 0.8)"
        ]

        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=labels,
                color=node_colors,
                customdata=[f"${v:,.0f}" for v in [
                    total_revenue, total_variable_costs, contribution, fixed_costs, abs(total_profit)]],
                hovertemplate="%{label}<br>Amount: %{customdata}<extra></extra>"
            ),
            link=dict(
                source=[0, 0, 2, 2],
                target=[1, 2, 3, 4],
                value=[total_variable_costs, contribution, fixed_costs,
                       total_profit if total_profit >= 0 else 0],
                color=[
                    "rgba(244, 67, 54, 0.4)",
                    "rgba(255, 193, 7, 0.4)",
                    "rgba(244, 67, 54, 0.4)",
                    "rgba(76, 175, 80, 0.4)" if total_profit >= 0 else "rgba(244, 67, 54, 0.4)"
                ],
                hovertemplate="%{source.label} → %{target.label}<br>$%{value:,.0f}<extra></extra>"
            )
        )])

        fig.update_layout(
            title="Revenue to Profit Flow Sankey Diagram",
            font=dict(size=12, family="Arial"),
            height=400,
            margin=dict(l=20, r=20, t=20, b=20),
            plot_bgcolor="rgba(240, 240, 240, 0.5)",
            paper_bgcolor="white"
        )

        st.plotly_chart(fig, use_container_width=True)

# ===================== NEW SECTION: CAPITAL ALLOCATION (SEPARATE) =====================
# NOTE: This section is intentionally independent from all break-even inputs/calculations above.
st.divider()
st.subheader("Capital Allocation Optimiser")

# Inputs for this section only (independent of break-even)
total_capital_available = st.number_input(
    "Total Capital Available for New Stock",
    min_value=0.0,
    value=3_000_000.0,
    step=50_000.0,
    format="%.2f",
    help="Capital to allocate proportionally using GP contribution weights."
)

# Load defaults from JSON (source of truth for categories, gross sales, and default target GP%)
config_path = Path(__file__).with_name("category_gp_config.json")
try:
    _raw_config = json.loads(config_path.read_text(encoding="utf-8"))
except Exception as e:
    st.error(f"Missing or invalid config file: {config_path.name}. Error: {e}")
    _raw_config = {}

# Normalize config into a list of category records (preserve JSON order)
categories = []
for category_name, cfg in _raw_config.items():
    categories.append(
        {
            "category": category_name,
            "gross_sales": float(cfg.get("gross_sales", 0.0)),
            "target_gp_percent": float(cfg.get("target_gp_percent", 0.0)),
            "rationale": str(cfg.get("rationale", "")).strip(),
        }
    )

st.caption(
    "This optimiser is fully independent from the break-even section above. "
    "Category list, Gross Sales, and default Target GP% are loaded from `category_gp_config.json`."
)

inputs_col, outputs_col = st.columns([0.45, 0.55], gap="large")

with inputs_col:
    st.markdown("**Category inputs**")

    target_gp_pct_by_category = {}
    gross_sales_by_category = {}

    for rec in categories:
        category = rec["category"]
        gross_sales = rec["gross_sales"]

        gross_sales_by_category[category] = gross_sales

        row_c1, row_c2, row_c3 = st.columns([0.46, 0.27, 0.27], gap="small")

        with row_c1:
            st.write(category)

        with row_c2:
            st.text_input(
                "Gross Sales",
                value=f"${gross_sales:,.2f}",
                key=f"gross_sales_ro__{category}",
                disabled=True,
                label_visibility="collapsed",
            )

        with row_c3:
            target_gp_pct_by_category[category] = st.number_input(
                "Target GP %",
                min_value=0.0,
                max_value=100.0,
                value=rec["target_gp_percent"],
                step=0.1,
                format="%.1f",
                key=f"target_gp_pct__{category}",
                label_visibility="collapsed",
            )

with outputs_col:
    # Compute GP contributions and allocation weights (independent of break-even)
    gp_contribution_by_category = {
        c: gross_sales_by_category[c] * (target_gp_pct_by_category[c] / 100.0)
        for c in gross_sales_by_category
    }
    total_gp_contribution = sum(gp_contribution_by_category.values())

    allocation_rows = []
    for c in gross_sales_by_category:
        gp_contrib = gp_contribution_by_category[c]
        weight = (gp_contrib / total_gp_contribution) if total_gp_contribution > 0 else 0.0
        allocated_capital = total_capital_available * weight

        allocation_rows.append(
            {
                "Category": c,
                "Gross Sales": gross_sales_by_category[c],
                "Target GP %": target_gp_pct_by_category[c],
                "GP Contribution": gp_contrib,
                "Allocation Weight (%)": weight * 100.0,
                "Recommended Capital Allocation": allocated_capital,
            }
        )

    # Bar chart: capital allocation by category
    st.markdown("**Allocation by Category**")
    
    chart_labels = [r["Category"] for r in allocation_rows]
    chart_values = [r["Recommended Capital Allocation"] for r in allocation_rows]

    chart = go.Figure(
        data=[
            go.Bar(
                x=chart_labels,
                y=chart_values,
                marker_color="rgba(33, 150, 243, 0.75)",
                hovertemplate="%{x}<br>$%{y:,.0f}<extra></extra>",
            )
        ]
    )
    chart.update_layout(
        title="",
        xaxis_title="",
        yaxis_title="Allocated Capital ($)",
        height=380,
        margin=dict(l=10, r=10, t=20, b=80),
        xaxis_tickangle=-45,
        showlegend=False,
    )
    st.plotly_chart(chart, use_container_width=True)

# ---- FULL-WIDTH TABLE SECTION ----
st.markdown("**Recommended Allocation Summary**")

# Format data for cleaner display without warnings
display_rows = []
for row in allocation_rows:
    display_rows.append({
        "Category": row["Category"],
        "Gross Sales": f"${row['Gross Sales']:,.2f}",
        "Target GP %": f"{row['Target GP %']:.1f}%",
        "GP Contribution": f"${row['GP Contribution']:,.2f}",
        "Allocation Weight (%)": f"{row['Allocation Weight (%)']:.2f}%",
        "Recommended Capital Allocation": f"${row['Recommended Capital Allocation']:,.2f}",
    })

st.dataframe(
    display_rows,
    use_container_width=True,
    hide_index=True,
)
# ===================== NEW MODULE: TARGET-BASED CAPITAL ALLOCATION OPTIMISER =====================
st.divider()
st.subheader("📊 Target-Based Capital Allocation Optimiser")

# Load target configuration from JSON
targets_config_path = Path(__file__).with_name("category_targets_config.json")
try:
    targets_raw_config = json.loads(targets_config_path.read_text(encoding="utf-8"))
except Exception as e:
    st.error(f"Missing or invalid config file: {targets_config_path.name}. Error: {e}")
    targets_raw_config = {}

# Normalize target config into a list of category records (preserve JSON order)
targets_categories = []
for category_name, cfg in targets_raw_config.items():
    targets_categories.append(
        {
            "category": category_name,
            "target_gross_sales": float(cfg.get("target_gross_sales", 0.0)),
            "target_gp_percent": float(cfg.get("target_gp_percent", 0.0)),
            "rationale": str(cfg.get("rationale", "")).strip(),
        }
    )

st.caption(
    "This module is fully independent and calculates capital allocation based on target gross sales and target GP percentages."
)

# Input for total capital
targets_total_capital = st.number_input(
    "Total Capital Available for Target-Based Allocation",
    min_value=0.0,
    value=3_000_000.0,
    step=50_000.0,
    format="%.2f",
    help="Capital to allocate based on target GP contribution weights.",
    key="targets_total_capital_input"
)

targets_inputs_col, targets_outputs_col = st.columns([0.45, 0.55], gap="large")

with targets_inputs_col:
    st.markdown("**Category Targets**")

    targets_target_gp_pct_by_category = {}
    targets_target_gross_sales_by_category = {}

    for rec in targets_categories:
        category = rec["category"]
        target_gross_sales = rec["target_gross_sales"]

        targets_target_gross_sales_by_category[category] = target_gross_sales

        targets_row_c1, targets_row_c2, targets_row_c3 = st.columns([0.46, 0.27, 0.27], gap="small")

        with targets_row_c1:
            st.write(category)

        with targets_row_c2:
            st.text_input(
                "Target Gross Sales",
                value=f"${target_gross_sales:,.2f}",
                key=f"targets_tgs_ro__{category}",
                disabled=True,
                label_visibility="collapsed",
            )

        with targets_row_c3:
            targets_target_gp_pct_by_category[category] = st.number_input(
                "Target GP %",
                min_value=0.0,
                max_value=100.0,
                value=rec["target_gp_percent"],
                step=0.1,
                format="%.1f",
                key=f"targets_target_gp_pct__{category}",
                label_visibility="collapsed",
            )

with targets_outputs_col:
    # Compute target GP contributions and allocation weights
    targets_gp_contribution_by_category = {
        c: targets_target_gross_sales_by_category[c] * (targets_target_gp_pct_by_category[c] / 100.0)
        for c in targets_target_gross_sales_by_category
    }
    targets_total_gp_contribution = sum(targets_gp_contribution_by_category.values())

    targets_allocation_rows = []
    for c in targets_target_gross_sales_by_category:
        targets_gp_contrib = targets_gp_contribution_by_category[c]
        targets_weight = (targets_gp_contrib / targets_total_gp_contribution) if targets_total_gp_contribution > 0 else 0.0
        targets_allocated_capital = targets_total_capital * targets_weight

        targets_allocation_rows.append(
            {
                "Category": c,
                "Target Gross Sales": targets_target_gross_sales_by_category[c],
                "Target GP %": targets_target_gp_pct_by_category[c],
                "GP Contribution": targets_gp_contrib,
                "Allocation Weight (%)": targets_weight * 100.0,
                "Recommended Capital Allocation": targets_allocated_capital,
            }
        )

    # Bar chart: target-based capital allocation by category
    st.markdown("**Target Allocation by Category**")
    
    targets_chart_labels = [r["Category"] for r in targets_allocation_rows]
    targets_chart_values = [r["Recommended Capital Allocation"] for r in targets_allocation_rows]

    targets_chart = go.Figure(
        data=[
            go.Bar(
                x=targets_chart_labels,
                y=targets_chart_values,
                marker_color="rgba(76, 175, 80, 0.75)",
                hovertemplate="%{x}<br>$%{y:,.0f}<extra></extra>",
            )
        ]
    )
    targets_chart.update_layout(
        title="",
        xaxis_title="",
        yaxis_title="Allocated Capital ($)",
        height=380,
        margin=dict(l=10, r=10, t=20, b=80),
        xaxis_tickangle=-45,
        showlegend=False,
    )
    st.plotly_chart(targets_chart, use_container_width=True)

# ---- FULL-WIDTH TABLE SECTION ----
st.markdown("**Target-Based Allocation Summary**")

# Format data for cleaner display without warnings
targets_display_rows = []
for row in targets_allocation_rows:
    targets_display_rows.append({
        "Category": row["Category"],
        "Target Gross Sales": f"${row['Target Gross Sales']:,.2f}",
        "Target GP %": f"{row['Target GP %']:.1f}%",
        "GP Contribution": f"${row['GP Contribution']:,.2f}",
        "Allocation Weight (%)": f"{row['Allocation Weight (%)']:.2f}%",
        "Recommended Capital Allocation": f"${row['Recommended Capital Allocation']:,.2f}",
    })

st.dataframe(
    targets_display_rows,
    use_container_width=True,
    hide_index=True,
)