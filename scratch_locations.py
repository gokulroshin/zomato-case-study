import pandas as pd
df = pd.read_parquet('data/restaurants.parquet')
print("--- listed_in(city) ---")
print(sorted([str(x) for x in df["listed_in(city)"].dropna().unique()]))
print("\n--- location ---")
print(sorted([str(x) for x in df["location"].dropna().unique()]))
