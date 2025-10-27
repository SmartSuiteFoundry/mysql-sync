# Database Reset Information

## What `make reset` Does

The `make reset` command completely resets your development environment to a fresh state, perfect for testing the sync from scratch.

### Process Flow

```
┌─────────────────────────────────────────┐
│  make reset                             │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  1. Confirmation Prompt                 │
│     "Continue? [y/N]"                   │
└────────────┬────────────────────────────┘
             │ (if yes)
             ▼
┌─────────────────────────────────────────┐
│  2. Backup Current State                │
│     sync_state.db →                     │
│     backups/sync_state_backup_DATE.db   │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  3. Delete Sync State                   │
│     - Remove sync_state.db              │
│     - Remove sync_state.db-journal      │
│     - All mappings deleted              │
│     - All history deleted               │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  4. Clear Logs                          │
│     - Remove logs/sync.log              │
│     - Fresh log file on next run        │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  5. Reset MySQL Database                │
│     - docker-compose down -v            │
│     - Delete all volumes (data)         │
│     - docker-compose up -d              │
│     - Reinitialize with sample data     │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  ✅ Fresh Environment Ready             │
│     - 5 original customers              │
│     - 7 original orders                 │
│     - No sync history                   │
│     - No record mappings                │
└─────────────────────────────────────────┘
```

## Before Reset

```
MySQL Database:
  customers: 5 records (possibly modified)
  orders: 7 records (possibly modified)

SQLite State Database:
  record_mappings: N records
  sync_runs: M sync history entries
  sync_metadata: Last sync times

Logs:
  logs/sync.log: Previous sync logs

SmartSuite:
  Records created from previous syncs (UNCHANGED)
```

## After Reset

```
MySQL Database:
  customers: 5 ORIGINAL records
    - John Smith (Acme Corp)
    - Jane Doe (Tech Solutions Inc)
    - Bob Johnson (Global Industries)
    - Alice Williams (Innovation Labs)
    - Charlie Brown (Enterprise Systems)

  orders: 7 ORIGINAL records
    - Various orders from 2024

SQLite State Database:
  record_mappings: 0 records (EMPTY)
  sync_runs: 0 history entries (EMPTY)
  sync_metadata: No last sync times (EMPTY)

Logs:
  logs/sync.log: DELETED (will be recreated)

SmartSuite:
  Previous records STILL EXIST
  (They are NOT deleted by reset)
```

## Use Cases

### 1. Testing First Sync
You want to test the initial sync behavior:
```bash
make reset
make run
# All records will be CREATED (not updated)
```

### 2. Testing After Breaking Changes
You changed field mappings and want to start fresh:
```bash
make reset
# Edit config/sync_mappings.yml
make run
```

### 3. Testing Idempotency
Verify that unchanged records are skipped:
```bash
make reset
make run          # Creates all records
make run          # Should skip all (unchanged)
```

### 4. Demo/Presentation
Show someone how the sync works from the beginning:
```bash
make reset
# Demo the sync process with fresh data
```

## Important Notes

### ⚠️ SmartSuite Records NOT Deleted

The `make reset` command does **NOT** delete records in SmartSuite. It only:
- Resets the local MySQL database
- Clears local sync state

This means:
- If you run sync after reset, it will create NEW records in SmartSuite
- You'll have duplicates unless you manually delete the old SmartSuite records first
- Or disable the sync you already ran

### ✅ State Backup Created

Before deleting anything, `make reset` backs up your current state to:
```
backups/sync_state_backup_YYYYMMDD_HHMMSS.db
```

You can restore this if needed:
```bash
cp backups/sync_state_backup_20250126_143022.db sync_state.db
```

### 🔄 MySQL Volume Deleted

The command uses `docker-compose down -v` which deletes the MySQL data volume. This means:
- All data changes are lost
- Database is recreated from `test_data/01_init.sql`
- Any custom test data you added will be deleted

## Manual Reset Steps

If you prefer to reset components individually:

### Reset Sync State Only
```bash
# Backup first
cp sync_state.db backups/sync_state_manual_backup.db

# Delete state
rm sync_state.db sync_state.db-journal

# Next sync will create new mappings
```

### Reset MySQL Only
```bash
# Keep sync state, just reset MySQL
docker-compose down -v
docker-compose up -d
```

### Reset Logs Only
```bash
rm logs/sync.log
```

### Clear SmartSuite Records (Manual)

If you want to truly start fresh, you must manually:
1. Go to SmartSuite
2. Delete records created by previous syncs
3. Or disable the sync configuration
4. Then run `make reset`

## Recovery

### Restore State from Backup
```bash
# List backups
ls -lh backups/

# Restore specific backup
cp backups/sync_state_backup_20250126_143022.db sync_state.db

# Verify
make status
```

### Restore MySQL from Custom Backup
If you created custom test data:
```sql
-- Export before reset
docker-compose exec mysql mysqldump -u syncuser -psyncpassword testdb > my_backup.sql

-- After reset, restore
docker-compose exec -T mysql mysql -u syncuser -psyncpassword testdb < my_backup.sql
```

## Testing Workflow

Recommended workflow for development/testing:

```bash
# 1. Initial setup
make install
make docker-up

# 2. Configure
# Edit .env and config/sync_mappings.yml

# 3. First test
make test
make run

# 4. Make changes and test
# Modify config or code
make reset
make run

# 5. Test idempotency
make run          # Creates records
make run          # Skips all (unchanged)

# 6. Test updates
make mysql-shell
UPDATE customers SET company = 'Test' WHERE id = 1;
exit
make run          # Updates 1 record

# 7. Reset and repeat
make reset
# Start testing again
```

## Comparison Table

| Command | MySQL | State DB | Logs | SmartSuite |
|---------|-------|----------|------|------------|
| `make reset` | ✅ Reset | ✅ Delete | ✅ Clear | ❌ No change |
| `make clean` | ❌ No change | ❌ No change | ❌ No change | ❌ No change |
| `make backup` | ❌ No change | 📦 Backup only | ❌ No change | ❌ No change |
| `docker-compose down -v` | ✅ Reset | ❌ No change | ❌ No change | ❌ No change |
| `rm sync_state.db` | ❌ No change | ✅ Delete | ❌ No change | ❌ No change |

## Quick Reference

```bash
# Full reset with confirmation
make reset

# Skip confirmation (use with caution!)
yes | make reset

# Reset then immediately sync
make reset && make run

# Reset and view what's in MySQL
make reset && make mysql-customers

# Reset and run with debug logging
make reset && make dev-run
```

## FAQ

**Q: Will this delete my SmartSuite records?**
A: No, `make reset` only resets local MySQL and sync state. SmartSuite records remain unchanged.

**Q: Can I undo a reset?**
A: The state database is automatically backed up before reset. MySQL data is permanently deleted (unless you made your own backup).

**Q: What if I run sync after reset?**
A: It will create NEW records in SmartSuite (potential duplicates). The sync has "forgotten" about previous records.

**Q: How do I truly start fresh with SmartSuite?**
A: Manually delete SmartSuite records first, then run `make reset`.

**Q: Is it safe to use in production?**
A: **NO!** This command is for development/testing only. Never use on production databases.

**Q: Can I reset just one sync?**
A: Not with `make reset`. You'd need to manually delete specific records from `sync_state.db`.

**Q: Does it affect my actual database?**
A: Only if you configured `.env` to point to your actual database (not recommended for testing).
