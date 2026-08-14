import logging
import sys
import pandas as pd
from sqlalchemy import create_engine
from curl_cffi import requests

# 1. Logging Configuration (Replaces interactive printing)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout) # Outputs to console/syslog
    ]
)

# 2. Configuration Constants
API_URL = "https://premierleague.com"
DEFAULT_CSV = "fpl_all_players_master.csv"
TABLE_NAME = "players_master"

# Update these fields with your exact MySQL configurations
MYSQL_CONFIG = {
    "user": "Kumar",
    "password": "StrongPassword123!",  # Update to your actual root password
    "host": "localhost",
    "port": "3306",
    "database": "FPL"     
}

def main():
    logging.info("Starting background FPL database sync...")
    
    # -------------------------------------------------------------------------
    # STEP 1: Stealth API Data Retrieval
    # -------------------------------------------------------------------------
    logging.info("Connecting to FPL API via curl_cffi session context...")
    
    with requests.Session() as session:
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://premierleague.com",
            "Referer": "https://premierleague.com/",
            "Sec-Ch-Ua": '"Not A(Break;Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
        }
        try:
            response = session.get(API_URL, headers=headers, impersonate="chrome120")
        except Exception as e:
            logging.error(f"Network connection failed: {e}")
            sys.exit(1)
    
    if response.status_code != 200:
        logging.error(f"Network Fault! Server responded with HTTP code: {response.status_code}")
        sys.exit(1)
        
    raw_text = response.text.strip()
    if raw_text.startswith("<") or "html" in raw_text.lower():
        logging.error("Redirect Error: Cloudflare kicked the scraper to the desktop home page.")
        sys.exit(1)
        
    data = response.json()
    logging.info("Comprehensive data payload downloaded successfully.")

    # -------------------------------------------------------------------------
    # STEP 2: Comprehensive Ingestion Processing via Pandas
    # -------------------------------------------------------------------------
    logging.info("Normalizing fields and parsing JSON payload...")
    
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
    
    # Safely check for original cost keys to prevent traceback crashes
    if 'original_cost' in df.columns:
        df['original_price_m'] = df['original_cost'] / 10
    elif 'cost_change_start' in df.columns and 'now_cost' in df.columns:
        df['original_price_m'] = (df['now_cost'] - df['cost_change_start']) / 10

    # Clean priority layout organization
    priority_cols = ['id', 'first_name', 'second_name', 'web_name', 'team_name', 'position_name', 'price_m']
    existing_priority = [col for col in priority_cols if col in df.columns]
    all_other_cols = [col for col in df.columns if col not in existing_priority]
    df = df[existing_priority + all_other_cols]

    # -------------------------------------------------------------------------
    # STEP 3: Silent Execution & Multi-Format Deployment
    # -------------------------------------------------------------------------
    # 1. Output to CSV Spreadsheet
    try:
        df.to_csv(DEFAULT_CSV, index=False)
        logging.info(f"CSV spreadsheet updated successfully: '{DEFAULT_CSV}'")
    except Exception as e:
        logging.error(f"Failed to write CSV file: {e}")

    # 2. Output to MySQL Database
    connection_url = f"mysql+mysqlconnector://{MYSQL_CONFIG['user']}:{MYSQL_CONFIG['password']}@{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']}"
    logging.info(f"Connecting to MySQL server at {MYSQL_CONFIG['host']}...")
    
    # Copy dataframe and securely stringify nested arrays/objects for MySQL compatibility
    db_df = df.copy()
    for col in db_df.columns:
        if db_df[col].apply(lambda x: isinstance(x, (list, dict))).any():
            db_df[col] = db_df[col].astype(str)
            
    try:
        engine = create_engine(connection_url)
        db_df.to_sql(TABLE_NAME, con=engine, if_exists="replace", index=False)
        logging.info(f"MySQL table '{TABLE_NAME}' updated successfully with {len(db_df)} rows.")
    except Exception as e:
        logging.error(f"An error occurred while pushing data to MySQL: {e}")
        sys.exit(1)

    logging.info("Background update process completed successfully.")

if __name__ == "__main__":
    main()

