import logging
import os
import sys
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, text
from curl_cffi import requests

# 1. Logging Setup (Optimised for system background cron/task scheduling redirects)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# 2. Pipeline Configuration Context
API_URL = "https://premierleague.com"
TABLE_NAME = "players_master"
OUTPUT_MARKDOWN_PATH = "FPL_Performance_Report.md"  # Change to absolute path if linking to Obsidian

MYSQL_CONFIG = {
    "user": "root",
    "password": "password",  # Update to your actual root password
    "host": "localhost",
    "port": "3306",
    "database": "fpl_db"     
}

def main():
    logging.info("=== STARTING UNIFIED FPL BACKGROUND ENGINE SECURE PROCESSING ===")
    
    # -------------------------------------------------------------------------
    # PIPELINE STAGE 1: Stealth API Data Retrieval
    # -------------------------------------------------------------------------
    logging.info("[STAGE 1/4] Establishing secure proxy link with FPL endpoints...")
    
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
            logging.error(f"❌ Structural request failed at transport layer: {e}")
            sys.exit(1)
            
    if response.status_code != 200:
        logging.error(f"❌ Ingestion rejected by FPL servers. HTTP status code: {response.status_code}")
        sys.exit(1)
        
    raw_text = response.text.strip()
    if raw_text.startswith("<") or "html" in raw_text.lower():
        logging.error("❌ Blocking Exception: Cloudflare triggered a redirect challenge block to home page.")
        sys.exit(1)
        
    data = response.json()
    logging.info("✅ Global data matrix payload collected successfully.")

    # -------------------------------------------------------------------------
    # PIPELINE STAGE 2: Database Ingestion & Structural Processing
    # -------------------------------------------------------------------------
    logging.info("[STAGE 2/4] Normalizing data metrics array via Pandas...")
    
    raw_players = data.get('elements', [])
    teams_list = data.get('teams', [])
    positions_list = data.get('element_types', [])

    team_map = {t['id']: t['name'] for t in teams_list}
    pos_map = {p['id']: p['singular_name_short'] for p in positions_list}

    df = pd.DataFrame(raw_players)

    # Injecting user-friendly join translations
    if 'team' in df.columns:
        df['team_name'] = df['team'].map(team_map)
    if 'element_type' in df.columns:
        df['position_name'] = df['element_type'].map(pos_map)

    # Normalized float calculation adjustments
    if 'now_cost' in df.columns:
        df['price_m'] = df['now_cost'] / 10
    if 'original_cost' in df.columns:
        df['original_price_m'] = df['original_cost'] / 10
    elif 'cost_change_start' in df.columns and 'now_cost' in df.columns:
        df['original_price_m'] = (df['now_cost'] - df['cost_change_start']) / 10

    # Layout column priority ordering
    priority_cols = ['id', 'first_name', 'second_name', 'web_name', 'team_name', 'position_name', 'price_m']
    existing_priority = [col for col in priority_cols if col in df.columns]
    all_other_cols = [col for col in df.columns if col not in existing_priority]
    df = df[existing_priority + all_other_cols]

    # Convert complex nested arrays/dictionaries to clean text for MySQL type mapping safety
    db_df = df.copy()
    for col in db_df.columns:
        if db_df[col].apply(lambda x: isinstance(x, (list, dict))).any():
            db_df[col] = db_df[col].astype(str)

    # Establish secure master database engine connection
    connection_url = f"mysql+mysqlconnector://{MYSQL_CONFIG['user']}:{MYSQL_CONFIG['password']}@{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']}"
    engine = create_engine(connection_url)
    
    try:
        db_df.to_sql(TABLE_NAME, con=engine, if_exists="replace", index=False)
        logging.info(f"✅ Ingestion successful. Master table '{TABLE_NAME}' populated with {len(db_df)} records.")
    except Exception as e:
        logging.error(f"❌ Failed to stream records straight into target MySQL schema: {e}")
        sys.exit(1)

    # -------------------------------------------------------------------------
    # PIPELINE STAGE 3: Analytical SQL Views Synchronization
    # -------------------------------------------------------------------------
    logging.info("[STAGE 3/4] Syncing core database view schemas...")
    
    views = {
        "view_fpl_value_for_money": """
            CREATE OR REPLACE VIEW view_fpl_value_for_money AS
            SELECT id AS player_id, web_name, team_name, position_name, price_m, total_points, minutes, ROUND(total_points / price_m, 2) AS points_per_million
            FROM players_master WHERE minutes >= 270 ORDER BY points_per_million DESC;
        """,
        "view_fpl_expected_performance": """
            CREATE OR REPLACE VIEW view_fpl_expected_performance AS
            SELECT id AS player_id, web_name, team_name, position_name, price_m, goals_scored, ROUND(CAST(expected_goals AS DECIMAL(10,2)), 2) AS xG, ROUND(goals_scored - CAST(expected_goals AS DECIMAL(10,2)), 2) AS goals_variance, assists, ROUND(CAST(expected_assists AS DECIMAL(10,2)), 2) AS xA, ROUND(assists - CAST(expected_assists AS DECIMAL(10,2)), 2) AS assists_variance
            FROM players_master WHERE minutes >= 180 ORDER BY xG DESC;
        """,
        "view_fpl_market_trends": """
            CREATE OR REPLACE VIEW view_fpl_market_trends AS
            SELECT id AS player_id, web_name, team_name, position_name, price_m, transfers_in_event, transfers_out_event, (transfers_in_event - transfers_out_event) AS net_transfers_this_gw, cost_change_event, cost_change_start
            FROM players_master ORDER BY net_transfers_this_gw DESC;
        """,
        "view_fpl_discipline_and_bonus": """
            CREATE OR REPLACE VIEW view_fpl_discipline_and_bonus AS
            SELECT id AS player_id, web_name, team_name, position_name, bps AS total_bps_score, bonus AS actual_bonus_points, yellow_cards, red_cards, (yellow_cards * 1 + red_cards * 3) AS discipline_penalty_score
            FROM players_master WHERE minutes > 0 ORDER BY yellow_cards DESC, red_cards DESC;
        """
    }

    try:
        with engine.connect() as connection:
            with connection.begin():
                for view_name, query in views.items():
                    connection.execute(text(query))
        logging.info("✅ All analytical SQL views successfully structuralised.")
    except Exception as e:
        logging.error(f"❌ View creation transaction failed on compilation layout: {e}")
        sys.exit(1)

    # -------------------------------------------------------------------------
    # PIPELINE STAGE 4: Markdown Data Visualization Compilation
    # -------------------------------------------------------------------------
    logging.info("[STAGE 4/4] Extracting data from active views to forge Obsidian report...")
    
    try:
        with engine.connect() as conn:
            df_value = pd.read_sql_query("SELECT web_name, team_name, position_name, price_m, total_points, points_per_million FROM view_fpl_value_for_money LIMIT 10;", conn)
            df_understat = pd.read_sql_query("SELECT web_name, team_name, position_name, price_m, goals_scored, xG, goals_variance FROM view_fpl_expected_performance ORDER BY goals_variance ASC LIMIT 7;", conn)
            df_trends = pd.read_sql_query("SELECT web_name, team_name, position_name, price_m, net_transfers_this_gw, cost_change_event FROM view_fpl_market_trends LIMIT 7;", conn)
            df_discipline = pd.read_sql_query("SELECT web_name, team_name, position_name, yellow_cards, red_cards, discipline_penalty_score FROM view_fpl_discipline_and_bonus LIMIT 5;", conn)
    except Exception as e:
        logging.error(f"❌ Failed to extract view frames to compile markdown: {e}")
        sys.exit(1)

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    md_content = f"""# ⚽ FPL Master Analytics & Performance Report
Generated automatically on: `{current_time}`

---

## 💎 1. Top 10 Best Value Assets (Points Per Million)
*Filters out players with fewer than 270 minutes on the pitch to isolate proven starting options.*

{df_value.to_markdown(index=False)}

---

## 🎯 2. Top 7 Attacking Underperformers (xG Understat Targets)
*Ranked by negative goal variance. These players are getting high-quality chances but finishing poorly, making them excellent transfer targets due for positive regression.*

{df_understat.to_markdown(index=False)}

---

## 📈 3. Top 7 Live Market Trends (Net Transfers)
*Tracks mass manager movement during the current gameweek. Use this to catch price rises or avoid drops.*

{df_trends.to_markdown(index=False)}

---

## ⚠️ 4. Top 5 Discipline Liabilities (Suspension Risk)
*Highlights players accumulating yellow/red cards who are approaching or serving suspension thresholds.*

{df_discipline.to_markdown(index=False)}

---

