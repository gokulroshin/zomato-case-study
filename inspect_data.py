import pandas as pd
df = pd.read_parquet("data/restaurants.parquet")
print("Columns:", df.columns.tolist())
print("Unique cuisines sample:", df['cuisines'].dropna().head().tolist())
print("Unique rest_types sample:", df['rest_type'].dropna().head().tolist())
