# MySQL to SmartSuite Sync

A robust, production-ready Python application for synchronizing data from MySQL databases to SmartSuite with idempotency, state tracking, and flexible scheduling.

## Features

- **Idempotent Sync**: Never creates duplicate records, handles updates intelligently
- **State Management**: SQLite-based tracking of sync history and record mappings
- **Flexible Mapping**: YAML-based configuration for complex field mappings and transformations
- **Incremental Sync**: Only processes changed records using timestamp-based queries
- **Scheduling**: Built-in scheduler with interval or cron-based execution
- **Robust Error Handling**: Comprehensive logging and graceful error recovery
- **Change Detection**: Hash-based comparison to skip unchanged records
- **Bi-directional Ready**: Architecture supports future MySQL ← SmartSuite sync

## Architecture

```
┌─────────────┐
│   MySQL DB  │
└──────┬──────┘
       │ Query
       ▼
┌─────────────────┐
│  Sync Engine    │ ◄───── YAML Config
│                 │
│  - Map Fields   │
│  - Transform    │
│  - Hash Check   │ ◄───── SQLite State
│  - Create/Update│
└────────┬────────┘
         │ API
         ▼
┌─────────────────┐
│   SmartSuite    │
└─────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Test MySQL Database (Docker)

```bash
# Start MySQL container with sample data
docker-compose up -d

# Check that it's running
docker-compose ps

# View logs
docker-compose logs -f
```

The test database includes:
- `customers` table with 5 sample records
- `orders` table with 7 sample records

### 3. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

Required environment variables:
- `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`
- `SMARTSUITE_TOKEN`, `SMARTSUITE_ACCOUNT_ID`
- `SYNC_INTERVAL_MINUTES` (optional, default: 5)
- `LOG_LEVEL` (optional, default: INFO)

### 4. Configure Sync Mappings

```bash
# Copy example config
cp config/sync_mappings.example.yml config/sync_mappings.yml

# Edit with your table IDs and field mappings
nano config/sync_mappings.yml
```

Key configuration sections:
- **Query**: SQL query to retrieve data (supports `:last_sync_time` parameter for incremental sync)
- **Primary Key**: Field to use for idempotency
- **Field Mappings**: Map MySQL columns to SmartSuite field slugs
- **Transformations**: Convert data types and values (numbers, dates, choice fields)

### 5. Validate Configuration

```bash
python main.py validate
```

### 6. Run Your First Sync

```bash
# Run once and exit
python main.py run

# Run specific sync only
python main.py run --sync-name customers_sync
```

## Usage

### Commands

#### Run Once
Execute all enabled syncs once and exit:
```bash
python main.py run
```

Run specific sync:
```bash
python main.py run --sync-name customers_sync
```

#### Scheduled Mode
Run syncs on a repeating schedule:
```bash
# Default interval (5 minutes)
python main.py schedule

# Custom interval
python main.py schedule --interval 10

# Run immediately then start scheduler
python main.py schedule --run-immediately
```

#### Validate Configuration
Check configuration file for errors:
```bash
python main.py validate
```

#### Show Status
View sync history and statistics:
```bash
python main.py status
```

### Logging

Logs are written to:
- **Console**: Real-time output
- **File**: `logs/sync.log`

Adjust log level:
```bash
python main.py --log-level DEBUG run
```

## Configuration Guide

### Sync Configuration Structure

```yaml
syncs:
  - name: "my_sync"
    enabled: true
    description: "Sync description"

    source:
      query: |
        SELECT * FROM my_table
        WHERE updated_at >= :last_sync_time OR :last_sync_time IS NULL
      primary_key: "id"
      updated_at_field: "updated_at"

    destination:
      table_id: "your_smartsuite_table_id"
      external_id_field: "external_id"

      field_mappings:
        mysql_column: "smartsuite_slug"
        name: "title"

      transformations:
        status:
          type: "choice"
          value_map:
            "active": "Active"
            "inactive": "Inactive"

        amount:
          type: "number"
          format: "float"

        date_field:
          type: "date"
          format: "%Y-%m-%d"
```

### Field Transformations

#### Number Transformation
```yaml
field_name:
  type: "number"
  format: "float"  # or "int"
```

#### Choice/Dropdown Transformation
```yaml
field_name:
  type: "choice"
  value_map:
    "db_value": "SmartSuite Display Value"
```

#### Date Transformation
```yaml
field_name:
  type: "date"
  format: "%Y-%m-%d"  # Python strftime format
```

## Idempotency & State Management

### How It Works

1. **First Sync**: Record is created in SmartSuite, mapping saved to SQLite
2. **Subsequent Syncs**:
   - Calculates hash of record data
   - Compares with stored hash
   - If unchanged: skips record
   - If changed: updates SmartSuite record
   - Updates hash in SQLite

### State Database Schema

**`sync_runs`**: Track each sync execution
- Timestamps, status, statistics

**`record_mappings`**: Map source IDs to SmartSuite record IDs
- Source ID, SmartSuite ID, data hash

**`sync_metadata`**: Track last successful sync time
- Used for incremental queries

### Querying State

```python
from state_manager import StateManager

