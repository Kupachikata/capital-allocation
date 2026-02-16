
import pandas as pd
import json
from pathlib import Path
import openpyxl
import traceback

def normalize_category_name(cat_name):
    if not isinstance(cat_name, str):
        return ""
    return str(cat_name).strip().upper().replace('-', '_').replace(' ', '_')

def convert_to_json():
    input_file = Path("products1.xlsx")
    output_file = Path("products.json")
    print(f"Reading {input_file} with openpyxl...", flush=True)
    
    try:
        # Load workbook using openpyxl directly
        wb = openpyxl.load_workbook(input_file, data_only=True)
        sheet = wb.active
        
        # Get headers
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            print("Empty sheet", flush=True)
            return
            
        header = rows[0]
        data = rows[1:]
        
        print(f"Headers found: {header}", flush=True)
        
        # Convert to list of dicts manually handling duplicate headers
        # We only care about specific columns
        target_indices = {}
        for idx, h in enumerate(header):
            if h in ['product', 'category', 'quantity', 'price', 'date']:
                target_indices[h] = idx
        
        print(f"Mapped columns: {target_indices}", flush=True)
        
        records = []
        for r_idx, row in enumerate(data):
            rec = {}
            for col_name, col_idx in target_indices.items():
                if col_idx < len(row):
                    rec[col_name] = row[col_idx]
            records.append(rec)
            
        print(f"Extracted {len(records)} raw records.", flush=True)
        
        # Create DataFrame from records
        df = pd.DataFrame(records)
        
        # 1. Force Positive Quantities
        if 'quantity' in df.columns:
            # Ensure numeric
            df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0)
            df['quantity'] = df['quantity'].abs()
            
        # 2. Normalize Categories
        if 'category' in df.columns:
            df['category_norm'] = df['category'].apply(normalize_category_name)
            
        # 3. Price
        if 'price' in df.columns:
             df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0.0)

        # 4. Date processing
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            min_date = df['date'].min()
            max_date = df['date'].max()
            if pd.isnull(min_date) or pd.isnull(max_date):
                 months_diff = 1.0
            else:
                days_diff = (max_date - min_date).days
                months_diff = max(1.0, days_diff / 30.0)
        else:
            months_diff = 1.0 
            
        print(f"Time period detected: {months_diff:.2f} months", flush=True)

        # 5. Aggregation
        agg_funcs = {
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
                "selling_price": float(row['price']),
                "monthly_sales_volume": float(monthly_vol)
            }
            products_list.append(p_obj)
            
        print(f"Converted {len(products_list)} products.", flush=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(products_list, f, indent=2)
            
        print(f"Saved to {output_file}", flush=True)

    except Exception as e:
        print(f"CRASH: {e}", flush=True)
        traceback.print_exc()

if __name__ == "__main__":
    convert_to_json()
