import streamlit as st
import math
import plotly.graph_objects as go
import plotly.express as px
import json
from pathlib import Path
import pandas as pd
from datetime import datetime

# Page configuration
st.set_page_config(page_title="Break Even Analysis", layout="wide")

# ===================== PHASE 2: POS-DRIVEN TURNOVER ESTIMATION =====================
# Helper functions for POS data processing (isolated, reusable)

def normalize_category_name(cat_name):
    """
    Normalize category names to handle variations in spacing and formatting.
    
    Rules:
    - Strip leading/trailing whitespace
    - Normalize hyphens and spaces: 'NON-EDIBLES' and 'NON EDIBLES' both map to 'NON_EDIBLES'
    - Convert to uppercase for consistent matching
    
    Examples:
    - 'NON-EDIBLES GROCERIES' -> 'NON_EDIBLES_GROCERIES'
    - 'NON EDIBLES GROCERIES ' -> 'NON_EDIBLES_GROCERIES'
    """
    if not isinstance(cat_name, str):
        return ""
    # Strip whitespace, convert to upper, replace hyphens with underscores
    return cat_name.strip().upper().replace('-', '_').replace(' ', '_')

@st.cache_data
def load_pos_data():
    """
    Load aggregated POS data from retail_pos_sales.xlsx.
    
    Expected columns: Category, Total_Net_Amount, Total_Quantity, 
    Avg_Unit_Cost_Original, Avg_New_Price, Avg_Profit_Margin
    
    Returns DataFrame or None if file not found/errors occur.
    """
    pos_file = Path(__file__).with_name("retail_pos_sales.xlsx")
    
    try:
        if not pos_file.exists():
            return None
        
        df = pd.read_excel(pos_file)
        
        # Validate required columns exist
        required_cols = ['Category', 'Total_Net_Amount']
        if not all(col in df.columns for col in required_cols):
            st.warning(f"⚠️ Missing required columns. Expected: {required_cols}")
            return None
        
        return df
    except Exception as e:
        st.warning(f"⚠️ Error loading POS data: {e}")
        return None




def _handle_turnover_change(category, turnover_unit, use_pos):
    """Handle turnover input changes - store manual value in session state."""
    key = f"turnover_cycles__{category}"
    value = st.session_state.get(key, 1.0)
    
    if not use_pos:
        # Store manual value when toggle is OFF
        st.session_state[f"manual_turnover__{category}"] = value
    else:
        # Update POS value if available
        pos_turnover, _ = calculate_pos_turnover(pos_transactions, category, 1000)
        if pos_turnover:
            st.session_state[f"pos_turnover__{category}"] = pos_turnover

def _handle_targets_turnover_change(category, turnover_unit, use_pos):
    """Handle turnover input changes for target-based allocation."""
    key = f"targets_turnover_cycles__{category}"
    value = st.session_state.get(key, 1.0)
    
    if not use_pos:
        # Store manual value when toggle is OFF
        st.session_state[f"targets_manual_turnover__{category}"] = value
    else:
        # Update POS value if available
        pos_turnover, _ = calculate_pos_turnover(pos_transactions, category, 1000)
        if pos_turnover:
            st.session_state[f"targets_pos_turnover__{category}"] = pos_turnover

# --- SYNC CALLBACKS ---
def sync_space_allocation():
    """Sync Target Space inputs with the Space Impact slider."""
    impact = st.session_state.get("space_impact_slider", 0.2)
    profit_weights = st.session_state.get("last_profit_weights", {})
    if not profit_weights:
        return
    for cat, p_weight in profit_weights.items():
        key = f"target_space_pct__{cat}"
        # Blend current space with profit weight based on impact
        # We assume 12.5 as baseline if not set
        current_space = st.session_state.get(key, 12.5) / 100.0
        new_space = (p_weight * (1.0 - impact) + current_space * impact) * 100.0
        st.session_state[key] = new_space

def sync_targets_space_allocation():
    """Sync Target Space inputs for target-based section with the slider."""
    impact = st.session_state.get("targets_space_impact_slider", 0.2)
    profit_weights = st.session_state.get("targets_last_profit_weights", {})
    if not profit_weights:
        return
    for cat, p_weight in profit_weights.items():
        key = f"targets_target_space_pct__{cat}"
        current_space = st.session_state.get(key, 12.5) / 100.0
        new_space = (p_weight * (1.0 - impact) + current_space * impact) * 100.0
        st.session_state[key] = new_space

def calculate_pos_turnover(pos_df, category_name, base_capital_allocation):
    """
    Estimate inventory turnover cycles from aggregated POS sales data.
    
    PHASE 2 LOGIC:
    - Uses aggregated category-level sales data (Total_Net_Amount)
    - Formula: turnover_cycles = Total_Net_Amount / base_capital_allocation
    - Clamped to 1-12 cycles per year (reasonable inventory bounds)
    - Category matching is normalized to handle spacing/hyphen variations
    
    Args:
        pos_df: DataFrame with aggregated POS data
        category_name: Category to look up
        base_capital_allocation: Base capital before turnover adjustment
    
    Returns:
        (turnover_cycles, is_pos_based): tuple where is_pos_based=True if 
        category found in POS data with valid sales, False otherwise
    """
    # Guard: no data available
    if pos_df is None or pos_df.empty:
        return None, False
    
    # Guard: missing Category column
    if 'Category' not in pos_df.columns:
        return None, False
    
    # Normalize input category name
    normalized_search = normalize_category_name(category_name)
    
    # Find matching category using normalized names
    # This handles: 'NON-EDIBLES GROCERIES' vs 'NON EDIBLES GROCERIES '
    for idx, row in pos_df.iterrows():
        if normalize_category_name(row['Category']) == normalized_search:
            total_sales = float(row['Total_Net_Amount'])
            
            # Guard: invalid or zero sales
            if total_sales <= 0:
                continue
            
            # Guard: invalid base allocation
            if base_capital_allocation <= 0:
                return None, False
            
            # Calculate turnover: annual sales velocity relative to capital required
            # This represents how many times inventory is replenished per year
            turnover_cycles = float(total_sales / base_capital_allocation)
            
            # Clamp to 1-12 range: inventory turns at least once/year, max 12x/year
            turnover_cycles = max(1.0, min(12.0, turnover_cycles))
            
            return float(turnover_cycles), True
    
    # No matching category found
    return None, False

