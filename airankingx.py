from http.server import HTTPServer, SimpleHTTPRequestHandler
import sys
import json
import csv
import io
import os
import socket
import logging
import re
import shutil
from urllib.parse import parse_qs, urlparse

PORT = 8888
PassWord = "88888"
LOG_FILE = "server.log"
CODEBASE_PATH = "/home/jerry/codebase/airanking/"

# Configure logging
try:
    # 确保日志目录存在
    os.makedirs(os.path.dirname(os.path.abspath(LOG_FILE)), exist_ok=True)
    
    # 尝试创建日志文件（如果不存在）并检查权限
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w') as f:
            pass  # 创建空文件
    
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logging.info("Logging initialized successfully")
except (IOError, PermissionError) as e:
    # 如果写入日志文件失败，则退回到控制台日志
    print(f"Warning: Cannot write to log file ({str(e)}). Logging to console instead.")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

class CustomHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        """Override log_message to use our logging system."""
        logging.info("%s - %s" % (self.address_string(), format % args))

    def end_headers(self):
        # Add CORS headers to work with Nginx proxy
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'X-Requested-With, Content-Type, Accept')
        SimpleHTTPRequestHandler.end_headers(self)
        
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        # Make index.html the default page
        if self.path == '/':
            self.path = '/index.html'
        
        # Handle the update_leaderboard endpoint for GET requests with test_mode
        if self.path.startswith('/update_leaderboard'):
            logging.info(f"GET request for {self.path}")
            
            # Parse the URL and query parameters
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            
            # Check if it's a test mode request
            if 'test_mode' in query_params:
                logging.info("Handling test mode request for update_leaderboard")
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                
                response = {
                    'success': True,
                    'message': 'Test mode - no data was updated',
                    'test': True
                }
                
                self.wfile.write(json.dumps(response).encode('utf-8'))
                return

        # Provide leaderboard data from player_statistics.csv
        if self.path.startswith('/leaderboard'):
            client_ip = self.address_string()
            logging.info(f"📊 GET /leaderboard request from {client_ip}")
            try:
                stats = self.read_csv_file('player_statistics.csv')
                logging.info(f"   → Loaded {len(stats)} player statistics")
                
                # Determine last update date from Date column (max string YYYY-MM-DD)
                dates = [str(row.get('Date')).strip() for row in stats if row.get('Date')]
                last_update = max(dates) if dates else None
                logging.info(f"   → Last update date: {last_update}")
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response_data = {
                    'success': True,
                    'lastUpdate': last_update,
                    'playerStats': stats
                }
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
                logging.info(f"✓ Leaderboard data sent successfully to {client_ip}")
                return
            except Exception as e:
                logging.error(f"❌ Failed to load leaderboard: {str(e)}")
                self.send_error_response(500, f"Failed to load leaderboard: {str(e)}")
                return
        
        # Log the actual path requested for other GET requests
        logging.info(f"GET request for {self.path}")
        
        return SimpleHTTPRequestHandler.do_GET(self)
    
    def do_POST(self):
        # Handle /update_leaderboard endpoint
        if self.path == '/update_leaderboard':
            client_ip = self.address_string()
            logging.info("=" * 80)
            logging.info(f"📥 RECEIVED POST REQUEST to {self.path} from {client_ip}")
            logging.info("=" * 80)
            
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                # Parse incoming JSON data
                logging.info("🔍 Step 1: Parsing JSON data...")
                data = json.loads(post_data.decode('utf-8'))
                logging.info("✓ JSON data parsed successfully")
                
                # Get new records from request
                new_records = data.get('newRecords', [])
                logging.info(f"📊 Step 2: Received {len(new_records)} new game records")
                
                # Log details of new records
                if new_records:
                    dates_in_request = set()
                    players_in_request = set()
                    for record in new_records:
                        if record.get('Time'):
                            dates_in_request.add(record['Time'])
                        if record.get('Player'):
                            players_in_request.add(record['Player'])
                    logging.info(f"   - Game dates: {sorted(dates_in_request)}")
                    logging.info(f"   - Players involved: {sorted(players_in_request)}")
                    logging.info(f"   - Total records to add: {len(new_records)}")
                
                # Read existing game records
                logging.info("📖 Step 3: Reading existing game records...")
                game_records = self.read_csv_file('team_building_record.csv')
                logging.info(f"✓ Successfully read {len(game_records)} existing records from database")

                # Extract dates (YYYY-MM-DD) from new_records and existing records
                logging.info("🔍 Step 4: Validating data - checking for duplicate dates...")
                def extract_date_str(t):
                    s = str(t or '').strip()
                    return s if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s) else None

                new_dates = {d for d in (extract_date_str(r.get('Time')) for r in new_records) if d}
                existing_dates = {d for d in (extract_date_str(r.get('Time')) for r in game_records) if d}

                # If any date already exists, do not update
                duplicate_dates = sorted(list(new_dates & existing_dates))
                if duplicate_dates:
                    logging.warning(f"⚠️ VALIDATION FAILED: Duplicate date(s) detected: {duplicate_dates}")
                    logging.info("❌ Update operation REJECTED - duplicate dates found")
                    logging.info("=" * 80)
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'success': False,
                        'message': '已经存在改日期记录，请核对',
                        'duplicateDates': duplicate_dates
                    }).encode('utf-8'))
                    return
                
                logging.info("✓ Validation passed - no duplicate dates found")
                
                # Add new records
                logging.info("➕ Step 5: Merging new records with existing data...")
                original_count = len(game_records)
                game_records.extend(new_records)
                new_count = len(game_records)
                logging.info(f"✓ Successfully merged: {original_count} + {len(new_records)} = {new_count} total records")
                
                # Save updated game records to production
                logging.info("💾 Step 6: Saving game records to production database...")
                self.write_csv_file('team_building_record.csv', game_records)
                logging.info("✓ Successfully saved game records to /var/www/airankingx.com/team_building_record.csv")
                
                # Try to save to codebase (may fail due to permissions, but don't stop the process)
                logging.info("💾 Step 7: Syncing game records to codebase...")
                try:
                    codebase_path = os.path.join(CODEBASE_PATH, 'team_building_record.csv')
                    self.write_csv_file(codebase_path, game_records)
                    logging.info(f"✓ Successfully synced game records to {codebase_path}")
                except Exception as e:
                    logging.warning(f"⚠️ Failed to sync to codebase (non-critical): {str(e)}")
                    logging.warning("   → You can manually sync later using: sudo sync_csv_back.sh")
                
                # Calculate player statistics
                logging.info("🧮 Step 8: Calculating player statistics...")
                player_stats = self.calculate_player_statistics(game_records)
                logging.info(f"✓ Successfully calculated statistics for {len(player_stats)} players")
                
                # Log top 3 players
                if len(player_stats) > 0:
                    top_3 = sorted(player_stats, key=lambda x: x.get('Ranking', 999))[:3]
                    logging.info("   📊 Top 3 players:")
                    for player in top_3:
                        logging.info(f"      #{player['Ranking']} {player['Player']}: {player['WinChips']} chips")
                
                # Save updated player statistics to production
                logging.info("💾 Step 9: Saving player statistics to production database...")
                self.write_csv_file('player_statistics.csv', player_stats)
                logging.info("✓ Successfully saved player statistics to /var/www/airankingx.com/player_statistics.csv")
                
                # Try to save to codebase (may fail due to permissions, but don't stop the process)
                logging.info("💾 Step 10: Syncing player statistics to codebase...")
                try:
                    codebase_path = os.path.join(CODEBASE_PATH, 'player_statistics.csv')
                    self.write_csv_file(codebase_path, player_stats)
                    logging.info(f"✓ Successfully synced player statistics to {codebase_path}")
                except Exception as e:
                    logging.warning(f"⚠️ Failed to sync player stats to codebase (non-critical): {str(e)}")
                    logging.warning("   → You can manually sync later using: sudo sync_csv_back.sh")

                # Send success response with updated data
                logging.info("📤 Step 11: Preparing success response...")
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                
                response = {
                    'success': True,
                    'gameRecords': game_records,
                    'playerStats': player_stats
                }
                
                response_size = len(json.dumps(response))
                logging.info(f"✓ Response prepared (size: {response_size} bytes)")
                logging.info("📤 Sending success response to client...")
                self.wfile.write(json.dumps(response).encode('utf-8'))
                
                logging.info("=" * 80)
                logging.info("🎉 UPDATE LEADERBOARD SUCCESS!")
                logging.info(f"   - Added {len(new_records)} new game records")
                logging.info(f"   - Updated {len(player_stats)} player statistics")
                logging.info(f"   - Client: {client_ip}")
                logging.info("=" * 80)
                
            except json.JSONDecodeError as e:
                logging.error("=" * 80)
                logging.error(f"❌ JSON PARSE ERROR: {str(e)}")
                logging.error(f"   - Client: {client_ip}")
                logging.error(f"   - Raw data length: {len(post_data)} bytes")
                logging.error("=" * 80)
                self.send_error_response(400, f"Invalid JSON data: {str(e)}")
                
            except Exception as e:
                # Send error response
                logging.error("=" * 80)
                logging.error(f"❌ SERVER ERROR during update_leaderboard")
                logging.error(f"   - Error type: {type(e).__name__}")
                logging.error(f"   - Error message: {str(e)}")
                logging.error(f"   - Client: {client_ip}")
                import traceback
                logging.error(f"   - Traceback:\n{traceback.format_exc()}")
                logging.error("=" * 80)
                self.send_error_response(500, str(e))
        else:
            # Handle other POST requests (404 Not Found)
            logging.warning(f"Received POST request to unknown endpoint: {self.path}")
            self.send_error_response(404, "Endpoint not found")
    
    def send_error_response(self, status_code, message):
        """Helper method to send error responses."""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        error_response = {
            'success': False,
            'message': message
        }
        
        self.wfile.write(json.dumps(error_response).encode('utf-8'))
    
    def read_csv_file(self, filename):
        """Read CSV file and return as list of dictionaries"""
        file_path = self.get_file_path(filename)
        if not os.path.exists(file_path):
            logging.warning(f"CSV file not found: {file_path}")
            return []
            
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                return list(reader)
        except Exception as e:
            logging.error(f"Error reading CSV file {filename}: {str(e)}")
            raise
    
    def write_csv_file(self, filename, data):
        """Write list of dictionaries to CSV file"""
        if not data:
            logging.warning(f"⚠️ No data to write to {filename}")
            return
            
        file_path = self.get_file_path(filename)
        backup_path = f"{file_path}.bak"
        
        logging.debug(f"   → Writing {len(data)} records to {file_path}")
        
        try:
            fieldnames = data[0].keys()
            
            # Create backup of existing file
            if os.path.exists(file_path):
                try:
                    # Use shutil.copy2 to preserve permissions and metadata
                    import shutil
                    original_size = os.path.getsize(file_path)
                    shutil.copy2(file_path, backup_path)
                    logging.debug(f"   → Created backup: {backup_path} ({original_size} bytes)")
                    
                    # Ensure backup has correct permissions
                    os.chmod(backup_path, 0o664)
                except (IOError, OSError, PermissionError) as e:
                    logging.warning(f"⚠️ Failed to create backup for {filename}: {str(e)}")
                    # Continue anyway - backup failure shouldn't stop the write
            
            # Write to a temporary file first
            temp_path = f"{file_path}.tmp"
            try:
                with open(temp_path, 'w', newline='', encoding='utf-8') as file:
                    writer = csv.DictWriter(file, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(data)
                
                # Set correct permissions before moving
                os.chmod(temp_path, 0o664)
                
                # Atomically replace the original file
                os.replace(temp_path, file_path)
                
                # Ensure final file has correct permissions
                os.chmod(file_path, 0o664)
                
                # Get file stats
                final_size = os.path.getsize(file_path)
                file_owner = os.stat(file_path)
                logging.debug(f"   → File written successfully: {final_size} bytes, owner: {file_owner.st_uid}:{file_owner.st_gid}")
                
            except (IOError, OSError, PermissionError) as e:
                logging.error(f"❌ Error writing to CSV file {filename}: {str(e)}")
                logging.error(f"   → File path: {file_path}")
                logging.error(f"   → Process UID: {os.getuid()}, GID: {os.getgid()}")
                # Clean up temp file if it exists
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except:
                        pass
                raise
                
        except PermissionError as e:
            logging.error(f"❌ Permission denied writing to {filename}: {str(e)}")
            logging.error(f"   → File path: {file_path}")
            logging.error(f"   → Current process UID: {os.getuid()}, GID: {os.getgid()}")
            if os.path.exists(file_path):
                stat_info = os.stat(file_path)
                logging.error(f"   → File owner: {stat_info.st_uid}:{stat_info.st_gid}, permissions: {oct(stat_info.st_mode)}")
            raise
        except Exception as e:
            logging.error(f"❌ Unexpected error writing to CSV file {filename}: {str(e)}")
            raise
    
    def get_file_path(self, filename):
        """Get absolute path for a file relative to the server directory."""
        server_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(server_dir, filename)
    
    def calculate_player_statistics(self, game_records):
        """Update player statistics based on baseline file and all dated game records.

        - Baseline: load from player_statistics_251029.csv.
        - Aggregate across ALL records that have a valid YYYY-MM-DD Time.
        - Use 'Chips' for updates, recompute rates, add Date (latest), round WinChips, and rank.
        """

        def extract_date_str(time_str):
            s = str(time_str or '').strip()
            return s if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s) else None

        # 1) Build stats map from baseline file
        stats_map = {}
        baseline_records = self.read_csv_file('player_statistics_251029.csv')
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

        # 2) Determine max date, and the set of records with valid dates
        date_strs = [extract_date_str(rec.get('Time')) for rec in game_records]
        date_strs = [ds for ds in date_strs if ds is not None]
        latest_date_str = max(date_strs) if date_strs else None
        logging.info(f"Latest update date (server): {latest_date_str}")

        # 3) Aggregate all records with valid dates (or all if none have a date)
        if date_strs:
            records_to_apply = [rec for rec in game_records if extract_date_str(rec.get('Time')) is not None]
        else:
            records_to_apply = game_records[:]

        # 4) Apply updates using 'Chips'
        for record in records_to_apply:
            player_name = record.get('Player')
            if not player_name:
                continue
            try:
                chips = float(record.get('FinalChips', 0) or 0)
            except (ValueError, TypeError):
                logging.warning(f"Invalid FinalChips value for player {player_name}: {record.get('Chips')}")
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

            player_stat['WinChips'] = float(player_stat.get('WinChips', 0) or 0) + chips
            player_stat['AttendCount'] = int(player_stat.get('AttendCount', 0) or 0) + 1

            if chips > 0:
                player_stat['WinCount'] = int(player_stat.get('WinCount', 0) or 0) + 1
            elif chips < 0:
                player_stat['LoseCount'] = int(player_stat.get('LoseCount', 0) or 0) + 1
            else:
                player_stat['PeaceCount'] = int(player_stat.get('PeaceCount', 0) or 0) + 1

        # 5) Build list, compute rate, round WinChips, add Date
        player_stats = []
        for _, stat in stats_map.items():
            attend = int(stat.get('AttendCount', 0) or 0)
            wins = int(stat.get('WinCount', 0) or 0)
            win_rate = (wins / attend) * 100 if attend > 0 else 0
            stat['WinChips'] = round(float(stat.get('WinChips', 0) or 0), 1)
            stat['WinningRate'] = f"{win_rate:.2f}%"
            stat['Date'] = latest_date_str
            player_stats.append(stat)

        # 6) Sort and rank
        player_stats.sort(key=lambda x: float(x.get('WinChips', 0) or 0), reverse=True)
        for i, stat in enumerate(player_stats):
            stat['Ranking'] = i + 1
            logging.info(f"Player {stat['Player']} ranking (server): {stat['Ranking']}")

        return player_stats

