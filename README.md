# SupabaseZombi

Keep your Supabase databases alive like a zombie! 🧟‍♂️

[한국어 문서](README.ko.md)

## Features

- Runs automatically every 24 hours
- Inserts random 1-10 entries per run
- Auto cleanup when exceeds 50 entries (maintains ~30)
- Supports multiple Supabase databases
- Runs in Docker container
- Telegram notification support (optional)

## Quick Start

```bash
# 1. Clone repository
git clone https://github.com/shsm0520/supabasezombi.git
cd supabasezombi

# 2. Edit config.json with your Supabase credentials
# 3. (Optional) Add Telegram settings to docker-compose.yml
# 4. Start service
docker-compose up -d
```

## Setup

### 1. Clone Repository

```bash
git clone https://github.com/shsm0520/supabasezombi.git
cd supabasezombi
```

### 2. Configure Supabase

Edit `config.json` with your database credentials:

```json
[
  {
    "name": "Database 1",
    "supabase_url": "https://your-project.supabase.co",
    "supabase_key": "your-anon-key",
    "table_name": "keep-alive"
  },
  {
    "name": "Database 2",
    "supabase_url": "https://another-project.supabase.co",
    "supabase_key_env": "SUPABASE_KEY_2",
    "table_name": "keep-alive"
  }
]
```

### 3. (Optional) Configure Telegram Notifications & Customize Settings

Uncomment and edit the desired settings in `docker-compose.yml`:

```yaml
environment:
  - TZ=Asia/Seoul
  # Telegram notification (optional)
  - TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
  - TELEGRAM_CHAT_ID=123456789
  # Configuration customization (optional)
  - RUN_INTERVAL_HOURS=24 # Run interval in hours
  - RANDOM_INSERT_MIN=1 # Minimum inserts per run
  - RANDOM_INSERT_MAX=10 # Maximum inserts per run
  - MAX_DATA_LIMIT=50 # Delete when exceeds this
  - TARGET_DATA_COUNT=30 # Target count after deletion
```

## Usage

### Docker Compose (Recommended)

```bash
# Start service (no build required!)
docker-compose up -d

# Check logs
docker-compose logs -f supabasezombi

# Stop service
docker-compose down

# Restart after changes
docker-compose restart
```

### Docker Direct (Alternative)

```bash
# Clone first
git clone https://github.com/shsm0520/supabasezombi.git
cd supabasezombi

# Edit config.json, then run
docker run -d \
  --name supabasezombi \
  --restart unless-stopped \
  -v $(pwd)/main_standalone.py:/app/main.py:ro \
  -v $(pwd)/config.json:/app/config.json:ro \
  -e TZ=Asia/Seoul \
  python:3.11-slim \
  sh -c "pip install --no-cache-dir supabase requests && python -u /app/main.py"

# Check logs
docker logs -f supabasezombi

# Stop container
docker stop supabasezombi
docker rm supabasezombi
```

### Python Direct (Local Development)

```bash
# Clone repository
git clone https://github.com/shsm0520/supabasezombi.git
cd supabasezombi

# Install dependencies
pip install supabase requests

# Edit config.json, then run
python main_standalone.py
```

## Logs

Check container logs to see the execution status:

```bash
docker logs -f supabasezombi
```

Example output:

```
2025-10-30 09:00:00 - INFO - SupabaseZombi started. Running every 24 hours 🧟‍♂️

2025-10-30 09:00:00 - INFO - == '2025-10-30 09:00:00' Run start (2 servers)
2025-10-30 09:00:00 - INFO - = Server #1: My Database
2025-10-30 09:00:01 - INFO -   ✓ SUCCESS | #15 data | Inserted: 7 | Deleted: 0
2025-10-30 09:00:01 - INFO - = Server #2: Another Database
2025-10-30 09:00:02 - INFO -   ✓ SUCCESS | #53 data | Inserted: 5 | Deleted: 23
2025-10-30 09:00:02 - INFO - == All run complete (2/2)
2025-10-30 09:00:02 - INFO - == Next run: '2025-10-31 09:00:02'
```

## Environment Variables

Manage sensitive information with environment variables.

Add to `docker-compose.yml`:

```yaml
environment:
  - SUPABASE_KEY_1=your-key-here
  - SUPABASE_KEY_2=another-key-here
```

Then reference in `config.json`:

```json
{
  "name": "Database 1",
  "supabase_url": "https://your-project.supabase.co",
  "supabase_key_env": "SUPABASE_KEY_1",
  "table_name": "keep-alive"
}
```

## Troubleshooting

### Container keeps restarting

- Check logs: `docker logs supabasezombi`
- Verify config.json is correct
- Ensure Supabase URL and Key are valid

### Run immediately

```bash
docker restart supabasezombi
```

## Telegram Notification

Get daily reports via Telegram:

1. Create bot via [@BotFather](https://t.me/BotFather)
2. Get your Chat ID via [@userinfobot](https://t.me/userinfobot)
3. Uncomment and edit in `docker-compose.yml`:
   ```yaml
   environment:
     - TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
     - TELEGRAM_CHAT_ID=123456789
   ```

Notification includes:

- Execution time and duration
- Success/failure count
- Failed server names (if any)

## Credits

Based on [supabase-inactive-fix](https://github.com/travisvn/supabase-inactive-fix) by [travisvn](https://github.com/travisvn)

Additional features:

- Randomized insert count (1-10 per run)
- Automatic data cleanup when exceeds 50 entries
- Simplified single-file implementation
- No build required Docker deployment
- Enhanced logging format
- Telegram notification support

## License

MIT License - Feel free to use!

---

**Star ⭐ this repo if you find it useful!**
