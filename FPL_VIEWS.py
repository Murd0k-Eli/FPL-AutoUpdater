import logging
import sys
from sqlalchemy import create_engine, text

# 1. Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# 2. Update these fields with your exact MySQL configurations
MYSQL_CONFIG = {
    "user" = os.getenv("DB_USER")                 #                                             >│
    "password" = os.getenv("DB_PASSWORD")        #                                              >│
    "host" = os.getenv("DB_HOST")               #                                               >│
    "port" = os.getenv("DB_PORT")              #                                                >│
    "database" = os.getenv("DB_DATABASE")     #
}

def create_fpl_analysis_views():
    connection_url = f"mysql+mysqlconnector://{MYSQL_CONFIG['user']}:{MYSQL_CONFIG['password']}@{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']}"
    
    # Define our 4 core analytical views
    views = {
        "view_fpl_value_for_money": """
            CREATE OR REPLACE VIEW view_fpl_value_for_money AS
            SELECT 
                id AS player_id,
                web_name,
                team_name,
                position_name,
                price_m,
                total_points,
                minutes,
                ROUND(total_points / price_m, 2) AS points_per_million
            FROM players_master
            WHERE minutes >= 270
            ORDER BY points_per_million DESC;
        """,
        
        "view_fpl_expected_performance": """
            CREATE OR REPLACE VIEW view_fpl_expected_performance AS
            SELECT 
                id AS player_id,
                web_name,
                team_name,
                position_name,
                price_m,
                goals_scored,
                ROUND(CAST(expected_goals AS DECIMAL(10,2)), 2) AS xG,
                ROUND(goals_scored - CAST(expected_goals AS DECIMAL(10,2)), 2) AS goals_variance,
                assists,
                ROUND(CAST(expected_assists AS DECIMAL(10,2)), 2) AS xA,
                ROUND(assists - CAST(expected_assists AS DECIMAL(10,2)), 2) AS assists_variance
            FROM players_master
            WHERE minutes >= 180
            ORDER BY xG DESC;
        """,
        
        "view_fpl_market_trends": """
            CREATE OR REPLACE VIEW view_fpl_market_trends AS
            SELECT 
                id AS player_id,
                web_name,
                team_name,
                position_name,
                price_m,
                transfers_in_event,
                transfers_out_event,
                (transfers_in_event - transfers_out_event) AS net_transfers_this_gw,
                cost_change_event,
                cost_change_start
            FROM players_master
            ORDER BY net_transfers_this_gw DESC;
        """,
        
        "view_fpl_discipline_and_bonus": """
            CREATE OR REPLACE VIEW view_fpl_discipline_and_bonus AS
            SELECT 
                id AS player_id,
                web_name,
                team_name,
                position_name,
                bps AS total_bps_score,
                bonus AS actual_bonus_points,
                yellow_cards,
                red_cards,
                (yellow_cards * 1 + red_cards * 3) AS discipline_penalty_score
            FROM players_master
            WHERE minutes > 0
            ORDER BY yellow_cards DESC, red_cards DESC;
        """
    }

    logging.info(f"Connecting to MySQL server to verify views...")
    try:
        engine = create_engine(connection_url)
        
        # Execute each view creation query within a safe database connection block
        with engine.connect() as connection:
            # SQLAlchemy requires explicit transaction handling for DDL queries
            with connection.begin():
                for view_name, query in views.items():
                    logging.info(f"Syncing view structures for: '{view_name}'...")
                    connection.execute(text(query))
                    
        logging.info("✅ Success! All FPL analytical views are active and up to date.")
        
    except Exception as e:
        logging.error(f"❌ Failed to compile SQL views: {e}")
        sys.exit(1)

if __name__ == "__main__":
    create_fpl_analysis_views()

