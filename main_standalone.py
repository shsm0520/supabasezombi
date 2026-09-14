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
import sys
import logging
import time
import random
import string
import secrets
import requests
from datetime import datetime, timedelta
from supabase import create_client, Client

# ========== Helper Functions for Configuration & Validation ==========
def parse_int_env(name: str, default: int) -> int:
    val_str = os.getenv(name)
    if val_str is None or val_str.strip() == '':
        return default
    try:
        return int(val_str)
    except ValueError as e:
        raise ValueError(f"Environment variable '{name}' must be an integer (got: '{val_str}')") from e


def get_validated_env_config():
    """Load and validate environment variable settings."""
    run_interval_hours = parse_int_env('RUN_INTERVAL_HOURS', 24)
    random_insert_min = parse_int_env('RANDOM_INSERT_MIN', 1)
    random_insert_max = parse_int_env('RANDOM_INSERT_MAX', 10)
    max_data_limit = parse_int_env('MAX_DATA_LIMIT', 50)
    target_data_count = parse_int_env('TARGET_DATA_COUNT', 30)
    max_runs_before_restart = parse_int_env('MAX_RUNS_BEFORE_RESTART', 0)

    if run_interval_hours <= 0:
        raise ValueError(f"RUN_INTERVAL_HOURS must be greater than 0 (got: {run_interval_hours})")
    if random_insert_min < 1:
        raise ValueError(f"RANDOM_INSERT_MIN must be at least 1 (got: {random_insert_min})")
    if random_insert_max < random_insert_min:
        raise ValueError(f"RANDOM_INSERT_MAX ({random_insert_max}) must be greater than or equal to RANDOM_INSERT_MIN ({random_insert_min})")
    if max_data_limit <= 0:
        raise ValueError(f"MAX_DATA_LIMIT must be greater than 0 (got: {max_data_limit})")
    if target_data_count < 0:
        raise ValueError(f"TARGET_DATA_COUNT must be greater than or equal to 0 (got: {target_data_count})")
    if target_data_count > max_data_limit:
        raise ValueError(f"TARGET_DATA_COUNT ({target_data_count}) cannot exceed MAX_DATA_LIMIT ({max_data_limit})")
    if max_runs_before_restart < 0:
        raise ValueError(f"MAX_RUNS_BEFORE_RESTART must be greater than or equal to 0 (got: {max_runs_before_restart})")

    return {
        'run_interval_hours': run_interval_hours,
        'random_insert_min': random_insert_min,
        'random_insert_max': random_insert_max,
        'max_data_limit': max_data_limit,
        'target_data_count': target_data_count,
        'max_runs_before_restart': max_runs_before_restart
    }


def validate_config_file(config_path='config.json'):
    """Validate config.json file existence, JSON validity, structure, and database credentials."""
    if not os.path.exists(config_path):
        raise ValueError(f"Configuration file '{config_path}' not found.")

    try:
        with open(config_path, 'r', encoding='utf-8') as config_file:
            configs = json.load(config_file)
    except json.JSONDecodeError as e:
        raise ValueError(f"Error parsing '{config_path}': {e}") from e

    if not isinstance(configs, list):
        raise ValueError(f"Configuration in '{config_path}' must be a JSON array (list).")

    if len(configs) == 0:
        raise ValueError(f"Configuration in '{config_path}' is empty. At least one database configuration is required.")

    for idx, config in enumerate(configs, 1):
        if not isinstance(config, dict):
            raise ValueError(f"Server #{idx} configuration must be a JSON object.")

        name = config.get('name')
        if not name or not isinstance(name, str) or not name.strip():
            raise ValueError(f"Server #{idx} is missing a valid 'name'.")

        url = config.get('supabase_url')
        if not url or not isinstance(url, str) or not url.strip():
            raise ValueError(f"Server #{idx} ('{name}') is missing 'supabase_url'.")

        key = config.get('supabase_key')
        key_env_var = config.get('supabase_key_env')

        if key_env_var:
            if not isinstance(key_env_var, str) or not key_env_var.strip():
                raise ValueError(f"Server #{idx} ('{name}') has an invalid 'supabase_key_env'.")
            env_val = os.getenv(key_env_var)
            if not env_val or not env_val.strip():
                raise ValueError(f"Server #{idx} ('{name}') references environment variable '{key_env_var}' which is not set or empty.")
        elif not key or not isinstance(key, str) or not key.strip():
            raise ValueError(f"Server #{idx} ('{name}') must specify either 'supabase_key' or a valid 'supabase_key_env'.")

        table_name = config.get('table_name', 'KeepAlive')
        if not table_name or not isinstance(table_name, str) or not table_name.strip():
            raise ValueError(f"Server #{idx} ('{name}') has an invalid 'table_name'.")

    return configs


