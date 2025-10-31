"""
SupabaseZombi - Keep your Supabase databases alive like a zombie! 🧟‍♂️

Based on: https://github.com/travisvn/supabase-inactive-fix
Original author: travisvn

Modified with enhancements:
- Randomized insert count (1-10 per run)
- Automatic cleanup when exceeds 50 entries
- Single-file implementation
- Enhanced logging

License: MIT
"""

import json
import os
import logging
import time
import random
import string
import secrets
import requests
from datetime import datetime, timedelta
from supabase import create_client, Client

# ========== Configuration ==========
run_interval_hours = int(os.getenv('RUN_INTERVAL_HOURS', '24'))      # Run every 24 hours
random_insert_min = int(os.getenv('RANDOM_INSERT_MIN', '1'))         # Minimum inserts per run
random_insert_max = int(os.getenv('RANDOM_INSERT_MAX', '10'))        # Maximum inserts per run
max_data_limit = int(os.getenv('MAX_DATA_LIMIT', '50'))              # Delete when exceeds this
target_data_count = int(os.getenv('TARGET_DATA_COUNT', '30'))        # Target count after deletion
max_runs_before_restart = int(os.getenv('MAX_RUNS_BEFORE_RESTART', '0'))  # 0 = never restart

# ========== Logging Setup ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Suppress verbose HTTP logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


# ========== Helper Functions ==========
def send_telegram_message(bot_token: str, chat_id: str, message: str) -> bool:
    """Send a message via Telegram Bot API"""
    if not bot_token or not chat_id:
        return False
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, data=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        logging.warning(f"Failed to send Telegram message: {e}")
        return False


def generate_random_string(length=10):
    """Generate a secure random string"""
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))


class SupabaseClient:
    """Simple Supabase client wrapper"""
    
    def __init__(self, url: str, key: str, table_name: str):
        self.url = url
        self.key = key
        self.table_name = table_name
        self.client: Client = create_client(url, key)

    def insert_random_name(self, random_name: str) -> bool:
        """Insert a random name into the table"""
        try:
            data = {"name": random_name}
            self.client.table(self.table_name).insert(data).execute()
            return True
        except Exception as e:
            logging.error(f"Failed to insert: {e}")
            return False

    def get_table_count(self) -> int:
        """Get the count of entries in the table"""
        try:
            response = self.client.table(self.table_name).select("*").execute()
            return len(response.data)
        except Exception as e:
            logging.error(f"Failed to get count: {e}")
            return None

    def delete_random_entry(self) -> bool:
        """Delete a random entry from the table"""
        try:
            response = self.client.table(self.table_name).select("*").execute()
            if not response.data:
                return False

            entry_to_delete = random.choice(response.data)
            entry_id = entry_to_delete.get('id')
            
            if entry_id is None:
                return False

            self.client.table(self.table_name).delete().eq('id', entry_id).execute()
            return True
        except Exception as e:
            logging.error(f"Failed to delete: {e}")
            return False


