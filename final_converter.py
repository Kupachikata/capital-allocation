
import pandas as pd
import json
from pathlib import Path

def normalize_category_name(cat_name):
    if not isinstance(cat_name, str):
        return ""
    return str(cat_name).strip().upper().replace('-', '_').replace(' ', '_')

def load_and_convert():
    print("Starting conversion...", flush=True)
    products_file = Path("products1.xlsx")
    
    if not products_file.exists():
        print("File not found")
        return
    
    try:
        df = pd.read_excel(products_file)
        
        # CLEANUP: Remove potentially duplicated columns
        df = df.loc[:, ~df.columns.duplicated()]

        # FORCE POSITIVE quantities as per user request
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
        # Use .loc to avoid "already exists" error
        df.loc[:, 'category_norm'] = df['category'].apply(normalize_category_name)

        # Aggregate
        df['revenue_txn'] = df['quantity'] * df['price']
        
        agg_funcs = {
            'revenue_txn': 'sum',
            'quantity': 'sum',
            'price': 'mean', 
            'category_norm': 'first'
        }
        
        product_agg = df.groupby(['product', 'category_norm']).agg(agg_funcs).reset_index()
        
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
            products_list.append(p_obj)
            
        print(f"Converted {len(products_list)} items.", flush=True)
        
        import json
        with open("products.json", "w", encoding='utf-8') as f:
            json.dump(products_list, f, indent=2)
            
        print("Saved to products.json", flush=True)
        
    except Exception as e:
        print(f"Error: {e}", flush=True)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    load_and_convert()
