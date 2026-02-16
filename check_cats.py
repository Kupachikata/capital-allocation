import pandas as pd

df = pd.read_excel(r'c:\Users\1Vincent\Desktop\BreakEvenV1-main\retail_pos_sales.xlsx')
print('Categories in retail_pos_sales.xlsx:')
for cat in df['Category'].dropna().unique():
    print(f'  {repr(cat)}')
