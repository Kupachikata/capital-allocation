# Break Even Analysis Web App

A Python web application for performing break-even analysis with an interactive dashboard.

## Features

- **Interactive Input Panel** (Left - 20% width):
  - Selling Price Per Unit (0-2)
  - Variable Cost Per Unit (0-2)
  - Expected Units Sold
  - Projected Fixed Costs

- **Analysis Dashboard** (Right - 80% width):
  - **Assumptions Section**: Displays captured input values
  - **Key Metrics Section**: Shows break-even units, break-even revenue, and contribution margin
  - **Profitability Analysis**: Displays expected revenue, total variable costs, and profit/loss

## Installation

1. Navigate to the project directory:

   ```bash
   cd c:\workspace\work\analytics\BreakEvenV1
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the App

```bash
streamlit run app.py
```

The app will open in your default browser at `http://localhost:8501`

## How to Use

1. **Set Your Inputs** (Left Panel):
   - Enter the selling price per unit (in dollars)
   - Enter the variable cost per unit (in dollars)
   - Specify expected units sold
   - Enter projected fixed costs

2. **View Results** (Right Panel):
   - The **Assumptions** section shows your input values
   - The **Key Metrics** section calculates break-even point and contribution margin
   - The **Profitability Analysis** section shows expected profit/loss based on expected units

## Calculations

- **Contribution Margin per Unit** = Selling Price - Variable Cost per Unit
- **Break Even Units** = Fixed Costs / Contribution Margin per Unit
- **Break Even Revenue** = Break Even Units × Selling Price
- **Expected Profit** = (Expected Units × Contribution Margin) - Fixed Costs