state = StateManager()

# Get sync history
stats = state.get_sync_statistics('customers_sync')

# Get last sync time
last_sync = state.get_last_sync_time('customers_sync')

# Get record mapping
mapping = state.get_record_mapping('customers_sync', 'source_id_123')
```

## Scheduling Options

### Option 1: Built-in Scheduler (Recommended)

Use APScheduler for in-process scheduling:

```bash
# Run with default interval
python main.py schedule

# Custom interval
python main.py schedule --interval 15
```

**Pros**:
- Easy configuration
- Single process
- Built-in logging
- Immediate feedback

**Cons**:
- Process must stay running
- No distributed scheduling

### Option 2: Cron

Add to crontab for system-level scheduling:

```bash
# Run every 5 minutes
*/5 * * * * cd /path/to/sync && /path/to/python main.py run >> logs/cron.log 2>&1

# Run every hour
0 * * * * cd /path/to/sync && /path/to/python main.py run >> logs/cron.log 2>&1
```

**Pros**:
- System-level reliability
- Works across reboots
- Well-understood by ops teams

**Cons**:
- Requires cron access
- Less flexible configuration
- External to application

### Option 3: Systemd Timer (Linux)

Create systemd service and timer:

```ini
# /etc/systemd/system/mysql-smartsuite-sync.service
[Unit]
Description=MySQL to SmartSuite Sync

[Service]
Type=oneshot
WorkingDirectory=/path/to/sync
ExecStart=/path/to/python main.py run
User=syncuser
```

```ini
# /etc/systemd/system/mysql-smartsuite-sync.timer
[Unit]
Description=MySQL to SmartSuite Sync Timer

[Timer]
OnCalendar=*:0/5
Persistent=true

[Install]
WantedBy=timers.target
```

Enable:
```bash
systemctl enable mysql-smartsuite-sync.timer
systemctl start mysql-smartsuite-sync.timer
```

## Production Deployment

### Recommendations

1. **Use systemd or supervisord** to keep scheduler process running
2. **Set up log rotation** to prevent disk space issues
3. **Monitor state database size** and archive old records periodically
4. **Use connection pooling** for high-frequency syncs
5. **Set up alerting** on sync failures
6. **Backup SQLite state database** regularly

### Systemd Service Example

```ini
# /etc/systemd/system/mysql-smartsuite-sync.service
[Unit]
Description=MySQL to SmartSuite Sync Scheduler
After=network.target mysql.service

[Service]
Type=simple
WorkingDirectory=/opt/mysql-smartsuite-sync
ExecStart=/usr/bin/python3 main.py schedule --run-immediately
Restart=always
RestartSec=10
User=syncuser
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
systemctl enable mysql-smartsuite-sync
systemctl start mysql-smartsuite-sync
systemctl status mysql-smartsuite-sync
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py", "schedule", "--run-immediately"]
```

Build and run:
```bash
docker build -t mysql-smartsuite-sync .
docker run -d --name sync \
  --env-file .env \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/sync_state.db:/app/sync_state.db \
  mysql-smartsuite-sync
```

## Troubleshooting

### MySQL Connection Issues

```bash
# Test connection
python -c "from mysql_client import MySQLClient; import os; from dotenv import load_dotenv; load_dotenv(); c = MySQLClient(os.getenv('MYSQL_HOST'), int(os.getenv('MYSQL_PORT', 3306)), os.getenv('MYSQL_USER'), os.getenv('MYSQL_PASSWORD'), os.getenv('MYSQL_DATABASE')); print('Success!' if c.test_connection() else 'Failed')"
```

### SmartSuite API Issues

- Verify token and account ID
- Check table IDs are correct
- Ensure field slugs match exactly
- Review SmartSuite API rate limits

### State Database Corruption

```bash
# Backup current state
cp sync_state.db sync_state.db.backup

# Reset state (will cause full re-sync)
rm sync_state.db

# Run sync
python main.py run
```

### Viewing State Database

```bash
sqlite3 sync_state.db

# Useful queries
SELECT * FROM sync_runs ORDER BY started_at DESC LIMIT 10;
SELECT sync_name, COUNT(*) FROM record_mappings GROUP BY sync_name;
SELECT * FROM sync_metadata;
```

## Future Enhancements

### Bi-directional Sync (SmartSuite → MySQL)

The architecture supports reverse sync:

1. Add reverse sync configs in YAML
2. Query SmartSuite for updated records
3. Map SmartSuite fields to MySQL columns
4. Use state manager to track last sync time
5. Execute MySQL INSERT/UPDATE statements

### Webhook Support

Add webhook endpoint to trigger immediate syncs:

```python
from flask import Flask, request

app = Flask(__name__)

@app.route('/webhook/sync/<sync_name>', methods=['POST'])
def trigger_sync(sync_name):
    # Trigger immediate sync
    scheduler.run_now(sync_name)
    return {'status': 'triggered'}
```

## License

MIT License - See LICENSE file for details

## Support

For issues and questions:
1. Check logs in `logs/sync.log`
2. Run with `--log-level DEBUG`
3. Review SmartSuite API documentation
4. Check MySQL query syntax

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request
