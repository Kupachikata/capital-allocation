
import pandas as pd
from pathlib import Path

def normalize_category_name(cat_name):
    if not isinstance(cat_name, str):
        return ""
    return cat_name.strip().upper().replace('-', '_').replace(' ', '_')

def load_product_data():
    products_file = Path("products.xlsx")
    try:
        
        df = pd.read_excel(products_file)
        print("Columns before:", df.columns.tolist())

        # Convert date to datetime
        df['date'] = pd.to_datetime(df['date'])
        
        # normalize category names
        # THIS IS THE LINE failing
        df['category_norm'] = df['category'].apply(normalize_category_name)
        
        print("Columns after:", df.columns.tolist())
        print("Success")
            
    except Exception as e:
        print(f"Error loading products.xlsx: {e}")

if __name__ == "__main__":
    load_product_data()