# Load POS data once at app startup
pos_transactions = load_pos_data()

st.title("Break Even Analysis")

# POS Data Status
if pos_transactions is not None:
    st.success(f"✓ POS Data Active: {len(pos_transactions)} categories loaded from retail_pos_sales.xlsx")
else:
    st.info("⚠️ POS Data: Not available - using assumed turnover values")


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

# ---------- Branch / Store loader using products3.xlsx ----------
@st.cache_data
def load_store_space_from_products():
    """
    Load unique stores and their total shop floor space from products3.xlsx.
    Expects columns that can be interpreted as:
    - store_name / branch
    - total shop floor space (sqm)
    """
    products_file = Path(__file__).with_name("products3.xlsx")
    try:
        if not products_file.exists():
            return None

        df = pd.read_excel(products_file)

        col_map = {}
        for c in df.columns:
            lower = str(c).strip().lower()

            # Store / branch name - PRIORITIZE explicit name, EXCLUDE "no" / "number"
            if ("store" in lower or "branch" in lower) and ("name" in lower) and ("no" not in lower):
                col_map[c] = "store_name"
                continue
            
            # Fallback: if just "store" or "branch" but NOT "no"/"id"/"code"
            if ("store" in lower or "branch" in lower) and ("no" not in lower) and ("id" not in lower) and ("code" not in lower) and ("space" not in lower):
                col_map[c] = "store_name"
                continue

            # Total shop floor space
            if ("shop" in lower or "store" in lower) and ("space" in lower or "sqm" in lower or "floor" in lower):
                col_map[c] = "shop_space"
                continue

        if col_map:
            df = df.rename(columns=col_map)
        
        # CLEANUP: Remove potentially duplicated columns
        df = df.loc[:, ~df.columns.duplicated()]

        if "store_name" not in df.columns or "shop_space" not in df.columns:
            return None

        store_df = (
            df[["store_name", "shop_space"]]
            .dropna(subset=["store_name", "shop_space"])
            .drop_duplicates(subset=["store_name"])
        )
        return store_df
    except Exception:
        # Fail silently for this helper – UI will fall back to manual input
        return None

store_space_df = load_store_space_from_products()

# Inputs for this section only (independent of break-even)
total_capital_available = st.number_input(
    "Total Capital Available for New Stock",
    min_value=0.0,
    value=3_000_000.0,
    step=50_000.0,
    format="%.2f",
    help="Capital to allocate proportionally using Turnover-Adjusted GP Contribution weights (GP Contribution × Turnover Cycles)."
)

# Branch selector between capital and floor space
selected_branch = None
if store_space_df is not None and not store_space_df.empty:
    # Ensure we have a Series (df["store_name"] can be a DataFrame if duplicate column names exist)
    store_col = store_space_df["store_name"]
    if isinstance(store_col, pd.DataFrame):
        store_col = store_col.iloc[:, 0]
    branch_options = sorted(store_col.astype(str).unique())
    
    # Session state for branch logic
    if "last_selected_branch" not in st.session_state:
        st.session_state["last_selected_branch"] = None

    selected_branch = st.selectbox(
        "Select Branch / Store",
        options=branch_options,
        index=None,
        placeholder="Choose an option",
        key="branch_select",
        help="Choose a branch to auto-fill its total shop floor space and drive store-specific product recommendations."
    )
    
    # Check for change and update space input
    if selected_branch != st.session_state["last_selected_branch"]:
        st.session_state["last_selected_branch"] = selected_branch
        # Fetch space for this branch
        match = store_space_df.loc[store_space_df["store_name"] == selected_branch, "shop_space"]
        if not match.empty:
            try:
                new_space = float(match.iloc[0])
                st.session_state["total_shop_space_input"] = new_space
            except:
                pass

# Shelf Space Inputs
col_space1, col_space2 = st.columns(2, gap="medium")
with col_space1:
    # Use key to allow programmatic update from branch selection
    # Initialize default ONLY if not in session state
    if "total_shop_space_input" not in st.session_state:
        st.session_state["total_shop_space_input"] = 1000.0
        
    total_shop_space = st.number_input(
        "Total Shop Floor Space (sqm)",
        min_value=400.0,
        max_value=8000.0,
        key="total_shop_space_input", # Key binds logic to session state
        step=50.0,
        help="Total available shelf space in square meters for the selected branch. You can override this manually."
    )
with col_space2:
    space_impact = st.slider(
        "Space Impact on Allocation",
        min_value=0.0,
        max_value=1.0,
        value=0.2,
        help="How much 'Space' influences allocation vs 'Turnover/Profit'. 0% = Pure Profit optimization. 100% = Pure Space filling.",
        key="space_impact_slider",
        on_change=sync_space_allocation
    )

# Turnover time unit selector - REMOVED (Fixed to Monthly)
turnover_unit = "Per Month"

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
            "turnover_cycles_per_year": float(cfg.get("turnover_cycles_per_year", 1.0)),
            "rationale": str(cfg.get("rationale", "")).strip(),
        }
    )


st.caption(
    "This optimiser is fully independent from the break-even section above. "
    "Category list, Gross Sales, and default Target GP% are loaded from `category_gp_config.json`. "
    "**Allocation weights are based on Turnover-Adjusted GP Contribution** (GP Contribution × Turnover Cycles), "
    "prioritizing categories that generate profit over time rather than just high margin per unit."
)

inputs_col, outputs_col = st.columns([0.45, 0.55], gap="large")

