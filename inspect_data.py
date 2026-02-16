import pandas as pd

file_path = r'c:\Users\1Vincent\Desktop\BreakEvenV1-main\retail_pos_sales.xlsx'
df = pd.read_excel(file_path)

print('Dataset Info:')
print(f'Shape: {df.shape}')
print(f'Columns: {df.columns.tolist()}')
print(f'\nData Types:\n{df.dtypes}')
print(f'\nFirst 5 rows:')
print(df.head())
print(f'\nDate Range:')
print(f"  Min: {df['Trans_Date'].min()}")
print(f"  Max: {df['Trans_Date'].max()}")
print(f'\nUnique Categories: {df["Category"].nunique()}')
print(f'Categories: {list(df["Category"].unique())}')
print(f'\nUnique Generics: {df["Generic"].nunique()}')
print(f'Sample data stats:')
print(f"  Total Net_Amount: ${df['Net_Amount'].sum():,.2f}")
print(f"  Total Quantity: {df['Quantity'].sum():,}")
print(f"  Avg Net_Amount per transaction: ${df['Net_Amount'].mean():,.2f}")
