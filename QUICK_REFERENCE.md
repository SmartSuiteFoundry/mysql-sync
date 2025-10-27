# Quick Reference

## Common Commands

### One-Time Sync
```bash
# Run all syncs once
python main.py run

# Run specific sync
python main.py run --sync-name customers_sync

# Run with debug logging
python main.py --log-level DEBUG run
```

### Scheduled Sync
```bash
# Default 5-minute interval
python main.py schedule

# Custom interval (10 minutes)
python main.py schedule --interval 10

# Run immediately then start scheduler
python main.py schedule --run-immediately
```

### Configuration & Status
```bash
# Validate config
python main.py validate

# Show sync status and history
python main.py status

# Test connections
python test_connection.py
```

### Docker Commands
```bash
# Start MySQL test database
docker-compose up -d

# View MySQL logs
docker-compose logs -f mysql

# Stop MySQL
docker-compose down

# Connect to MySQL
docker-compose exec mysql mysql -u syncuser -psyncpassword testdb

# Reset everything to fresh start (MySQL + sync state)
make reset

# Or reset MySQL only (delete all data)
docker-compose down -v
docker-compose up -d
```

### State Database Queries
```bash
sqlite3 sync_state.db

# Recent sync runs
SELECT * FROM sync_runs ORDER BY started_at DESC LIMIT 10;

# Mapping counts by sync
SELECT sync_name, COUNT(*) as record_count
FROM record_mappings
GROUP BY sync_name;

# Last sync times
SELECT * FROM sync_metadata;

# Failed syncs
SELECT * FROM sync_runs WHERE status = 'failed';
```

## File Locations

| File | Purpose |
|------|---------|
| `.env` | Environment variables and secrets |
| `config/sync_mappings.yml` | Sync configuration |
| `sync_state.db` | SQLite state database |
| `logs/sync.log` | Application logs |

## Configuration Snippets

### Basic Field Mapping
```yaml
field_mappings:
  mysql_column: "smartsuite_slug"
  name: "title"
  email: "email_field"
```

### Number Transformation
```yaml
transformations:
  amount:
    type: "number"
    format: "float"  # or "int"
```

### Choice/Dropdown Mapping
```yaml
transformations:
  status:
    type: "choice"
    value_map:
      "active": "Active"
      "inactive": "Inactive"
```

### Date Formatting
```yaml
transformations:
  date_field:
    type: "date"
    format: "%Y-%m-%d"  # ISO format
```

### Incremental Query Pattern
```sql
SELECT *
FROM your_table
WHERE updated_at >= :last_sync_time OR :last_sync_time IS NULL
ORDER BY updated_at ASC
```

## Troubleshooting Quick Checks

### MySQL Connection
```bash
# Test from command line
python -c "from mysql_client import MySQLClient; from dotenv import load_dotenv; import os; load_dotenv(); c = MySQLClient(os.getenv('MYSQL_HOST'), int(os.getenv('MYSQL_PORT', 3306)), os.getenv('MYSQL_USER'), os.getenv('MYSQL_PASSWORD'), os.getenv('MYSQL_DATABASE')); print('OK' if c.test_connection() else 'FAIL')"
```

### Check Logs
```bash
# Tail logs
tail -f logs/sync.log

# Search for errors
grep ERROR logs/sync.log

# Search for specific sync
grep "customers_sync" logs/sync.log
```

### Reset State (Forces Full Re-sync)
```bash
# Backup first!
cp sync_state.db sync_state.db.backup

# Delete state
rm sync_state.db

# Next sync will be a full sync
python main.py run
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MYSQL_HOST` | Yes | - | MySQL host |
| `MYSQL_PORT` | No | 3306 | MySQL port |
| `MYSQL_USER` | Yes | - | MySQL user |
| `MYSQL_PASSWORD` | Yes | - | MySQL password |
| `MYSQL_DATABASE` | Yes | - | Database name |
| `SMARTSUITE_TOKEN` | Yes | - | API token |
| `SMARTSUITE_ACCOUNT_ID` | Yes | - | Account ID |
| `SYNC_INTERVAL_MINUTES` | No | 5 | Sync interval |
| `LOG_LEVEL` | No | INFO | Log level |
| `STATE_DB_PATH` | No | sync_state.db | State DB path |

## Sync Statistics Meaning

| Metric | Description |
|--------|-------------|
| **Processed** | Total records retrieved from MySQL |
| **Created** | New records created in SmartSuite |
| **Updated** | Existing records updated (data changed) |
| **Skipped** | Existing records skipped (no changes) |
| **Errors** | Records that failed to sync |

## Production Deployment

### Systemd (Linux)
```bash
# Copy service file
sudo cp deployment/mysql-smartsuite-sync.service /etc/systemd/system/

# Edit paths in service file
sudo nano /etc/systemd/system/mysql-smartsuite-sync.service

# Enable and start
sudo systemctl enable mysql-smartsuite-sync
sudo systemctl start mysql-smartsuite-sync

# Check status
sudo systemctl status mysql-smartsuite-sync

# View logs
sudo journalctl -u mysql-smartsuite-sync -f
```

### Docker
```bash
# Build
docker build -f deployment/Dockerfile -t mysql-smartsuite-sync .

# Run
docker run -d --name sync \
  --env-file .env \
  -v $(pwd)/config:/app/config:ro \
  -v $(pwd)/logs:/app/logs \
  -v sync_state:/app \
  mysql-smartsuite-sync

# Or use docker-compose
docker-compose -f deployment/docker-compose.prod.yml up -d

# View logs
docker logs -f sync
```

### Cron
```bash
# Edit crontab
crontab -e

# Add entry (every 5 minutes)
*/5 * * * * cd /path/to/sync && /path/to/python main.py run >> logs/cron.log 2>&1
```

## Performance Tips

1. **Use incremental sync**: Always include `updated_at >= :last_sync_time` in queries
2. **Index updated_at**: Create index on timestamp columns in MySQL
3. **Limit batch size**: For large tables, use pagination in queries
4. **Adjust interval**: Don't sync more often than necessary
5. **Monitor state DB**: Archive old records periodically

## Common Errors

### "No module named 'dotenv'"
```bash
pip install python-dotenv
```

### "Can't connect to MySQL server"
- Check MySQL is running: `docker-compose ps`
- Check host/port in `.env`
- Check firewall rules

### "SmartSuite 401 Unauthorized"
- Verify API token is correct
- Check token hasn't expired
- Ensure token has necessary permissions

### "Field 'xyz' not found"
- Check field slug matches exactly (case-sensitive)
- Verify field exists in SmartSuite table
- Review field mappings in config

### "Duplicate key error"
- State database may be corrupted
- Check `record_mappings` table for duplicates
- May need to reset state: `rm sync_state.db`

## Getting Help

1. Check logs: `tail -f logs/sync.log`
2. Enable debug logging: `python main.py --log-level DEBUG run`
3. Validate config: `python main.py validate`
4. Test connections: `python test_connection.py`
5. Check state: `sqlite3 sync_state.db`
6. Review documentation: `README.md` and `SETUP.md`