with inputs_col:
    st.markdown("**Category inputs**")
    
    header_c1, header_c2, header_c3, header_c4, header_c6 = st.columns([0.25, 0.18, 0.15, 0.15, 0.27], gap="small")
    with header_c1:
        st.markdown("**Category**")
    with header_c2:
        st.markdown("**Gross Sales**")
    with header_c3:
        st.markdown("**Tgt GP %**")
    with header_c4:
        st.markdown("**Tgt Space %**")
    with header_c6:
        st.markdown(f"**Turnover (Cycles/Mo)**")

    target_gp_pct_by_category = {}
    target_space_pct_by_category = {} # New
    gross_sales_by_category = {}
    turnover_cycles_by_category = {}

    for rec in categories:
        category = rec["category"]
        gross_sales = rec["gross_sales"]
        
        # Get default turnover in cycles per year from config
        default_annual_cycles = rec["turnover_cycles_per_year"]
        
        # Convert annual cycles to Monthly for default input
        default_input_value = default_annual_cycles / 12.0

        gross_sales_by_category[category] = gross_sales

        row_c1, row_c2, row_c3, row_c4, row_c6 = st.columns([0.25, 0.18, 0.15, 0.15, 0.27], gap="small")

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

        with row_c4:
            # Default space allocation proportional to sales (approx)
            # This is a heuristic default; user can override
            if f"target_space_pct__{category}" not in st.session_state:
                 # Calculate heuristic only if not in state to avoid overwrite
                 pass 
            
            target_space_pct_by_category[category] = st.number_input(
                "Tgt Space %",
                min_value=0.0,
                max_value=100.0,
                # Initialize with 12.5 if not already in session state
                value=st.session_state.get(f"target_space_pct__{category}", 12.5),
                step=0.5,
                format="%.1f",
                key=f"target_space_pct__{category}",
                label_visibility="collapsed"
            )

        # Hardcoded to True since toggle is removed
        use_pos = True

        with row_c6:
            # Get POS turnover for this category (to show in input when toggle is ON)
            pos_turnover_for_display, _ = calculate_pos_turnover(pos_transactions, category, gross_sales * 0.1) if pos_transactions is not None else (None, False)
            
            # Initialize session state for POS value and manual value if not exists
            if f"pos_turnover__{category}" not in st.session_state:
                st.session_state[f"pos_turnover__{category}"] = pos_turnover_for_display if pos_turnover_for_display else default_annual_cycles
            if f"manual_turnover__{category}" not in st.session_state:
                st.session_state[f"manual_turnover__{category}"] = default_input_value
            
            # Determine which value to use based on toggle
            if use_pos:
                # When POS toggle is ON, use POS value (Annual / 12 -> Monthly)
                pos_annual = st.session_state.get(f"pos_turnover__{category}", default_annual_cycles)
                display_value = pos_annual / 12.0
            else:
                # When toggle is OFF, use manual value
                display_value = st.session_state.get(f"manual_turnover__{category}", default_input_value)
            
            # Number input for turnover cycles
            turnover_input = st.number_input(
                "Turnover Cycles",
                min_value=0.01,
                max_value=365.0,
                value=float(display_value),
                step=0.1,
                format="%.1f",
                key=f"turnover_cycles__{category}",
                label_visibility="collapsed",
                on_change=_handle_turnover_change,
                args=(category, turnover_unit, use_pos),
            )
            
            # Store the manual value when toggle is OFF
            if not use_pos:
                st.session_state[f"manual_turnover__{category}"] = turnover_input
            
            # Store POS value for future use
            if pos_turnover_for_display:
                st.session_state[f"pos_turnover__{category}"] = pos_turnover_for_display
            
            # Store as Monthly cycles
            turnover_cycles_by_category[category] = turnover_input