# ========== Main Logic ==========
def run_keepalive():
    """Execute the keep-alive logic once"""
    try:
        with open('config.json', 'r') as config_file:
            configs = json.load(config_file)
    except FileNotFoundError:
        logging.error("Configuration file 'config.json' not found.")
        return
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing 'config.json': {e}")
        return

    # Read Telegram settings from environment variables
    telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', '')

    success_count = 0
    total_count = len(configs)
    failed_databases = []
    has_errors = False
    
    start_time = datetime.now()

    for idx, config in enumerate(configs, 1):
        name = config.get('name', 'Unnamed Database')
        url = config.get('supabase_url')
        key = config.get('supabase_key')
        table_name = config.get('table_name', 'KeepAlive')

        # Check for environment variable
        key_env_var = config.get('supabase_key_env')
        if key_env_var:
            key = os.getenv(key_env_var)

        if not url or not key:
            logging.info(f"= Server #{idx}: {name}")
            logging.info(f"  ❌ FAILED | Missing credentials")
            failed_databases.append(name)
            has_errors = True
            continue

        logging.info(f"= Server #{idx}: {name}")

        try:
            # Initialize Supabase client
            supabase_client = SupabaseClient(url, key, table_name)

            # Insert random number of entries
            num_inserts = random.randint(random_insert_min, random_insert_max)
            insert_success_count = 0
            
            for _ in range(num_inserts):
                random_name = generate_random_string(10)
                if supabase_client.insert_random_name(random_name):
                    insert_success_count += 1
                    time.sleep(0.1)  # Small delay between inserts
            
            if insert_success_count == 0:
                logging.info(f"  ❌ FAILED | All inserts failed")
                failed_databases.append(name)
                has_errors = True
                continue

            # Get current count
            count = supabase_client.get_table_count()
            if count is None:
                logging.info(f"  ❌ FAILED | Count error")
                failed_databases.append(name)
                has_errors = True
                continue

            # Delete excess entries if needed
            delete_count = 0
            if count > max_data_limit:
                num_deletes = count - target_data_count
                for _ in range(num_deletes):
                    if supabase_client.delete_random_entry():
                        delete_count += 1
                    time.sleep(0.1)
                
                if delete_count > 0:
                    logging.info(f"  ✓ SUCCESS | #{count} data | Inserted: {insert_success_count} | Deleted: {delete_count}")
                else:
                    logging.info(f"  ⚠️  SUCCESS | #{count} data | Inserted: {insert_success_count} | Delete failed")
                    has_errors = True
            else:
                logging.info(f"  ✓ SUCCESS | #{count} data | Inserted: {insert_success_count} | Deleted: 0")

            success_count += 1

        except Exception as e:
            logging.info(f"  ❌ FAILED | {str(e)[:50]}")
            failed_databases.append(name)
            has_errors = True

    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    if success_count == total_count and not has_errors:
        status_msg = f"✅ All run complete ({success_count}/{total_count})"
        logging.info(f"== {status_msg}")
    elif success_count == total_count and has_errors:
        status_msg = f"⚠️ All run complete with warnings ({success_count}/{total_count})"
        logging.info(f"== {status_msg}")
    else:
        status_msg = f"❌ Run complete with errors ({success_count}/{total_count})"
        logging.info(f"== {status_msg}")
        if failed_databases:
            logging.info(f"   Failed servers: {', '.join(failed_databases)}")
    
    # Send Telegram notification
    if telegram_bot_token and telegram_chat_id:
        telegram_msg = f"<b>🧟‍♂️ SupabaseZombi Report</b>\n\n"
        telegram_msg += f"📅 Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        telegram_msg += f"⏱ Duration: {duration:.1f}s\n"
        telegram_msg += f"📊 Result: {success_count}/{total_count} servers\n\n"
        
        if success_count == total_count and not has_errors:
            telegram_msg += "✅ All databases updated successfully!"
        elif success_count == total_count and has_errors:
            telegram_msg += "⚠️ All databases updated with warnings"
        else:
            telegram_msg += f"❌ {len(failed_databases)} database(s) failed\n"
            if failed_databases:
                telegram_msg += f"Failed: {', '.join(failed_databases)}"
        
        send_telegram_message(telegram_bot_token, telegram_chat_id, telegram_msg)


def main():
    """Main function that runs the keep-alive service continuously"""
    logging.info("SupabaseZombi started. Running every 24 hours 🧟‍♂️")
    if max_runs_before_restart > 0:
        logging.info(f"Service will restart after {max_runs_before_restart} runs")
    logging.info("")
    
    run_count = 0
    
    while True:
        try:
            run_count += 1
            current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Get server count
            try:
                with open('config.json', 'r') as config_file:
                    configs = json.load(config_file)
                    server_count = len(configs)
            except:
                server_count = 0
            
            logging.info(f"== '{current_date}' Run start ({server_count} servers)")
            run_keepalive()
            
            # Check restart condition
            if max_runs_before_restart > 0 and run_count >= max_runs_before_restart:
                logging.info(f"Reached maximum run count ({max_runs_before_restart}). Restarting...")
                break
            
            # Calculate next run time
            next_run_time = datetime.now() + timedelta(hours=run_interval_hours)
            logging.info(f"== Next run: '{next_run_time.strftime('%Y-%m-%d %H:%M:%S')}'")
            logging.info("")
            
            time.sleep(run_interval_hours * 3600)
            
        except KeyboardInterrupt:
            logging.info("Service stopped by user")
            break
        except Exception as e:
            logging.error(f"❌ Critical error: {e}")
            logging.info("Retrying in 1 hour...")
            time.sleep(3600)


if __name__ == "__main__":
    main()
