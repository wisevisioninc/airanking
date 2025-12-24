
import sys
import json
import csv
import io
import os
import socket
import logging
import re
import pandas as pd

base_player_statistics_file = 'player_statistics_251029.csv'

def calculate_player_statistics(game_records):
    """Update player statistics based on baseline file and the latest date's game records.

    Rules:
    - Baseline: load from base_player_statistics_file.
    - Latest date: directly use Time formatted as YYYY-MM-DD.
    - Update using FinalChips for scoring and counts (Win/Lose/Peace).
    - Recompute WinningRate and Ranking.
    Returns: (player_stats: list[dict], latest_date: str|None)
    """

    def extract_date_str(time_str):
        """Return YYYY-MM-DD if Time matches that format; otherwise None."""
        s = (time_str or "").strip()
        return s if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s) else None

    # 1) Build stats map from baseline file
    stats_map = {}
    baseline_records = read_csv_file(base_player_statistics_file)
    for row in baseline_records:
        player_name = row.get('Player')
        if not player_name:
            continue
        try:
            win_chips = float(row.get('WinChips', 0) or 0)
        except (ValueError, TypeError):
            win_chips = 0
        def _to_int(value):
            try:
                return int(float(value))
            except (ValueError, TypeError):
                return 0
        stats_map[player_name] = {
            'Player': player_name,
            'WinChips': win_chips,
            'AttendCount': _to_int(row.get('AttendCount')),
            'WinCount': _to_int(row.get('WinCount')),
            'LoseCount': _to_int(row.get('LoseCount')),
            'PeaceCount': _to_int(row.get('PeaceCount')),
        }

    # 2) Determine latest date among provided game records using direct YYYY-MM-DD strings
    date_strs = [extract_date_str(rec.get('Time')) for rec in game_records]
    date_strs = [ds for ds in date_strs if ds is not None]
    latest_date_str = max(date_strs) if date_strs else None
    logging.info(f"Latest update date: {latest_date_str}")

    # 3) Choose records to apply: include all dated records (multiple dates supported)
    if date_strs:
        records_to_apply = [rec for rec in game_records if extract_date_str(rec.get('Time')) is not None]
    else:
        records_to_apply = game_records[:]

    # 4) Apply updates from all selected records using 'Chips'
    for record in records_to_apply:
        player_name = record.get('Player')
        if not player_name:
            continue
        try:
            chips = float(record.get('Chips', 0) or 0)
        except (ValueError, TypeError):
            logging.warning(f"Invalid Chips value for player {player_name}: {record.get('Chips')}")
            chips = 0

        if player_name not in stats_map:
            stats_map[player_name] = {
                'Player': player_name,
                'WinChips': 0,
                'AttendCount': 0,
                'WinCount': 0,
                'LoseCount': 0,
                'PeaceCount': 0,
                'WinningRate': 0,
                'Ranking': 0
            }
            
        player_stat = stats_map[player_name]

        # New total chips
        player_stat['WinChips'] = float(player_stat.get('WinChips', 0) or 0) + chips
        # Attend count increments for any participation in the latest event day
        player_stat['AttendCount'] = int(player_stat.get('AttendCount', 0) or 0) + 1

        if chips > 0:
            player_stat['WinCount'] = int(player_stat.get('WinCount', 0) or 0) + 1
        elif chips < 0:
            player_stat['LoseCount'] = int(player_stat.get('LoseCount', 0) or 0) + 1
        else:
            player_stat['PeaceCount'] = int(player_stat.get('PeaceCount', 0) or 0) + 1

    # 5) Convert map to list and compute winning rate; also add Date and round WinChips
    player_stats = []
    for _, stat in stats_map.items():
        attend = int(stat.get('AttendCount', 0) or 0)
        wins = int(stat.get('WinCount', 0) or 0)
        win_rate = (wins / attend) * 100 if attend > 0 else 0
        # Round WinChips to one decimal place
        stat['WinChips'] = round(float(stat.get('WinChips', 0) or 0), 1)
        stat['WinningRate'] = f"{win_rate:.2f}%"
        # Add Date for this ranking update
        stat['Date'] = latest_date_str
        player_stats.append(stat)

    # 6) Sort by WinChips and assign ranking
    player_stats.sort(key=lambda x: float(x.get('WinChips', 0) or 0), reverse=True)
    for i, stat in enumerate(player_stats):
        stat['Ranking'] = i + 1
        logging.info(f"Player {stat['Player']} ranking: {stat['Ranking']}")

    return player_stats, latest_date_str

