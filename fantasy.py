import os
import sys
import pandas as pd
from sqlalchemy import create_engine
from curl_cffi import requests

# 1. Configuration Constants
API_URL = "https://premierleague.com"
DEFAULT_CSV = "fpl_players_data.csv"
TABLE_NAME = "players"

# 2. Update these fields with your MySQL Server details
MYSQL_CONFIG = {
    "user": "root",          # Your MySQL Username
    "password": "password",  # Your MySQL Password
    "host": "localhost",     # Host (e.g., localhost or an IP address)
    "port": "3306",          # Default MySQL Port
    "database": "fpl_db"     # The database name you want to use
}

def clear_screen():
    """Clears the terminal screen for a clean user interface."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(title):
    """Prints a consistent UI header."""
    print("=" * 60)
    print(f" {title.center(58)} ")
    print("=" * 60)

def main():
    clear_screen()
    print_header("FPL DATA EXTRACTOR (IMPERSONATION VERSION)")
    
    # ----------------------------------------------------
    # STEP 1: Fetching the Data with Browser Impersonation
    # ----------------------------------------------------
    print("\n[STEP 1/3] Fetch Live FPL API Data")
    input("👉 Press ENTER to impersonate a browser and fetch data...")
    
    print("\n🔄 Connecting to FPL API via curl_cffi (Chrome 120 Impersonation)...")
    
    # curl_cffi clones the exact TLS signature and network fingerprint of a clean desktop browser
    response = requests.get(API_URL, impersonate="chrome120")
    
    # HTTP Status Check
    if response.status_code != 200:
        print(f"\n❌ Server Error! Status Code: {response.status_code}")
        print("Raw Content Response:")
        print(response.text[:500])
        sys.exit(1)
        
    # Response Type Validation Check
    raw_text = response.text.strip()
    if raw_text.startswith("<") or "html" in raw_text.lower():
        print("\n❌ Blocking Error: The server still served an HTML webpage.")
        print("\n--- BEGIN HTML TEMPLATE ---")
        print(raw_text[:600])
        print("--- END HTML TEMPLATE ---")
        sys.exit(1)
        
    data = response.json()
    print("✅ Data successfully retrieved from FPL servers!")

    # ----------------------------------------------------
    # STEP 2: Processing the Data
    # ----------------------------------------------------
    print("\n[STEP 2/3] Process Data Attributes")
    print(f"🔄 Parsing stats into database structures...")
    
    players = data.get('elements', [])
    teams_list = data.get('teams', [])
    positions_list = data.get('element_types', [])

    team_map = {t['id']: t['name'] for t in teams_list}
    pos_map = {p['id']: p['singular_name_short'] for p in positions_list}

    parsed_players = []
    for p in players:
        parsed_players.append({
            'player_id': p.get('id'),
            'first_name': p.get('first_name'),
            'second_name': p.get('second_name'),
            'web_name': p.get('web_name'),
            'team': team_map.get(p.get('team'), 'Unknown'),
            'position': pos_map.get(p.get('element_type'), 'Unknown'),
            'price_m': p.get('now_cost', 0) / 10,
            'total_points': p.get('total_points', 0),
            'form': float(p.get('form', '0.0')),
            'selected_by_pct': float(p.get('selected_by_percent', '0.0')),
            'goals_scored': p.get('goals_scored', 0),
            'assists': p.get('assists', 0),
            'clean_sheets': p.get('clean_sheets', 0)
        })

    df = pd.DataFrame(parsed_players)
    print(f"✅ Successfully processed {len(df)} Premier League players.")
    input("\n👉 Press ENTER to proceed to the export menu...")

    # ----------------------------------------------------
    # STEP 3: Export Menu Screen
    # ----------------------------------------------------
    while True:
        clear_screen()
        print_header("STEP 3/3: EXPORT CONFIGURATION")
        print("\nChoose your preferred format to save the data:")
        print(" Export to CSV Spreadsheet Only")
        print(" Export to MySQL Database Only")
        print(" Export to BOTH CSV and MySQL Database")
        print(" Cancel and Exit")
        
        choice = input("\nEnter choice (1-4): ").strip()

        if choice == '1':
            df.to_csv(DEFAULT_CSV, index=False)
            print(f"\n✅ Success! CSV spreadsheet file created: '{DEFAULT_CSV}'")
            break
            
        elif choice == '2':
            save_to_mysql(df)
            break
            
        elif choice == '3':
            df.to_csv(DEFAULT_CSV, index=False)
            print(f"\n✅ Success! CSV spreadsheet file created: '{DEFAULT_CSV}'")
            save_to_mysql(df)
            break
            
        elif choice == '4':
            print("\nOperation cancelled by user.")
            sys.exit(0)
        else:
            print("\n⚠️ Invalid selection! Please enter a number between 1 and 4.")
            input("Press ENTER to try again...")

    print_header("PROCESS COMPLETE")
    print("\nAll tasks finished successfully!\n")

def save_to_mysql(df):
    """Handles connection and transfer to MySQL."""
    connection_url = f"mysql+mysqlconnector://{MYSQL_CONFIG['user']}:{MYSQL_CONFIG['password']}@{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']}"
    print(f"\n🔄 Connecting to MySQL server at {MYSQL_CONFIG['host']}...")
    
    engine = create_engine(connection_url)
    df.to_sql(TABLE_NAME, con=engine, if_exists="replace", index=False)
    print(f"✅ Success! Updated MySQL table '{TABLE_NAME}' with {len(df)} rows.")

    print("\n📊 Database Preview (Top 3 players by Total Points):")
    query = f"SELECT web_name, team, position, total_points FROM {TABLE_NAME} ORDER BY total_points DESC LIMIT 3"
    
    with engine.connect() as connection:
        test_df = pd.read_sql_query(query, connection)
        
    print("-" * 50)
    print(test_df.to_string(index=False))
    print("-" * 50)

if __name__ == "__main__":
    main()

