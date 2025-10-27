# Makefile for MySQL to SmartSuite Sync

.PHONY: help install test validate run schedule status clean docker-up docker-down reset

help:
	@echo "MySQL to SmartSuite Sync - Available Commands"
	@echo "=============================================="
	@echo ""
	@echo "Setup:"
	@echo "  make install       Install Python dependencies"
	@echo "  make docker-up     Start MySQL test database"
	@echo "  make docker-down   Stop MySQL test database"
	@echo "  make reset         Reset MySQL DB and sync state to fresh start"
	@echo ""
	@echo "Development:"
	@echo "  make test          Test database connections"
	@echo "  make validate      Validate configuration"
	@echo "  make run           Run sync once"
	@echo "  make schedule      Run scheduler (Ctrl+C to stop)"
	@echo "  make status        Show sync status and history"
	@echo ""
	@echo "Maintenance:"
	@echo "  make logs          View recent logs"
	@echo "  make clean         Clean generated files"
	@echo "  make backup        Backup state database"
	@echo ""

install:
	pip install -r requirements.txt
	@echo "✓ Dependencies installed"
	@[ -f .env ] || (cp .env.example .env && echo "⚠ Created .env - please configure it!")
	@[ -f config/sync_mappings.yml ] || (cp config/sync_mappings.example.yml config/sync_mappings.yml && echo "⚠ Created config/sync_mappings.yml - please configure it!")

docker-up:
	docker-compose up -d
	@echo "⏳ Waiting for MySQL to be ready..."
	@sleep 5
	@docker-compose exec mysql mysqladmin ping -h localhost --silent || echo "⚠ MySQL may need more time to start"
	@echo "✓ MySQL is running"

docker-down:
	docker-compose down

reset:
	@echo "🔄 Resetting to fresh state..."
	@echo ""
	@echo "This will:"
	@echo "  1. Reset MySQL database to original sample data"
	@echo "  2. Delete sync state (all mappings and history)"
	@echo "  3. Clear logs"
	@echo ""
	@read -p "Continue? [y/N] " confirm && [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ] || (echo "Cancelled" && exit 1)
	@echo ""
	@echo "📦 Backing up current state..."
	@mkdir -p backups
	@[ -f sync_state.db ] && cp sync_state.db backups/sync_state_backup_$$(date +%Y%m%d_%H%M%S).db && echo "  ✓ State backed up" || echo "  ℹ No state to backup"
	@echo ""
	@echo "🗑️  Removing sync state..."
	@rm -f sync_state.db sync_state.db-journal
	@echo "  ✓ Sync state deleted"
	@echo ""
	@echo "🗑️  Clearing logs..."
	@rm -f logs/sync.log
	@echo "  ✓ Logs cleared"
	@echo ""
	@echo "🔄 Resetting MySQL database..."
	@docker-compose down -v
	@docker-compose up -d
	@echo "  ⏳ Waiting for MySQL to initialize..."
	@sleep 8
	@docker-compose exec mysql mysqladmin ping -h localhost --silent && echo "  ✓ MySQL ready" || echo "  ⚠ MySQL may need more time"
	@echo ""
	@echo "✅ Reset complete! Database has original sample data."
	@echo ""
	@echo "Verify with:"
	@echo "  make mysql-customers  # Should show 5 customers"
	@echo "  make run              # Will create new records in SmartSuite"
	@echo ""

test:
	python test_connection.py

validate:
	python main.py validate

run:
	python main.py run

schedule:
	python main.py schedule --run-immediately

status:
	python main.py status

logs:
	@[ -f logs/sync.log ] && tail -n 50 logs/sync.log || echo "No logs found"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name "*~" -delete 2>/dev/null || true
	@echo "✓ Cleaned up generated files"

backup:
	@mkdir -p backups
	@[ -f sync_state.db ] && cp sync_state.db backups/sync_state_$$(date +%Y%m%d_%H%M%S).db && echo "✓ State database backed up" || echo "⚠ No state database to backup"

# Development helpers
dev-run:
	python main.py --log-level DEBUG run

dev-schedule:
	python main.py --log-level DEBUG schedule --run-immediately

# Database helpers
db-shell:
	sqlite3 sync_state.db

db-stats:
	@sqlite3 sync_state.db "SELECT sync_name, COUNT(*) as records FROM record_mappings GROUP BY sync_name;"

db-recent:
	@sqlite3 sync_state.db "SELECT sync_name, started_at, status, records_processed FROM sync_runs ORDER BY started_at DESC LIMIT 10;"

# MySQL helpers
mysql-shell:
	docker-compose exec mysql mysql -u syncuser -psyncpassword testdb

mysql-customers:
	docker-compose exec mysql mysql -u syncuser -psyncpassword testdb -e "SELECT * FROM customers;"

mysql-orders:
	docker-compose exec mysql mysql -u syncuser -psyncpassword testdb -e "SELECT * FROM orders;"