def read_csv_file(filename):
    """Read CSV file using pandas and return as list of dictionaries"""
    file_path = get_file_path(filename)
    if not os.path.exists(file_path):
        logging.warning(f"CSV file not found: {file_path}")
        return []
        
    try:
        df = pd.read_csv(file_path)
        return df.to_dict(orient='records')
    except pd.errors.EmptyDataError:
        logging.warning(f"CSV file {filename} is empty; proceeding with no records")
        return []
    except Exception as e:
        logging.error(f"Error reading CSV file {filename}: {str(e)}")
        raise

def write_csv_file(filename, data):
    """Write list of dictionaries to CSV file using pandas"""
    if not data:
        logging.warning(f"No data to write to {filename}")
        return
        
    file_path = get_file_path(filename)
    backup_path = f"{file_path}.bak"
    temp_path = f"{file_path}.tmp"
    
    try:
        # Ensure directory exists
        dir_name = os.path.dirname(file_path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, mode=0o775, exist_ok=True)

        # Create backup of existing file
        if os.path.exists(file_path):
            try:
                import shutil
                shutil.copy2(file_path, backup_path)
                logging.info(f"Created backup of {filename} at {backup_path}")
                
                # Ensure backup has correct permissions
                os.chmod(backup_path, 0o664)
            except (IOError, OSError, PermissionError) as e:
                logging.error(f"Failed to create backup for {filename}: {str(e)}")
                # Continue anyway - backup failure shouldn't stop the write

        # Write to a temporary file first
        try:
            df = pd.DataFrame(data)
            df.to_csv(temp_path, index=False)
            
            # Set correct permissions before moving
            os.chmod(temp_path, 0o664)
            
            # Atomically replace the original file
            os.replace(temp_path, file_path)
            
            # Ensure final file has correct permissions
            os.chmod(file_path, 0o664)
            
            logging.info(f"Successfully wrote {len(data)} records to {filename}")
        except (IOError, OSError, PermissionError) as e:
            logging.error(f"Error writing to CSV file {filename}: {str(e)}")
            # Clean up temp file if it exists
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            raise
            
    except PermissionError as e:
        logging.error(f"Permission denied writing to {filename}: {str(e)}")
        logging.error(f"File path: {file_path}")
        logging.error(f"Current process user: {os.getuid()}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error writing to CSV file {filename}: {str(e)}")
        raise

def get_file_path(filename):
    """Get absolute path for a file relative to the server directory."""
    server_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(server_dir, filename)

if __name__ == "__main__":
    # 读取CSV文件
    # Read existing game records
    game_records = read_csv_file('team_building_record.csv')
    logging.info(f"Read {len(game_records)} existing records")

    # Calculate player statistics and get latest date for backup naming
    player_stats, latest_date = calculate_player_statistics(game_records)
    logging.info(f"Calculated statistics for {len(player_stats)} players on latest date: {latest_date}")
    
    # Save updated player statistics
    write_csv_file('player_statistics.csv', player_stats)
    logging.info("Saved updated player statistics")

    # Also write a dated backup into records_bak/player_statistics_{Time}.csv
    if latest_date:
        backup_name = f"records_bak/player_statistics_{latest_date}.csv"
        write_csv_file(backup_name, player_stats)
        logging.info(f"Saved backup player statistics to {backup_name}")

