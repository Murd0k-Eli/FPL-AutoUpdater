import logging
import os
import sys
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine

# 1. Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# 2. Configuration Settings
OUTPUT_MARKDOWN_PATH = "FPL_Performance_Report.md"  # Change path if moving to Obsidian folders

MYSQL_CONFIG = {
    "user": "Kumar",
    "password": "StrongPassword123!",  # Update to your actual root password
    "host": "localhost",
    "port": "3306",
    "database": "FPL"     
}

def generate_markdown_report():
    connection_url = f"mysql+mysqlconnector://{MYSQL_CONFIG['user']}:{MYSQL_CONFIG['password']}@{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']}"
    
    logging.info("Connecting to MySQL to fetch analysis view snapshots...")
    try:
        engine = create_engine(connection_url)
        
        with engine.connect() as conn:
            # Query 1: Top 10 Best Value-for-Money Assets
            q_value = "SELECT web_name, team_name, position_name, price_m, total_points, points_per_million FROM view_fpl_value_for_money LIMIT 10;"
            df_value = pd.read_sql_query(q_value, conn)
            
            # Query 2: Top 7 Attacking Underperformers (xG Understat Targets)
            q_understat = "SELECT web_name, team_name, position_name, price_m, goals_scored, xG, goals_variance FROM view_fpl_expected_performance ORDER BY goals_variance ASC LIMIT 7;"
            df_understat = pd.read_sql_query(q_understat, conn)
            
            # Query 3: Top 7 Live Market Transfer Trends
            q_trends = "SELECT web_name, team_name, position_name, price_m, net_transfers_this_gw, cost_change_event FROM view_fpl_market_trends LIMIT 7;"
            df_trends = pd.read_sql_query(q_trends, conn)
            
            # Query 4: Top 5 Card Suspects & Discipline Liabilities
            q_discipline = "SELECT web_name, team_name, position_name, yellow_cards, red_cards, discipline_penalty_score FROM view_fpl_discipline_and_bonus LIMIT 5;"
            df_discipline = pd.read_sql_query(q_discipline, conn)
            
    except Exception as e:
        logging.error(f"❌ Failed to extract view data arrays from MySQL: {e}")
        sys.exit(1)

    logging.info("Compiling data structures into clean Markdown tables...")
    
    # 3. Construct Markdown Content
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
**💡 Navigation Tip:** In Obsidian, switch to *Reading View* to review these tables cleanly. Run your background update script to completely refresh this report asset anytime!
"""

    # 4. Save to target markdown destination path
    try:
        with open(OUTPUT_MARKDOWN_PATH, "w", encoding="utf-8") as f:
            f.write(md_content)
        logging.info(f"✅ Success! Performance report compiled safely at: '{OUTPUT_MARKDOWN_PATH}'")
    except Exception as e:
        logging.error(f"❌ Failed to write Markdown report file: {e}")

if __name__ == "__main__":
    generate_markdown_report()

