# Install dependencies as needed:
# pip install kagglehub pandas sqlalchemy pymysql

import os
import glob
import pandas as pd
import kagglehub
from sqlalchemy import create_engine

# --- 1. CONFIGURATION ---
dataset_handle = "rovnez/fc-26-fifa-26-player-data"

# MySQL Database setup (Update these credentials with your own)

db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_HOST")         
db_port = os.getenv("DB_PORT")              
db_name = os.getenv("DB_DATABASE")
table_name = "FIFA_STATS"

# --- 2. FETCH DATA FROM KAGGLE ---
print(f"Downloading dataset files from: {dataset_handle}...")
try:
    # This downloads the entire dataset directory to your local cache safely
    download_dir = kagglehub.dataset_download(dataset_handle)
    print(f"Dataset downloaded locally to: {download_dir}")
    
    # Dynamically locate any CSV file inside the downloaded directory
    csv_files = glob.glob(os.path.join(download_dir, "*.csv"))
    
    if not csv_files:
        raise FileNotFoundError("No CSV files found inside the downloaded Kaggle dataset.")
        
    # Read the first discovered CSV file
    target_csv_path = csv_files[0]
    print(f"Loading data from discovered file: {os.path.basename(target_csv_path)}")
    df = pd.read_csv(target_csv_path)

except Exception as e:
    print(f"Failed to fetch or parse Kaggle dataset: {e}")
    exit(1)

print("\nFirst 5 records preview:")
print(df.head())

# --- 3. SAVE TO LOCAL WORKING DIRECTORY CSV ---
csv_filename = "FIFA_players_stats.csv"
df.to_csv(csv_filename, index=False)
print(f"\nSuccess: Clean copy saved locally to {csv_filename}")

# --- 4. EXPORT TO MYSQL ---
print(f"\nConnecting to MySQL database '{db_name}'...")
try:
    # Create the database connection engine using PyMySQL
    connection_string = f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    engine = create_engine(connection_string)

    # Write the dataframe to the SQL database
    df.to_sql(name=table_name, con=engine, if_exists='replace', index=False)
    print(f"Success: Table '{table_name}' populated in MySQL database!")

except Exception as e:
    print(f"\nAn error occurred while uploading to MySQL: {e}")
