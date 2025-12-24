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
            try:
                stats = self.read_csv_file('player_statistics.csv')
                # Determine last update date from Date column (max string YYYY-MM-DD)
                dates = [str(row.get('Date')).strip() for row in stats if row.get('Date')]
                last_update = max(dates) if dates else None
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': True,
                    'lastUpdate': last_update,
                    'playerStats': stats
                }).encode('utf-8'))
                return
            except Exception as e:
                logging.error(f"Failed to load leaderboard: {str(e)}")
                self.send_error_response(500, f"Failed to load leaderboard: {str(e)}")
                return
        
        # Log the actual path requested for other GET requests
        logging.info(f"GET request for {self.path}")
        
        return SimpleHTTPRequestHandler.do_GET(self)
    
    def do_POST(self):
        # Handle /update_leaderboard endpoint
        if self.path == '/update_leaderboard':
            logging.info(f"Received POST request to {self.path}")
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                
                # Process the incoming data
                logging.info("Processing new game records...")
                # Get new records from request
                new_records = data.get('newRecords', [])
                logging.info(f"Received {len(new_records)} new records")
                
                # Read existing game records
                game_records = self.read_csv_file('team_building_record.csv')
                logging.info(f"Read {len(game_records)} existing records")

                # Extract dates (YYYY-MM-DD) from new_records and existing records
                def extract_date_str(t):
                    s = str(t or '').strip()
                    return s if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s) else None

                new_dates = {d for d in (extract_date_str(r.get('Time')) for r in new_records) if d}
                existing_dates = {d for d in (extract_date_str(r.get('Time')) for r in game_records) if d}

                # If any date already exists, do not update
                duplicate_dates = sorted(list(new_dates & existing_dates))
                if duplicate_dates:
                    logging.info(f"Duplicate date(s) detected, skipping update: {duplicate_dates}")
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'success': False,
                        'message': '已经存在改日期记录，请核对',
                        'duplicateDates': duplicate_dates
                    }).encode('utf-8'))
                    return
                
                # Add new records
                game_records.extend(new_records)
                
                # Save updated game records
                self.write_csv_file('team_building_record.csv', game_records)
                logging.info("Saved updated game records")
                self.write_csv_file(os.path.join(CODEBASE_PATH, 'team_building_record.csv'), game_records)
                logging.info("Saved updated game records to codebase")
                
                # Calculate player statistics
                player_stats = self.calculate_player_statistics(game_records)
                logging.info(f"Calculated statistics for {len(player_stats)} players")
                
                # Save updated player statistics
                self.write_csv_file('player_statistics.csv', player_stats)
                logging.info("Saved updated player statistics")
                self.write_csv_file(os.path.join(CODEBASE_PATH, 'player_statistics.csv'), player_stats)
                logging.info("Saved updated player statistics to codebase")

                # Send success response with updated data
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                
                response = {
                    'success': True,
                    'gameRecords': game_records,
                    'playerStats': player_stats
                }
                
                logging.info("Sending success response")
                self.wfile.write(json.dumps(response).encode('utf-8'))
                
            except json.JSONDecodeError as e:
                logging.error(f"Invalid JSON data: {str(e)}")
                self.send_error_response(400, f"Invalid JSON data: {str(e)}")
                
            except Exception as e:
                # Send error response
                logging.error(f"Error processing request: {str(e)}")
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
            logging.warning(f"No data to write to {filename}")
            return
            
        file_path = self.get_file_path(filename)
        backup_path = f"{file_path}.bak"
        
        try:
            fieldnames = data[0].keys()
            
            # Create backup of existing file
            if os.path.exists(file_path):
                try:
                    # Use shutil.copy2 to preserve permissions and metadata
                    import shutil
                    shutil.copy2(file_path, backup_path)
                    logging.info(f"Created backup of {filename} at {backup_path}")
                    
                    # Ensure backup has correct permissions
                    os.chmod(backup_path, 0o664)
                except (IOError, OSError, PermissionError) as e:
                    logging.error(f"Failed to create backup for {filename}: {str(e)}")
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
    
    logging.info(f"Starting server on {ip_address}:{port}")
    print(f"Starting server on {ip_address}:{port}")
    print(f"Server logs will be written to {LOG_FILE}")
    print(f"Press Ctrl+C to stop the server")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logging.info("Server shutdown initiated by user")
        print("\nShutting down server")
        httpd.server_close()
    except Exception as e:
        logging.error(f"Server error: {str(e)}")
        print(f"Server error: {str(e)}")

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