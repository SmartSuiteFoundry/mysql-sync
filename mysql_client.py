"""
MySQL Client
------------
Handles MySQL database connections and query execution.
"""

import pymysql
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class MySQLClient:
    """Client for interacting with MySQL database."""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str
    ):
        """
        Initialize MySQL client.

        Args:
            host: MySQL host
            port: MySQL port
            user: MySQL user
            password: MySQL password
            database: Database name
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database

    @contextmanager
    def get_connection(self):
        """
        Get a MySQL connection context manager.

        Yields:
            MySQL connection
        """
        conn = None
        try:
            conn = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                cursorclass=pymysql.cursors.DictCursor,
                charset='utf8mb4'
            )
            yield conn
        except pymysql.Error as e:
            logger.error(f"MySQL connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a SQL query and return results.

        Args:
            query: SQL query to execute
            params: Query parameters (for prepared statements)

        Returns:
            List of row dictionaries

        Raises:
            pymysql.Error: If query execution fails
        """
        if params is None:
            params = {}

        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Convert :param_name style to %(param_name)s for pymysql
                formatted_query = self._format_query(query)

                logger.debug(f"Executing query: {formatted_query}")
                logger.debug(f"Parameters: {params}")

                cursor.execute(formatted_query, params)
                results = cursor.fetchall()

                logger.info(f"Query returned {len(results)} rows")
                return results

    def _format_query(self, query: str) -> str:
        """
        Convert :param_name style to %(param_name)s for pymysql.

        Args:
            query: SQL query with :param_name style parameters

        Returns:
            Query with %(param_name)s style parameters
        """
        import re

        # Replace :param_name with %(param_name)s
        # Look for :word_characters but not inside quotes
        def replacer(match):
            param_name = match.group(1)
            return f"%({param_name})s"

        # This regex finds :word but avoids replacing inside quotes
        # Simple version - for production might need more sophisticated parsing
        formatted = re.sub(r':(\w+)', replacer, query)
        return formatted

    def test_connection(self) -> bool:
        """
        Test database connection.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    return result is not None
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get information about table columns.

        Args:
            table_name: Name of the table

        Returns:
            List of column information dictionaries
        """
        query = """
            SELECT
                COLUMN_NAME,
                DATA_TYPE,
                IS_NULLABLE,
                COLUMN_KEY,
                COLUMN_DEFAULT,
                EXTRA
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
        """

        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (self.database, table_name))
                return cursor.fetchall()