with outputs_col:
    # Compute GP contributions (independent of break-even)
    gp_contribution_by_category = {
        c: gross_sales_by_category[c] * (target_gp_pct_by_category[c] / 100.0)
        for c in gross_sales_by_category
    }
    
    # STEP 1: Determine effective turnover for each category BEFORE calculating weights
    # This allows us to incorporate turnover into the allocation weight calculation
    category_turnover_data = {}
    for c in gross_sales_by_category:
        # Get default turnover from config (in annual cycles)
        default_annual_cycles = next(
            (rec["turnover_cycles_per_year"] for rec in categories if rec["category"] == c),
            1.0
        )
        
        # Get user-entered turnover (in selected time unit, converted to annual)
        user_entered_annual = turnover_cycles_by_category.get(c, default_annual_cycles)
        
        # Check if user explicitly wants POS or ASSUMED
        use_pos = st.session_state.get(f"use_pos__{c}", True)
        
        # Estimate base allocation for POS calculation (use a preliminary estimate)
        preliminary_gp_contrib = gp_contribution_by_category[c]
        preliminary_total_gp = sum(gp_contribution_by_category.values())
        preliminary_weight = (preliminary_gp_contrib / preliminary_total_gp) if preliminary_total_gp > 0 else 0.0
        preliminary_base_allocation = total_capital_available * preliminary_weight
        
        # New: Space Weight
        target_space = target_space_pct_by_category.get(c, 0.0)
        # Normalize inputs? For now assume they sum roughly to 100, but we'll re-normalize weights later.

        # PHASE 2: Priority logic based on toggle
        if use_pos:
            # Try POS data first
            pos_turnover, is_pos_based = calculate_pos_turnover(pos_transactions, c, preliminary_base_allocation)
            if pos_turnover is not None:
                # pos_turnover comes as ANNUAL, convert to MONTHLY for calculations
                effective_turnover_cycles = pos_turnover / 12.0
                turnover_source = "POS_ESTIMATED"
            else:
                # Fall back to config default when POS not available (Annual / 12)
                effective_turnover_cycles = max(default_annual_cycles / 12.0, 0.08)
                turnover_source = "ASSUMED (no POS)"
        else:
            # Use user-entered/manual value (Already Monthly)
            effective_turnover_cycles = max(user_entered_annual, 0.08)
            turnover_source = "ASSUMED"
        
        category_turnover_data[c] = {
            "turnover_cycles": effective_turnover_cycles,
            "source": turnover_source
        }
    
    # STEP 2: Calculate Turnover-Adjusted GP Contribution = GP Contribution × Turnover Cycles
    # This rewards categories that generate profit over time (high margin × high turnover)
    turnover_adjusted_gp_by_category = {
        c: gp_contribution_by_category[c] * category_turnover_data[c]["turnover_cycles"]
        for c in gross_sales_by_category
    }
    total_turnover_adjusted_gp = sum(turnover_adjusted_gp_by_category.values())
    
    # Calculate Total Target Space % (to normalize space weights)
    total_target_space_pct = sum(target_space_pct_by_category.values())

    # STEP 3: Calculate allocation weights based on Blended Logic
    allocation_rows = []
    
    # Pre-calculate to allow normalization
    temp_weights = {}
    for c in gross_sales_by_category:
        # 1. Profit Weight (Turnover-Adjusted GP)
        turnover_adj_gp = turnover_adjusted_gp_by_category[c]
        profit_weight = (turnover_adj_gp / total_turnover_adjusted_gp) if total_turnover_adjusted_gp > 0 else 0.0
        
        # 2. Space Weight (Target Space %)
        space_pct = target_space_pct_by_category[c]
        space_weight = (space_pct / total_target_space_pct) if total_target_space_pct > 0 else 0.0
        
        # 3. Blended Weight
        # If Impact = 0, Weight = Profit Weight. If Impact = 1, Weight = Space Weight.
        final_weight = (profit_weight * (1.0 - space_impact)) + (space_weight * space_impact)
        temp_weights[c] = final_weight
    
    # Store profit weights for sync callback
    st.session_state["last_profit_weights"] = {
        c: (turnover_adjusted_gp_by_category[c] / total_turnover_adjusted_gp) if total_turnover_adjusted_gp > 0 else 0.0
        for c in gross_sales_by_category
    }

    # Normalize final weights to ensure they sum to 1.0
    total_final_weight = sum(temp_weights.values())
    
    for c in gross_sales_by_category:
        try:
            gp_contrib = gp_contribution_by_category[c]
            turnover_cycles = category_turnover_data[c]["turnover_cycles"]
            turnover_source = category_turnover_data[c]["source"]
            target_space_pct = target_space_pct_by_category[c]
            
            turnover_adj_gp = turnover_adjusted_gp_by_category[c]
            
            # Normalized Weight
            weight = (temp_weights[c] / total_final_weight) if total_final_weight > 0 else 0.0
            
            # Base capital allocation based on turnover-adjusted weights
            # This is now the "Effective Capital Required" as per user request
            effective_capital_required = total_capital_available * weight

            # Calculate Stock Density ($/sqm) - REMOVED
            # category_space_sqm = total_shop_space * (target_space_pct / 100.0)
            # stock_density = (effective_capital_required / category_space_sqm) if category_space_sqm > 0 else 0.0

            allocation_rows.append(
                {
                    "Category": c,
                    "Gross Sales": gross_sales_by_category[c],
                    "Target GP %": target_gp_pct_by_category[c],
                    "Target Space %": target_space_pct,
                    "GP Contribution": gp_contrib,
                    "Turnover (Monthly)": float(turnover_cycles),
                    "Turnover-Adjusted GP": float(turnover_adj_gp),
                    "Turnover Source": turnover_source,
                    "Allocation Weight (%)": weight * 100.0,
                    "Effective Capital Required": float(effective_capital_required), # Renamed from Base
                    # "Stock Density ($/sqm)": float(stock_density)
                }
            )
        except Exception as e:
            st.error(f"Error processing category {c}: {e}")
            continue

    if allocation_rows:
        # Bar chart: capital allocation by category
        st.markdown("**Allocation by Category**")
        
        chart_labels = [r["Category"] for r in allocation_rows]
        chart_values = [r["Effective Capital Required"] for r in allocation_rows]

        try:
            chart = go.Figure(
                data=[
                    go.Bar(
                        x=chart_labels,
                        y=chart_values,
                        marker_color="rgba(135, 206, 235, 0.75)",
                        hovertemplate="%{x}<br>$%{y:,.0f}<extra></extra>",
                    )
                ]
            )
            chart.update_layout(
                title="",
                xaxis_title="",
                yaxis_title="Effective Capital Required ($)",
                height=380,
                margin=dict(l=10, r=10, t=20, b=80),
                xaxis_tickangle=-45,
                showlegend=False,
            )
            st.plotly_chart(chart, use_container_width=True)
        except Exception as e:
            st.error(f"Error rendering chart: {e}")
    else:
        st.warning("No allocation data available to display")

# ---- FULL-WIDTH TABLE SECTION ----
st.markdown("**Recommended Allocation Summary**")

# Display the selected time unit and explain allocation logic
st.caption(
    f"**Allocation Logic:** Weights are based on **Turnover-Adjusted GP Contribution** (GP Contribution × Turnover Cycles). "
    f"This prioritizes categories that generate profit over time (high margin × high turnover). "
    f"Turnover cycles measured: **Monthly**"
)

# Format data for cleaner display without warnings
if allocation_rows:
    display_rows = []
    for row in allocation_rows:
        display_turnover = row['Turnover (Monthly)']
        
        display_rows.append({
            "Category": row["Category"],
            "Gross Sales": f"${row['Gross Sales']:,.2f}",
            "Target GP %": f"{row['Target GP %']:.1f}%",
            "Target Space %": f"{row['Target Space %']:.1f}%",
            "GP Contribution": f"${row['GP Contribution']:,.2f}",
            "Turnover (Cycles/Month)": f"{display_turnover:.2f}",
            "Turnover-Adjusted GP": f"${row['Turnover-Adjusted GP']:,.2f}",
            "Allocation Weight (%)": f"{row['Allocation Weight (%)']:.2f}%",
            "Effective Capital Required": f"${row['Effective Capital Required']:,.2f}",
        })
        
        # Capture Capital Limit for this Category
        norm_cat_key = normalize_category_name(row["Category"])
        # Store in a temporary dict to update session state later
        if "category_capital_limits" not in st.session_state:
            st.session_state["category_capital_limits"] = {}
        st.session_state["category_capital_limits"][norm_cat_key] = row['Effective Capital Required']

    st.dataframe(
        display_rows,
        use_container_width=True,
        hide_index=True,
    )

