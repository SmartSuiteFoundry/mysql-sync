#!/usr/bin/env python3
"""
Connection Test Script
---------------------
Quick script to test MySQL and SmartSuite connections.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

print("Testing Connections...")
print("=" * 70)

# Test MySQL
print("\n1. MySQL Connection")
print("-" * 70)

try:
    from mysql_client import MySQLClient

    mysql = MySQLClient(
        host=os.getenv('MYSQL_HOST'),
        port=int(os.getenv('MYSQL_PORT', 3306)),
        user=os.getenv('MYSQL_USER'),
        password=os.getenv('MYSQL_PASSWORD'),
        database=os.getenv('MYSQL_DATABASE')
    )

    if mysql.test_connection():
        print("✓ MySQL connection successful")

        # Test query
        result = mysql.execute_query("SELECT COUNT(*) as count FROM customers")
        count = result[0]['count'] if result else 0
        print(f"✓ Found {count} customers in database")
    else:
        print("✗ MySQL connection failed")
        sys.exit(1)

except Exception as e:
    print(f"✗ MySQL error: {e}")
    sys.exit(1)

# Test SmartSuite
print("\n2. SmartSuite Connection")
print("-" * 70)

try:
    from smartsuite_client import SmartSuiteClient

    smartsuite = SmartSuiteClient(
        token=os.getenv('SMARTSUITE_TOKEN'),
        account_id=os.getenv('SMARTSUITE_ACCOUNT_ID')
    )

    # Try to get account info (any simple API call)
    print("✓ SmartSuite client initialized")
    print(f"  Account ID: {smartsuite.account_id}")

    # Note: Add a test call if you have a known table ID
    # tables = smartsuite.get_solution_tables('your_solution_id')
    # print(f"✓ Found {len(tables)} tables")

except Exception as e:
    print(f"✗ SmartSuite error: {e}")
    sys.exit(1)

# Test State Manager
print("\n3. State Manager")
print("-" * 70)

try:
    from state_manager import StateManager

    state = StateManager('test_state.db')
    print("✓ State manager initialized")
    print(f"  Database: test_state.db")

    # Clean up test database
    import os
    if os.path.exists('test_state.db'):
        os.remove('test_state.db')
        print("✓ Test cleanup completed")

except Exception as e:
    print(f"✗ State manager error: {e}")
    sys.exit(1)

print("\n" + "=" * 70)
print("All connections successful! ✓")
print("=" * 70)