def get_ip_address():
    """Get the server's IP address to display in the startup message."""
    try:
        # Get the server hostname
        hostname = socket.gethostname()
        # Get the IP address
        ip_address = socket.gethostbyname(hostname)
        return ip_address
    except Exception as e:
        logging.error(f"Failed to get IP address: {str(e)}")
        return "unknown"

def run(server_class=HTTPServer, handler_class=CustomHandler, port=PORT):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    
    ip_address = get_ip_address()
    
    # Log startup information
    logging.info("=" * 80)
    logging.info("🚀 AIRANKINGX SERVER STARTING")
    logging.info("=" * 80)
    logging.info(f"Server IP: {ip_address}")
    logging.info(f"Server Port: {port}")
    logging.info(f"Process UID: {os.getuid()}, GID: {os.getgid()}")
    logging.info(f"Working Directory: {os.getcwd()}")
    logging.info(f"Codebase Path: {CODEBASE_PATH}")
    logging.info(f"Log File: {os.path.abspath(LOG_FILE)}")
    
    # Check file permissions
    csv_files = ['team_building_record.csv', 'player_statistics.csv', 'player_statistics_251029.csv']
    logging.info("Checking CSV files:")
    for csv_file in csv_files:
        file_path = os.path.join(os.getcwd(), csv_file)
        if os.path.exists(file_path):
            stat_info = os.stat(file_path)
            size = os.path.getsize(file_path)
            logging.info(f"   ✓ {csv_file}: {size} bytes, owner: {stat_info.st_uid}:{stat_info.st_gid}, perms: {oct(stat_info.st_mode)}")
        else:
            logging.warning(f"   ⚠️ {csv_file}: NOT FOUND")
    
    # Check codebase directory access
    if os.path.exists(CODEBASE_PATH):
        logging.info(f"Codebase directory accessible: {CODEBASE_PATH}")
        if os.access(CODEBASE_PATH, os.W_OK):
            logging.info("   ✓ Codebase directory is WRITABLE")
        else:
            logging.warning("   ⚠️ Codebase directory is NOT writable (sync will fail)")
    else:
        logging.warning(f"   ⚠️ Codebase directory NOT FOUND: {CODEBASE_PATH}")
    
    logging.info("=" * 80)
    logging.info("✓ Server ready to accept connections")
    logging.info("=" * 80)
    
    print(f"🚀 AIRankingX Server Started")
    print(f"   Server: {ip_address}:{port}")
    print(f"   Logs: {LOG_FILE}")
    print(f"   Press Ctrl+C to stop")
    print("")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logging.info("=" * 80)
        logging.info("🛑 Server shutdown initiated by user")
        logging.info("=" * 80)
        print("\n🛑 Shutting down server...")
        httpd.server_close()
    except Exception as e:
        logging.error("=" * 80)
        logging.error(f"❌ Server error: {str(e)}")
        logging.error("=" * 80)
        print(f"❌ Server error: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            PORT = int(sys.argv[1])
        except ValueError:
            logging.error(f"Invalid port number: {sys.argv[1]}")
            print(f"Invalid port number: {sys.argv[1]}")
            sys.exit(1)
    
    logging.info(f"Server starting with password: {PassWord}, port: {PORT}")
    run(port=PORT) 