def validate_all(config_path='config.json'):
    """Validate both environment configuration and config.json file."""
    env_cfg = get_validated_env_config()
    configs = validate_config_file(config_path)
    return env_cfg, configs

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
        """Get the exact count of entries in the table"""
        try:
            response = self.client.table(self.table_name).select("*", count="exact", head=True).execute()
            return response.count if response.count is not None else 0
        except Exception as e:
            logging.error(f"Failed to get count: {e}")
            return None

    def delete_excess_entries(self, num_to_delete: int, batch_size: int = 500) -> int:
        """Delete excess entries in batches of IDs"""
        if num_to_delete <= 0:
            return 0

        deleted_total = 0
        remaining_to_delete = num_to_delete

        while remaining_to_delete > 0:
            current_batch_limit = min(remaining_to_delete, batch_size)
            try:
                # Query IDs to delete (limiting query size)
                response = self.client.table(self.table_name).select("id").limit(current_batch_limit).execute()
                if not response.data:
                    break

                ids_to_delete = [row.get('id') for row in response.data if row.get('id') is not None]
                if not ids_to_delete:
                    break

                # Delete batch by IDs
                del_response = self.client.table(self.table_name).delete().in_("id", ids_to_delete).execute()
                deleted_in_batch = len(del_response.data) if del_response.data is not None else len(ids_to_delete)
                deleted_total += deleted_in_batch
                remaining_to_delete -= deleted_in_batch

                if deleted_in_batch == 0:
                    break
            except Exception as e:
                logging.error(f"Failed batch delete: {e}")
                break

        return deleted_total


# ========== Main Logic ==========
def run_keepalive(env_cfg=None, configs=None, config_path='config.json'):
    """Execute the keep-alive logic once"""
    if env_cfg is None or configs is None:
        try:
            env_cfg, configs = validate_all(config_path)
        except ValueError as e:
            logging.error(f"Configuration validation failed: {e}")
            return

    random_insert_min = env_cfg['random_insert_min']
    random_insert_max = env_cfg['random_insert_max']
    max_data_limit = env_cfg['max_data_limit']
    target_data_count = env_cfg['target_data_count']

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
                delete_count = supabase_client.delete_excess_entries(num_deletes)
                
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
    try:
        env_cfg, configs = validate_all('config.json')
    except ValueError as e:
        logging.error(f"❌ Startup configuration validation error: {e}")
        sys.exit(1)

    run_interval_hours = env_cfg['run_interval_hours']
    max_runs_before_restart = env_cfg['max_runs_before_restart']

    logging.info(f"SupabaseZombi started. Running every {run_interval_hours} hours 🧟‍♂️")
    if max_runs_before_restart > 0:
        logging.info(f"Service will restart after {max_runs_before_restart} runs")
    logging.info("")
    
    run_count = 0
    
    while True:
        try:
            # Re-validate config before each run
            env_cfg, configs = validate_all('config.json')
            run_interval_hours = env_cfg['run_interval_hours']
            max_runs_before_restart = env_cfg['max_runs_before_restart']

            run_count += 1
            current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            server_count = len(configs)
            
            logging.info(f"== '{current_date}' Run start ({server_count} servers)")
            run_keepalive(env_cfg, configs)
            
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
        except ValueError as e:
            logging.error(f"❌ Configuration error during execution: {e}")
            sys.exit(1)
        except Exception as e:
            logging.error(f"❌ Critical error: {e}")
            logging.info("Retrying in 1 hour...")
            time.sleep(3600)


if __name__ == "__main__":
    main()