# ===================== NEW MODULE: PARETO PRODUCT ALLOCATION =====================
st.divider()
st.subheader("Products")

st.caption(
    "Select a category to view the top-performing products that contribute to 80% of sales revenue. "
    "Recommended stocking quantities are calculated based on the **Turnover Cycles** determined in the section above."
)

# 1. Load Product Data
@st.cache_data
def load_product_data(target_branch=None):
    # Use products3.xlsx as the source dataset for Pareto + branch logic
    products_file = Path(__file__).with_name("products3.xlsx")
    try:
        if not products_file.exists():
            st.warning("products3.xlsx not found.")
            return []
        
        df = pd.read_excel(products_file)

        # --- Flexible column mapping for products3.xlsx ---
        col_map = {}
        for c in df.columns:
            lower = c.strip().lower()
            norm = lower.replace(" ", "_")

            # Store / branch name
            if ("store" in lower or "branch" in lower) and ("name" in lower) and ("no" not in lower):
                col_map[c] = "store_name"
                continue
            
            if ("store" in lower or "branch" in lower) and ("no" not in lower) and ("id" not in lower) and ("code" not in lower) and ("space" not in lower):
                col_map[c] = "store_name"
                continue

            # Total shop floor space
            if ("shop" in lower or "store" in lower) and ("space" in lower or "sqm" in lower or "floor" in lower):
                col_map[c] = "shop_space"
                continue

            # Category-like
            if "category" in lower or "dept" in lower or "department" in lower:
                col_map[c] = "category"
                continue

            # Product / item description
            if "product" in lower or "item" in lower or "sku" in lower or "description" in lower:
                col_map[c] = "product"
                continue

            # Quantity / units sold / volume
            if "qty" in lower or "quantity" in lower or "units" in lower or "volume" in lower:
                col_map[c] = "quantity"
                continue

            # Selling / unit price
            if "price" in lower or "selling" in lower or ("unit" in lower and "cost" not in lower):
                col_map[c] = "price"
                continue

            # Transaction / sales date
            if "date" in lower or "trans_date" in norm or "transaction" in lower:
                col_map[c] = "date"
                continue

        if col_map:
            df = df.rename(columns=col_map)
        
        # Validation after mapping
        required_cols = ['category', 'product', 'quantity', 'price', 'date']
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            st.warning(f"products3.xlsx is missing required columns even after mapping: {missing}.")
            return []

        # CLEANUP: Remove potentially duplicated columns
        df = df.loc[:, ~df.columns.duplicated()]

        # --- BRANCH FILTERING ---
        if target_branch:
            if 'store_name' in df.columns:
                mask = df['store_name'].astype(str).str.strip().str.lower() == str(target_branch).strip().lower()
                df = df.loc[mask]
                
                if df.empty:
                    st.warning(f"No data found for branch: {target_branch}")
                    return []
            else:
                st.warning("Data does not contain 'store_name' column, cannot filter by branch.")

        # FORCE POSITIVE quantities
        if 'quantity' in df.columns:
            df['quantity'] = df['quantity'].abs()

        # Convert date to datetime
        df['date'] = pd.to_datetime(df['date'])
        
        # Calculate Date Range for Monthly Normalization
        min_date = df['date'].min()
        max_date = df['date'].max()
        days_diff = (max_date - min_date).days
        months_diff = max(1.0, days_diff / 30.0) 

        # normalize category names
        df.loc[:, 'category_norm'] = df['category'].apply(normalize_category_name)

        # Aggregate by Product + Category
        df['revenue_txn'] = df['quantity'] * df['price']
        
        agg_funcs = {
            'revenue_txn': 'sum',
            'quantity': 'sum',
            'price': 'mean',
        }
        if 'shop_space' in df.columns:
            agg_funcs['shop_space'] = 'max'

        group_cols = ['product', 'category_norm']
        if 'store_name' in df.columns:
            group_cols.insert(0, 'store_name')
        
        product_agg = (
            df.groupby(group_cols)
              .agg(agg_funcs)
              .reset_index()
        )
        
        products_list = []
        for _, row in product_agg.iterrows():
            total_qty = row['quantity']
            monthly_vol = total_qty / months_diff
            
            p_obj = {
                "name": row['product'],
                "category": row['category_norm'],
                "unit_cost": 0.0,
                "selling_price": row['price'],
                "monthly_sales_volume": monthly_vol,
            }
            if 'store_name' in product_agg.columns:
                p_obj["store_name"] = row['store_name']
            if 'shop_space' in product_agg.columns:
                p_obj["shop_space"] = row.get('shop_space', None)
            products_list.append(p_obj)
        
        return products_list
            
    except Exception as e:
        st.error(f"Error loading products3.xlsx: {e}")
        return []

# Pass selected branch to load_product_data to trigger filtering and cache refresh
target_branch = st.session_state.get("branch_select")
all_products = load_product_data(target_branch)

# 2. Category Selector
pareto_col1, pareto_col2 = st.columns([0.3, 0.7], gap="medium")

with pareto_col1:
    # Use normalized categories from config for dropdown to ensure matching
    category_options = [rec["category"] for rec in categories]
    selected_pareto_category = st.selectbox("Select Category", options=category_options)

    # 3. Get Turnover info
    use_pos_state = st.session_state.get(f"use_pos__{selected_pareto_category}", True)
    
    if use_pos_state:
        pareto_turnover_annual = st.session_state.get(f"pos_turnover__{selected_pareto_category}", 12.0)
        pareto_turnover_monthly = pareto_turnover_annual / 12.0
    else:
        pareto_turnover_monthly = st.session_state.get(f"manual_turnover__{selected_pareto_category}", 1.0)
    


