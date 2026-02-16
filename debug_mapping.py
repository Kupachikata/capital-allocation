import pandas as pd
from pathlib import Path

def test_mapping():
    products_file = Path("products3.xlsx")
    if not products_file.exists():
        print("products3.xlsx not found")
        return

    df = pd.read_excel(products_file)
    print("Original columns:", df.columns.tolist())

    col_map = {}
    for c in df.columns:
        lower = str(c).strip().lower()
        norm = lower.replace(" ", "_")
        print(f"Processing col: '{c}' -> lower: '{lower}'")

        if "store" in lower or "branch" in lower:
            col_map[c] = "store_name"
            # print("  Matched store_name")
            # continue - simulating the code's continue by using elif or just structure

        if ("shop" in lower or "store" in lower) and ("space" in lower or "sqm" in lower or "floor" in lower):
            col_map[c] = "shop_space"
            # continue

        if "category" in lower or "dept" in lower or "department" in lower:
            col_map[c] = "category"
            
        if "product" in lower or "item" in lower or "sku" in lower or "description" in lower:
            col_map[c] = "product"

        if "qty" in lower or "quantity" in lower or "units" in lower or "volume" in lower:
            col_map[c] = "quantity"

        if "price" in lower or "selling" in lower or ("unit" in lower and "cost" not in lower):
            col_map[c] = "price"
            print("  Matched price")

        if "date" in lower or "trans_date" in norm or "transaction" in lower:
            col_map[c] = "date"
            print("  Matched date")

    print("\nMapping Dict:", col_map)
    
    if col_map:
        df = df.rename(columns=col_map)
    
    print("\nRenamed columns:", df.columns.tolist())
    
    required_cols = ['category', 'product', 'quantity', 'price', 'date']
    missing = [c for c in required_cols if c not in df.columns]
    print("\nMissing columns:", missing)

if __name__ == "__main__":
    test_mapping()
