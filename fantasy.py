import os
import sys
import pandas as pd
from sqlalchemy import create_engine
from curl_cffi import requests

# 1. Configuration Constants
API_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"
DEFAULT_CSV = "fpl_all_players_master.csv"
TABLE_NAME = "players_master"

# Update these fields with your exact MySQL configurations
MYSQL_CONFIG = {
    "user": "Kumar",
    "password": "StrongPassword123!",  # Update to your actual root password
    "host": "localhost",
    "port": "3306",
    "database": "FPL"     # Run 'CREATE DATABASE IF NOT EXISTS fpl_db;' in MySQL first
}

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(title):
    print("=" * 65)
    print(f" {title.center(63)} ")
    print("=" * 65)

def main():
    clear_screen()
    print_header("FPL FULL DATABASE DATA SOURCE INGESTION ENGINE")
    
    # -------------------------------------------------------------------------
    # STEP 1: Stealth API Data Retrieval
    # -------------------------------------------------------------------------
    print("\n[STEP 1/3] Establish Safe Connection to FPL Data Matrix")
    input("👉 Press ENTER to fire browser impersonation wrappers...")
    
    print("\n🔄 Connecting to FPL API via curl_cffi session context...")
    
    with requests.Session() as session:
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://fantasy.premierleague.com",
            "Referer": "https://fantasy.premierleague.com/",
            "Sec-Ch-Ua": '"Not A(Break;Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
        }
        response = session.get(API_URL, headers=headers, impersonate="chrome120")
    
    if response.status_code != 200:
        print(f"\n❌ Network Fault! Server responded with HTTP code: {response.status_code}")
        sys.exit(1)
        
    raw_text = response.text.strip()
    if raw_text.startswith("<") or "html" in raw_text.lower():
        print("\n❌ Redirect Error: Cloudflare kicked the scraper to the desktop home page.")
        sys.exit(1)
        
    data = response.json()
    print("✅ Comprehensive data payload downloaded successfully!")

    # -------------------------------------------------------------------------
    # STEP 2: Comprehensive Ingestion Processing via Pandas (FIXED VERSION)
    # -------------------------------------------------------------------------
    print("\n[STEP 2/3] Processing Global Field Matrix")
    print("🔄 Standardizing fields and generating user-friendly layout joins...")
    
    raw_players = data.get('elements', [])
    teams_list = data.get('teams', [])
    positions_list = data.get('element_types', [])

    # Create mapping translation dictionaries
    team_map = {t['id']: t['name'] for t in teams_list}
    pos_map = {p['id']: p['singular_name_short'] for p in positions_list}

    # Swallow every single field from the JSON payload dynamically
    df = pd.DataFrame(raw_players)

    # Convert internal numeric foreign IDs into real string text descriptions safely
    if 'team' in df.columns:
        df['team_name'] = df['team'].map(team_map)
    if 'element_type' in df.columns:
        df['position_name'] = df['element_type'].map(pos_map)

    # Fallback-safe structural price conversions
    if 'now_cost' in df.columns:
        df['price_m'] = df['now_cost'] / 10
    
    # Safely check for original cost keys to prevent traceback KeyError crashes
    if 'original_cost' in df.columns:
        df['original_price_m'] = df['original_cost'] / 10
    elif 'cost_change_start' in df.columns and 'now_cost' in df.columns:
        # Reconstruct starting price mathematically if direct variable isn't present
        df['original_price_m'] = (df['now_cost'] - df['cost_change_start']) / 10

    # Clean priority layout organization
    priority_cols = ['id', 'first_name', 'second_name', 'web_name', 'team_name', 'position_name', 'price_m']
    # Filter out columns that don't exist in the current layout configuration
    existing_priority = [col for col in priority_cols if col in df.columns]
    all_other_cols = [col for col in df.columns if col not in existing_priority]
    df = df[existing_priority + all_other_cols]

    print(f"✅ Success! Ingested {len(df.columns)} data dimensions for {len(df)} elements.")
    input("\n👉 Press ENTER to load the data destination menu...")

    # -------------------------------------------------------------------------
    # STEP 3: Multi-Format Deployment Selection
    # -------------------------------------------------------------------------
    while True:
        clear_screen()
        print_header(f"STEP 3/3: DEPLOYMENT SELECTION ({len(df.columns)} COLUMNS)")
        print("\nSelect target destination for your dataset:")
        print(" 1️⃣ Dump all features to CSV Spreadsheet File")
        print(" 2️⃣ Pipe all features straight into MySQL Database")
        print(" 3️⃣ Sync to BOTH CSV and MySQL simultaneously")
        print(" 4️⃣ Abort and Exit")
        
        choice = input("\nEnter routing selection (1-4): ").strip()

        if choice == '1':
            df.to_csv(DEFAULT_CSV, index=False)
            print(f"\n✅ File successfully written to spreadsheet: '{DEFAULT_CSV}'")
            break
            
        elif choice == '2':
            save_to_mysql_master(df)
            break
            
        elif choice == '3':
            df.to_csv(DEFAULT_CSV, index=False)
            print(f"\n✅ File successfully written to spreadsheet: '{DEFAULT_CSV}'")
            save_to_mysql_master(df)
            break
            
        elif choice == '4':
            print("\nOperation cancelled.")
            sys.exit(0)
        else:
            print("\n⚠️ Selection invalid! Choose an option from 1 to 4.")
            input("Press ENTER to refresh menu...")

    print_header("INGESTION COMPLETED")
    print(f"\nAll operations concluded. Table contains {len(df.columns)} active data variables.\n")


def save_to_mysql_master(df):
    """Dynamically stringifies nested objects and writes all data profiles to MySQL."""""
    connection_url = f"mysql+mysqlconnector://{MYSQL_CONFIG['user']}:{MYSQL_CONFIG['password']}@{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']}"
    print(f"\n🔄 Injecting tables to MySQL endpoint: {MYSQL_CONFIG['host']}...")
    # 💡 FIX: Make a temporary copy and convert nested objects (lists/dicts) into clean strings
    db_df = df.copy()
    for col in db_df.columns:
    # If the column contains lists or dictionaries, convert it into text string formatting
        if db_df[col].apply(lambda x: isinstance(x, (list, dict))).any():
            db_df[col] = db_df[col].astype(str)
    engine = create_engine(connection_url)
    # Pushes all schema entries cleanly without object structural conflicts
    db_df.to_sql(TABLE_NAME, con=engine, if_exists="replace", index=False)
    print(f"✅ Success! Master MySQL table '{TABLE_NAME}' updated with {len(db_df)} rows.")
    print("\n📊 Mini Table Crosscheck (Verification Sample):")
    # Check for fields that exist in the current layout configuration
    sample_fields = ['id', 'web_name', 'team_name', 'position_name', 'price_m', 'ict_index']
    existing_samples = [f for f in sample_fields if f in db_df.columns]
    fields_str = ", ".join(existing_samples)                              
    query = f"SELECT {fields_str} FROM {TABLE_NAME} ORDER BY total_points DESC LIMIT 3"                                                                           
    with engine.connect() as connection:
        test_df = pd.read_sql_query(query, connection)                                                                                                                                             
    print("-" * 75)
    print(test_df.to_string(index=False))
    print("-" * 75)
if __name__== "__main__":
    main()