with pareto_col2:
        if all_products:
            # Filter products by Category (normalized) and optionally by selected Branch / Store
            selected_branch = st.session_state.get("branch_select")
            norm_cat = normalize_category_name(selected_pareto_category)

            category_products = []
            for p in all_products:
                if p["category"] != norm_cat:
                    continue
                if selected_branch and p.get("store_name") and str(p.get("store_name")) != str(selected_branch):
                    continue
                category_products.append(p)
            
            # Retrieve Capital Limit for this Category
            cat_capital_limit = st.session_state.get("category_capital_limits", {}).get(norm_cat, 0.0)

            if category_products:
                # Calculate Revenue (Price * Volume)
                product_analysis = []
                total_category_revenue = 0.0
                
                for p in category_products:
                    revenue = p["selling_price"] * p["monthly_sales_volume"]
                    total_category_revenue += revenue
                    product_analysis.append({
                        **p,
                        "revenue": revenue
                    })
                
                # Sort by Revenue Descending
                product_analysis.sort(key=lambda x: x["revenue"], reverse=True)
                
                # Pareto Logic
                pareto_products = []
                cumulative_revenue = 0.0
                
                # Display Limit Info
                st.info(f"**Capital Budget for {selected_pareto_category}:** ${cat_capital_limit:,.2f} (Derived from Allocation Table)")

                for p in product_analysis:
                    cumulative_revenue += p["revenue"]
                    cumulative_pct = (cumulative_revenue / total_category_revenue) if total_category_revenue > 0 else 0
                    
                    # --- PROPORTIONAL ALLOCATION LOGIC ---
                    sales_share = (p["revenue"] / total_category_revenue) if total_category_revenue > 0 else 0
                    allocated_capital = sales_share * cat_capital_limit
                    
                    if p["selling_price"] > 0:
                        recommended_qty = allocated_capital / p["selling_price"]
                    else:
                        recommended_qty = 0
                    
                    recommended_qty = max(0, recommended_qty)
                    capital_needed = recommended_qty * p["selling_price"]
                    
                    pareto_row = {
                        "Product Name": p["name"],
                        "Selling Price": p["selling_price"],
                        "Monthly Sales Vol": p["monthly_sales_volume"],
                        "Revenue Contribution": p["revenue"],
                        "Share of Sales": sales_share,
                        "Rec. Order Qty": math.ceil(recommended_qty),
                        "Capital Allocated": capital_needed,
                    }
                    pareto_products.append(pareto_row)
                
                st.markdown(f"**Product Stocking Recommendations (Sales-Weighted)**")
                
                pareto_display = []
                for row in pareto_products:
                    pareto_display.append({
                        "Product Name": row["Product Name"],
                        "Rec. Order Qty": f"{row['Rec. Order Qty']:,}",
                        "Capital Allocated": f"${row['Capital Allocated']:,.2f}",
                    })
                
                st.dataframe(
                    pareto_display, 
                    use_container_width=True,
                    hide_index=True
                )
            else:
                if norm_cat == "AIRTIME":
                    st.info(f"**Capital Budget for AIRTIME:** ${cat_capital_limit:,.2f}")
                    st.write("Airtime allocation is strictly based on the simplified capital limit above. No individual product breakdown is needed.")
                else:
                    st.warning(f"No products found for category: {selected_pareto_category} (Normalized: {normalize_category_name(selected_pareto_category)})")
        else:
            st.error("No product data loaded or products3.xlsx is empty.")

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
            "turnover_cycles_per_year": float(cfg.get("turnover_cycles_per_year", 1.0)),
            "rationale": str(cfg.get("rationale", "")).strip(),
        }
    )

st.caption(
    "This module is fully independent and calculates capital allocation based on target gross sales and target GP percentages. "
    "**Allocation weights are based on Turnover-Adjusted GP Contribution** (GP Contribution × Turnover Cycles), "
    "prioritizing categories that generate profit over time rather than just high margin per unit."
)

# Input for total capital
targets_total_capital = st.number_input(
    "Total Capital Available for Target-Based Allocation",
    min_value=0.0,
    value=3_000_000.0,
    step=50_000.0,
    format="%.2f",
    help="Capital to allocate based on Turnover-Adjusted GP Contribution weights (GP Contribution × Turnover Cycles).",
    key="targets_total_capital_input"
)
# Shelf Space Inputs
col_targets_space1, col_targets_space2 = st.columns(2, gap="medium")
with col_targets_space1:
    targets_total_shop_space = st.number_input(
        "Total Shop Floor Space (sqm)",
        min_value=400.0,
        max_value=8000.0,
        value=1000.0,
        step=50.0,
        help="Total available shelf space in square meters.",
        key="targets_total_shop_space"
    )
with col_targets_space2:
    targets_space_impact = st.slider(
        "Space Impact on Allocation",
        min_value=0.0,
        max_value=1.0,
        value=0.2,
        help="How much 'Space' influences allocation vs 'Turnover/Profit'.",
        key="targets_space_impact_slider",
        on_change=sync_targets_space_allocation
    )

# Turnover time unit selector - REMOVED (Fixed to Monthly)
targets_turnover_unit = "Per Month"

targets_inputs_col, targets_outputs_col = st.columns([0.45, 0.55], gap="large")

