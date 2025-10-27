# Get Started in 5 Minutes

This is your fastest path to getting the MySQL to SmartSuite sync running.

## Prerequisites Checklist

- [ ] Python 3.8+ installed
- [ ] Docker installed (for test database)
- [ ] SmartSuite API token and account ID
- [ ] 5 minutes of time

## Step 1: Install (1 minute)

```bash
# Install dependencies
make install

# Or manually:
pip install -r requirements.txt
cp .env.example .env
cp config/sync_mappings.example.yml config/sync_mappings.yml
```

## Step 2: Start Test Database (1 minute)

```bash
# Start MySQL with sample data
make docker-up

# Or manually:
docker-compose up -d
```

This creates a MySQL database with:
- 5 sample customers
- 7 sample orders

## Step 3: Configure (2 minutes)

### Edit `.env`

```bash
# Only change these two lines:
SMARTSUITE_TOKEN=your_actual_token_here
SMARTSUITE_ACCOUNT_ID=your_actual_account_id_here

# Everything else is already configured for test database
```

### Edit `config/sync_mappings.yml`

```yaml
# Find this line (appears twice, once for customers, once for orders):
table_id: "REPLACE_WITH_YOUR_TABLE_ID"

# Replace with your SmartSuite table ID
table_id: "abc123xyz"  # Your actual table ID
```

**How to get table ID**: Open your table in SmartSuite, look at the URL:
```
https://app.smartsuite.com/.../{TABLE_ID_HERE}/...
```

## Step 4: Test (30 seconds)

```bash
# Test all connections
make test

# You should see:
# ✓ MySQL connection successful
# ✓ Found 5 customers in database
# ✓ SmartSuite client initialized
# ✓ State manager initialized
```

## Step 5: First Sync (30 seconds)

```bash
# Run your first sync!
make run

# Watch it sync records from MySQL to SmartSuite
```

Check SmartSuite - your records should be there!

## What Just Happened?

1. ✅ Queried MySQL for customer and order data
2. ✅ Mapped MySQL fields to SmartSuite fields
3. ✅ Created records in SmartSuite
4. ✅ Saved mappings to local SQLite database

## Try It Again

```bash
# Run sync again
make run

# This time all records will be SKIPPED
# (because nothing changed - that's idempotency!)
```

## Make a Change

```bash
# Update a customer in MySQL
make mysql-shell

# In MySQL shell:
UPDATE customers SET company = 'New Company Name' WHERE id = 1;
exit

# Run sync again
make run

# You should see:
# - 1 record UPDATED (the one you changed)
# - Other records SKIPPED (unchanged)
```

## Start Over (Reset Everything)

Want to test from scratch? Use the reset command:

```bash
# Reset MySQL and sync state to fresh start
make reset

# This will:
# - Backup your current state
# - Delete sync state database
# - Clear logs
# - Reset MySQL to original sample data
# - Let you test the first sync again!
```

## Next Steps

### Run on a Schedule

```bash
# Run every 5 minutes (Ctrl+C to stop)
make schedule
```

### View Status

```bash
# See sync history
make status

# View logs
make logs
```

### Configure Your Real Database

Edit `.env` and change MySQL settings:

```bash
MYSQL_HOST=your.database.host
MYSQL_USER=your_user
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=your_database
```

Edit `config/sync_mappings.yml`:
- Update SQL queries
- Map your actual fields
- Add field transformations

### Deploy to Production

See [README.md](README.md) for:
- SystemD service setup
- Docker deployment
- Cron scheduling
- Production best practices

## Useful Commands

```bash
make help              # Show all commands
make validate          # Check configuration
make status            # Show sync history
make logs              # View recent logs
make reset             # Reset to fresh start (MySQL + state)
make docker-down       # Stop test database
make backup            # Backup state database
make clean             # Clean up files
```

## Common Issues

### "Can't connect to MySQL"
```bash
# Check if MySQL is running
docker-compose ps

# Restart if needed
make docker-down
make docker-up
```

### "SmartSuite 401 Unauthorized"
- Check your API token in `.env`
- Make sure it's not expired
- Verify token has correct permissions

### "Table not found"
- Check `table_id` in `config/sync_mappings.yml`
- Make sure table exists in SmartSuite
- Verify you have access to the table

### "Field not found"
- Check field slugs match exactly (case-sensitive!)
- Go to table settings in SmartSuite
- Copy the exact field slug

## Need More Help?

- **Full Documentation**: [README.md](README.md)
- **Setup Guide**: [SETUP.md](SETUP.md)
- **Command Reference**: [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
- **Architecture**: [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)

## Quick Reference

| What | Command |
|------|---------|
| Install | `make install` |
| Start MySQL | `make docker-up` |
| Test | `make test` |
| Run once | `make run` |
| Schedule | `make schedule` |
| Status | `make status` |
| Logs | `make logs` |
| Help | `make help` |

---

**You're all set!** 🎉

Your MySQL data is now syncing to SmartSuite with full idempotency and state tracking.

Edit `config/sync_mappings.yml` to customize your sync, and use `make schedule` to run continuously.
