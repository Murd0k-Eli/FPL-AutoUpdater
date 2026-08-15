import os
import sys
import mysql.connector
from dotenv import load_dotenv

def run_player_sync_procedure():
    # 1. Load the environment variables from the .env file
    load_dotenv()

    # 2. Build configuration dictionary from environment variables
    db_config = {
        'host': os.getenv('DB_HOST'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'database': os.getenv('DB_DATABASE')
    }

    # Safety check: Ensure crucial config data was loaded
    if not db_config['host'] or not db_config['user']:
        print("Error: Failed to load database credentials from .env file.", file=sys.stderr)
        return

    connection = None
    try:
        # 3. Connect to the database using mysql-connector
        connection = mysql.connector.connect(**db_config)
        print("Successfully connected to the database using .env credentials.")
        
        # Open cursor with dictionary output enabled
        with connection.cursor(dictionary=True) as cursor:
            
            # 4. Fetch targeted rows from the FPL table 
            fpl_query = """
                SELECT id, first_name, second_name, web_name, team_name 
                FROM players_master 
                WHERE team_name = %s
            """
            cursor.execute(fpl_query, ('Arsenal',))
            fpl_players = cursor.fetchall()
            
            if not fpl_players:
                print("No FPL players found matching the criteria.")
                return

            print(f"Cycling through {len(fpl_players)} players via script procedure...\n")
            print(f"{'FPL Name':<25} | {'FIFA Short Name':<20} | {'FIFA ID':<10}")
            print("-" * 65)

            # 5. Procedure Loop (Simulating the Database Cursor)
            for player in fpl_players:
                f_name = player['first_name']
                s_name = player['second_name']
                t_name = player['team_name']

                # Create parameterized wildcards securely
                first_name_pattern = f"%{f_name}%"
                second_name_pattern = f"%{s_name}%"

                # 6. Fetch matching columns from the FIFA table
                fifa_query = """
                    SELECT player_id, short_name, long_name 
                    FROM fifa_database.EPL_STATS 
                    WHERE club_name = %s 
                      AND long_name LIKE %s 
                      AND long_name LIKE %s
                    LIMIT 1
                """
                
                cursor.execute(fifa_query, (t_name, first_name_pattern, second_name_pattern))
                fifa_match = cursor.fetchone()

                # 7. Extract fields and apply fallback logic
                fpl_full_name = f"{f_name} {s_name}"
                
                if fifa_match:
                    fifa_id = fifa_match['player_id']
                    fifa_short_name = fifa_match['short_name']
                else:
                    fifa_id = "N/A"
                    fifa_short_name = "NOT FOUND IN FIFA"

                # 8. Output results to console
                print(f"{fpl_full_name:<25} | {fifa_short_name:<20} | {fifa_id:<10}")

    except mysql.connector.Error as e:
        print(f"MySQL Error occurred: {e}", file=sys.stderr)
    finally:
        # Cleanly close the connection
        if connection and connection.is_connected():
            connection.close()
            print("\nDatabase connection closed cleanly.")

if __name__ == "__main__":
    run_player_sync_procedure()