with targets_inputs_col:
    st.markdown("**Category Targets**")
    
    # Column headers
    header_c1, header_c2, header_c3, header_c4, header_c6 = st.columns([0.25, 0.18, 0.15, 0.15, 0.27], gap="small")
    with header_c1:
        st.markdown("**Category**")
    with header_c2:
        st.markdown("**Target Sales**")
    with header_c3:
        st.markdown("**Tgt GP %**")
    with header_c4:
        st.markdown("**Tgt Space %**")
    with header_c6:
        st.markdown(f"**Turnover (Cycles/Mo)**")

    targets_target_gp_pct_by_category = {}
    targets_target_space_pct_by_category = {}
    targets_target_gross_sales_by_category = {}
    targets_turnover_cycles_by_category = {}

    for rec in targets_categories:
        category = rec["category"]
        target_gross_sales = rec["target_gross_sales"]
        
        # Get default turnover in cycles per year from config
        default_annual_cycles = rec["turnover_cycles_per_year"]
        
        # Convert annual cycles to Monthly for default input
        default_input_value = default_annual_cycles / 12.0

        targets_target_gross_sales_by_category[category] = target_gross_sales

        targets_target_gross_sales_by_category[category] = target_gross_sales

        targets_row_c1, targets_row_c2, targets_row_c3, targets_row_c4, targets_row_c6 = st.columns([0.25, 0.18, 0.15, 0.15, 0.27], gap="small")

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

        with targets_row_c4:
            # Default space allocation
            targets_target_space_pct_by_category[category] = st.number_input(
                "Tgt Space %",
                min_value=0.0,
                max_value=100.0,
                value=st.session_state.get(f"targets_target_space_pct__{category}", 12.5), 
                step=0.5,
                format="%.1f",
                key=f"targets_target_space_pct__{category}",
                label_visibility="collapsed"
            )

        # Hardcoded to True since toggle is removed
        targets_use_pos = True

        with targets_row_c6:
            # Get POS turnover for this category (to show in input when toggle is ON)
            pos_turnover_for_display, _ = calculate_pos_turnover(pos_transactions, category, target_gross_sales * 0.1) if pos_transactions is not None else (None, False)
            
            # Initialize session state for POS value and manual value if not exists
            if f"targets_pos_turnover__{category}" not in st.session_state:
                st.session_state[f"targets_pos_turnover__{category}"] = pos_turnover_for_display if pos_turnover_for_display else default_annual_cycles
            if f"targets_manual_turnover__{category}" not in st.session_state:
                st.session_state[f"targets_manual_turnover__{category}"] = default_input_value
            
            # Determine which value to use based on toggle
            if targets_use_pos:
                # When POS toggle is ON, use POS value (Annual / 12 -> Monthly)
                pos_annual = st.session_state.get(f"targets_pos_turnover__{category}", default_annual_cycles)
                display_value = pos_annual / 12.0
            else:
                # When toggle is OFF, use manual value
                display_value = st.session_state.get(f"targets_manual_turnover__{category}", default_input_value)
            
            # Number input for turnover cycles
            turnover_input = st.number_input(
                "Turnover Cycles",
                min_value=0.01,
                max_value=365.0,
                value=float(display_value),
                step=0.1,
                format="%.1f",
                key=f"targets_turnover_cycles__{category}",
                label_visibility="collapsed",
                on_change=_handle_targets_turnover_change,
                args=(category, targets_turnover_unit, targets_use_pos),
            )
            
            # Store the manual value when toggle is OFF
            if not targets_use_pos:
                st.session_state[f"targets_manual_turnover__{category}"] = turnover_input
            
            # Store POS value for future use
            if pos_turnover_for_display:
                st.session_state[f"targets_pos_turnover__{category}"] = pos_turnover_for_display
            
            # Store as Monthly cycles
            targets_turnover_cycles_by_category[category] = turnover_input

