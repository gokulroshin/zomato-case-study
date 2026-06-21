import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)

parquet_path = 'data/restaurants.parquet'

def update_parquet():
    df = pd.read_parquet(parquet_path)
    logging.info(f"Loaded {len(df)} rows from {parquet_path}")
    
    # User requested to update locations in the parquet file.
    # We'll overwrite the messy 'location' column with the clean 'listed_in(city)' column
    # since 'listed_in(city)' has exactly Indiranagar, Bellandur, Whitefield, etc.
    df['location'] = df['listed_in(city)']
    
    df.to_parquet(parquet_path, index=False)
    logging.info(f"Successfully updated 'location' column in {parquet_path} and saved.")

if __name__ == "__main__":
    update_parquet()
