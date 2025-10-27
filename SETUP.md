# Setup Guide

Step-by-step guide to get the MySQL to SmartSuite sync running.

## Prerequisites

- Python 3.8 or higher
- Docker and Docker Compose (for test database)
- SmartSuite account with API access

## Step 1: Install Python Dependencies

```bash
pip install -r requirements.txt
```

Or use a virtual environment (recommended):

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Step 2: Start Test MySQL Database

```bash
# Start MySQL container
docker-compose up -d

# Wait for MySQL to be ready (check logs)
docker-compose logs -f mysql

# You should see: "ready for connections"
```

The test database includes:
- Database: `testdb`
- User: `syncuser` / Password: `syncpassword`
- Tables: `customers`, `orders`
- Sample data pre-loaded

To connect to the database:
```bash
docker-compose exec mysql mysql -u syncuser -psyncpassword testdb
```

## Step 3: Configure Environment Variables

```bash
# Copy the example
cp .env.example .env
```

Edit `.env` with your credentials:

```bash
# MySQL (already configured for test database)
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=syncuser
MYSQL_PASSWORD=syncpassword
MYSQL_DATABASE=testdb

# SmartSuite (REPLACE WITH YOUR VALUES)
SMARTSUITE_TOKEN=your_actual_token_here
SMARTSUITE_ACCOUNT_ID=your_actual_account_id_here

# Sync Configuration
SYNC_INTERVAL_MINUTES=5
LOG_LEVEL=INFO
```

### Getting SmartSuite Credentials

1. **API Token**:
   - Log into SmartSuite
   - Go to Settings → API Keys
   - Create a new API key
   - Copy the token

2. **Account ID**:
   - In SmartSuite, look at your URL
   - Format: `https://app.smartsuite.com/account/{ACCOUNT_ID}/...`
   - Copy the account ID from the URL

## Step 4: Set Up SmartSuite Tables

You need to create tables in SmartSuite to receive the synced data.

### For Customers Sync

Create a table with these fields:

| Field Label    | Field Type | Field Slug (use this in config) |
|----------------|------------|----------------------------------|
| Customer Name  | Title      | title                            |
| Customer ID    | Number     | customer_id                      |
| Email Address  | Email      | email_address                    |
| Phone Number   | Phone      | phone_number                     |
| Company Name   | Text       | company_name                     |
| Customer Status| Single Select | customer_status               |
| Credit Limit   | Number     | credit_limit                     |
| Created Date   | Date       | created_date                     |
| Last Updated   | Date       | last_updated                     |

For the "Customer Status" field, add these choices:
- Active
- Inactive
- Pending

### For Orders Sync

Create a table with these fields:

| Field Label    | Field Type | Field Slug (use this in config) |
|----------------|------------|----------------------------------|
| Order Number   | Title      | title                            |
| Order ID       | Number     | order_id                         |
| Customer       | Text       | customer                         |
| Order Date     | Date       | order_date                       |
| Total          | Number     | total                            |
| Order Status   | Single Select | order_status                  |
| Notes          | Long Text  | notes                            |
| Created Date   | Date       | created_date                     |
| Last Updated   | Date       | last_updated                     |

For the "Order Status" field, add these choices:
- Pending
- Processing
- Shipped
- Delivered
- Cancelled

**Important**: Copy the Table IDs from SmartSuite (visible in the URL when viewing a table).

## Step 5: Configure Sync Mappings

```bash
# Copy the example config
cp config/sync_mappings.example.yml config/sync_mappings.yml
```

Edit `config/sync_mappings.yml`:

```yaml
syncs:
  - name: "customers_sync"
    enabled: true
    description: "Sync customer data from MySQL to SmartSuite"

    source:
      query: |
        SELECT
          id,
          customer_name,
          email,
          phone,
          company,
          status,
          credit_limit,
          created_at,
          updated_at
        FROM customers
        WHERE updated_at >= :last_sync_time OR :last_sync_time IS NULL
        ORDER BY updated_at ASC

      primary_key: "id"
      updated_at_field: "updated_at"

    destination:
      table_id: "REPLACE_WITH_YOUR_TABLE_ID"  # ← Change this!

      field_mappings:
        id: "customer_id"
        customer_name: "title"
        email: "email_address"
        phone: "phone_number"
        company: "company_name"
        status: "customer_status"
        credit_limit: "credit_limit"
        created_at: "created_date"
        updated_at: "last_updated"

      external_id_field: "customer_id"

      transformations:
        credit_limit:
          type: "number"
          format: "float"
        status:
          type: "choice"
          value_map:
            "active": "Active"
            "inactive": "Inactive"
            "pending": "Pending"
```

Repeat for the orders sync configuration.

## Step 6: Test Connections

```bash
python test_connection.py
```

This will verify:
- MySQL connection works
- SmartSuite client is configured
- State manager can initialize

## Step 7: Validate Configuration

```bash
python main.py validate
```

This checks:
- YAML syntax is correct
- All required fields are present
- Configuration is well-formed

## Step 8: Run First Sync

```bash
# Run with debug logging to see what's happening
python main.py --log-level DEBUG run
```

Watch for:
- Records retrieved from MySQL
- Records created in SmartSuite
- State saved to SQLite

Check SmartSuite to verify records were created!

## Step 9: Test Update Detection

Update a record in MySQL:

```sql
docker-compose exec mysql mysql -u syncuser -psyncpassword testdb

UPDATE customers
SET company = 'Updated Company Name'
WHERE id = 1;
```

Run sync again:

```bash
python main.py run
```

You should see:
- 1 record processed
- 1 record updated (not created)
- Other records skipped (unchanged)

## Step 10: Start Scheduled Sync

```bash
# Run with default 5-minute interval
python main.py schedule --run-immediately
```

The scheduler will:
- Run sync immediately
- Then run every 5 minutes
- Keep running until you stop it (Ctrl+C)

## Verification Checklist

- [ ] Python dependencies installed
- [ ] Docker MySQL running
- [ ] `.env` file configured with real credentials
- [ ] SmartSuite tables created with correct fields
- [ ] `config/sync_mappings.yml` updated with table IDs
- [ ] Connection test passed
- [ ] Configuration validation passed
- [ ] First sync completed successfully
- [ ] Records visible in SmartSuite
- [ ] Update detection works correctly
- [ ] Scheduler runs successfully

## Troubleshooting

### "Failed to connect to MySQL"

- Check MySQL container is running: `docker-compose ps`
- Check MySQL logs: `docker-compose logs mysql`
- Verify credentials in `.env`

### "SmartSuite 401 Unauthorized"

- Verify `SMARTSUITE_TOKEN` is correct
- Check token hasn't expired
- Ensure token has necessary permissions

### "SmartSuite 404 Not Found"

- Verify `table_id` in config is correct
- Check table exists and you have access

### "Field not found" errors

- Check field slugs match exactly (case-sensitive)
- Verify field types are compatible
- Review field mappings in config

### Records not syncing

- Check logs: `logs/sync.log`
- Verify query returns data: `docker-compose exec mysql mysql -u syncuser -psyncpassword testdb -e "SELECT * FROM customers LIMIT 5"`
- Check state database: `sqlite3 sync_state.db "SELECT * FROM sync_runs"`

## Next Steps

Once the test sync is working:

1. **Configure your production database**: Update `.env` with real MySQL credentials
2. **Create production sync configs**: Add your actual tables and queries
3. **Set up proper scheduling**: Use systemd or cron for production
4. **Configure log rotation**: Prevent log files from growing too large
5. **Set up monitoring**: Track sync failures and alert on errors
6. **Backup state database**: Regular backups of `sync_state.db`

See [README.md](README.md) for production deployment guidance.