with targets_outputs_col:
    # Compute target GP contributions
    targets_gp_contribution_by_category = {
        c: targets_target_gross_sales_by_category[c] * (targets_target_gp_pct_by_category[c] / 100.0)
        for c in targets_target_gross_sales_by_category
    }
    
    # STEP 1: Determine effective turnover for each category BEFORE calculating weights
    # This allows us to incorporate turnover into the allocation weight calculation
    targets_category_turnover_data = {}
    for c in targets_target_gross_sales_by_category:
        # Get default turnover from config (in annual cycles)
        default_annual_cycles = next(
            (rec["turnover_cycles_per_year"] for rec in targets_categories if rec["category"] == c),
            1.0
        )
        
        # Get user-entered turnover (in selected time unit, converted to annual)
        user_entered_annual = targets_turnover_cycles_by_category.get(c, default_annual_cycles)
        
        # Check if user explicitly wants POS or ASSUMED
        targets_use_pos = st.session_state.get(f"targets_use_pos__{c}", True)
        
        # Estimate base allocation for POS calculation (use a preliminary estimate)
        preliminary_gp_contrib = targets_gp_contribution_by_category[c]
        preliminary_total_gp = sum(targets_gp_contribution_by_category.values())
        preliminary_weight = (preliminary_gp_contrib / preliminary_total_gp) if preliminary_total_gp > 0 else 0.0
        preliminary_base_allocation = targets_total_capital * preliminary_weight
        
        # PHASE 2: Priority logic based on toggle
        if targets_use_pos:
            # Try POS data first
            pos_turnover, is_pos_based = calculate_pos_turnover(pos_transactions, c, preliminary_base_allocation)
            if pos_turnover is not None:
                # Annual -> Monthly
                targets_effective_turnover_cycles = pos_turnover / 12.0
                targets_turnover_source = "POS_ESTIMATED"
            else:
                # Fall back to config default when POS not available (Annual -> Monthly)
                targets_effective_turnover_cycles = max(default_annual_cycles / 12.0, 0.08)
                targets_turnover_source = "ASSUMED (no POS)"
        else:
            # Use user-entered/manual value (Already Monthly)
            targets_effective_turnover_cycles = max(user_entered_annual, 0.08)
            targets_turnover_source = "ASSUMED"
        
        targets_category_turnover_data[c] = {
            "turnover_cycles": targets_effective_turnover_cycles,
            "source": targets_turnover_source
        }
    
    # STEP 2: Calculate Turnover-Adjusted GP Contribution = GP Contribution × Turnover Cycles
    # This rewards categories that generate profit over time (high margin × high turnover)
    targets_turnover_adjusted_gp_by_category = {
        c: targets_gp_contribution_by_category[c] * targets_category_turnover_data[c]["turnover_cycles"]
        for c in targets_target_gross_sales_by_category
    }
    targets_total_turnover_adjusted_gp = sum(targets_turnover_adjusted_gp_by_category.values())
    
    # Calculate Total Target Space % (to normalize space weights)
    targets_total_target_space_pct = sum(targets_target_space_pct_by_category.values())

    # STEP 3: Calculate allocation weights based on Blended Logic
    targets_allocation_rows = []
    
    # Pre-calculate to allow normalization
    targets_temp_weights = {}
    for c in targets_target_gross_sales_by_category:
        # 1. Profit Weight
        turnover_adj_gp = targets_turnover_adjusted_gp_by_category[c]
        profit_weight = (turnover_adj_gp / targets_total_turnover_adjusted_gp) if targets_total_turnover_adjusted_gp > 0 else 0.0
        
        # 2. Space Weight
        space_pct = targets_target_space_pct_by_category[c]
        space_weight = (space_pct / targets_total_target_space_pct) if targets_total_target_space_pct > 0 else 0.0
        
        # 3. Blended Weight
        final_weight = (profit_weight * (1.0 - targets_space_impact)) + (space_weight * targets_space_impact)
        targets_temp_weights[c] = final_weight

    # Store profit weights for sync callback
    st.session_state["targets_last_profit_weights"] = {
        c: (targets_turnover_adjusted_gp_by_category[c] / targets_total_turnover_adjusted_gp) if targets_total_turnover_adjusted_gp > 0 else 0.0
        for c in targets_target_gross_sales_by_category
    }

    # Normalize final weights
    targets_total_final_weight = sum(targets_temp_weights.values())

    for c in targets_target_gross_sales_by_category:
        try:
            targets_gp_contrib = targets_gp_contribution_by_category[c]
            targets_turnover_cycles = targets_category_turnover_data[c]["turnover_cycles"]
            targets_turnover_source = targets_category_turnover_data[c]["source"]
            targets_target_space_pct = targets_target_space_pct_by_category[c]
            
            targets_turnover_adj_gp = targets_turnover_adjusted_gp_by_category[c]
            
            # Normalized Weight
            targets_weight = (targets_temp_weights[c] / targets_total_final_weight) if targets_total_final_weight > 0 else 0.0
            
            # Base capital allocation based on turnover-adjusted weights
            # Renamed to Effective Capital Required
            targets_effective_capital_required = targets_total_capital * targets_weight
            
            # Calculate Stock Density ($/sqm) - REMOVED
            # targets_category_space_sqm = targets_total_shop_space * (targets_target_space_pct / 100.0)
            # targets_stock_density = (targets_effective_capital_required / targets_category_space_sqm) if targets_category_space_sqm > 0 else 0.0

            targets_allocation_rows.append(
                {
                    "Category": c,
                    "Target Gross Sales": targets_target_gross_sales_by_category[c],
                    "Target GP %": targets_target_gp_pct_by_category[c],
                    "Target Space %": targets_target_space_pct,
                    "GP Contribution": targets_gp_contrib,
                    "Turnover (Monthly)": float(targets_turnover_cycles),
                    "Turnover-Adjusted GP": float(targets_turnover_adj_gp),
                    "Turnover Source": targets_turnover_source,
                    "Allocation Weight (%)": targets_weight * 100.0,
                    "Effective Capital Required": float(targets_effective_capital_required), # Renamed
                    # "Stock Density ($/sqm)": float(targets_stock_density)
                }
            )
        except Exception as e:
            st.error(f"Error processing category {c}: {e}")
            continue

    if targets_allocation_rows:
        # Bar chart: target-based capital allocation by category
        st.markdown("**Target Allocation by Category**")
        
        targets_chart_labels = [r["Category"] for r in targets_allocation_rows]
        targets_chart_values = [r["Effective Capital Required"] for r in targets_allocation_rows]

        try:
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
                yaxis_title="Effective Capital Required ($)",
                height=380,
                margin=dict(l=10, r=10, t=20, b=80),
                xaxis_tickangle=-45,
                showlegend=False,
            )
            st.plotly_chart(targets_chart, use_container_width=True)
        except Exception as e:
            st.error(f"Error rendering target chart: {e}")
    else:
        st.warning("No target allocation data available to display")

# ---- FULL-WIDTH TABLE SECTION ----
st.markdown("**Target-Based Allocation Summary**")

# Display the selected time unit and explain allocation logic
st.caption(
    f"**Allocation Logic:** Weights are based on a blend of **Turnover-Adjusted GP** (Profit) and **Target Space** (Shelf Filling). "
    f"Space Impact: **{targets_space_impact*100:.0f}%**. "
    f"Turnover cycles measured: **Monthly** | Turnover Source: **POS_ESTIMATED** (actual sales velocity) or **ASSUMED** (config default)"
)

if targets_allocation_rows:
    # Format data for cleaner display without warnings
    targets_display_rows = []
    for row in targets_allocation_rows:
        display_turnover = row['Turnover (Monthly)']
        
        targets_display_rows.append({
            "Category": row["Category"],
            "Target Gross Sales": f"${row['Target Gross Sales']:,.2f}",
            "Target GP %": f"{row['Target GP %']:.1f}%",
            "Target Space %": f"{row['Target Space %']:.1f}%",
            "GP Contribution": f"${row['GP Contribution']:,.2f}",
            "Turnover (Cycles/Month)": f"{display_turnover:.2f}",
            "Turnover-Adjusted GP": f"${row['Turnover-Adjusted GP']:,.2f}",
            "Turnover Source": row["Turnover Source"],
            "Allocation Weight (%)": f"{row['Allocation Weight (%)']:.2f}%",
            "Effective Capital Required": f"${row['Effective Capital Required']:,.2f}",
            # "Stock Density ($/sqm)": f"${row['Stock Density ($/sqm)']:,.2f}",
        })

    st.dataframe(
        targets_display_rows,
        use_container_width=True,
        hide_index=True,
    )
else:
    st.warning("No target allocation data to display in summary table")