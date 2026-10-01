"""
models/db.py
------------
Thin wrapper around mysql-connector-python that gives the rest of
the app a simple way to run queries without repeating boilerplate.
"""

import mysql.connector
from mysql.connector import pooling
from config import Config

_pool = None


def init_pool():
    """Create a connection pool once, at app startup."""
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="exam_analysis_pool",
            pool_size=5,
            host=Config.MYSQL_HOST,
            port=Config.MYSQL_PORT,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB,
        )
    return _pool


def get_connection():
    """Get a connection from the pool (creates the pool on first call)."""
    pool = init_pool()
    return pool.get_connection()


def run_query(query, params=None, fetch=False, fetch_one=False, commit=False):
    """
    Execute a single query and manage the connection/cursor lifecycle.

    Args:
        query: SQL string with %s placeholders.
        params: tuple/list of parameters for the placeholders.
        fetch: if True, return all matching rows.
        fetch_one: if True, return a single row (or None).
        commit: if True, commit the transaction (for INSERT/UPDATE/DELETE).

    Returns:
        - list of dict rows if fetch=True
        - single dict row (or None) if fetch_one=True
        - lastrowid (int) if commit=True and nothing fetched
        - True on plain success otherwise
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params or ())

        if fetch:
            result = cursor.fetchall()
            return result
        if fetch_one:
            result = cursor.fetchone()
            return result
        if commit:
            conn.commit()
            return cursor.lastrowid
        return True
    finally:
        cursor.close()
        conn.close()
