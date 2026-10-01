"""
models/admin_model.py
----------------------
Data-access functions for the `admin` table.
"""

from models.db import run_query


def get_admin_by_username(username):
    query = "SELECT * FROM admin WHERE username = %s AND is_active = TRUE"
    return run_query(query, (username,), fetch_one=True)


def get_admin_by_id(admin_id):
    query = "SELECT * FROM admin WHERE admin_id = %s"
    return run_query(query, (admin_id,), fetch_one=True)


def create_admin(username, email, password_hash, full_name):
    query = """
        INSERT INTO admin (username, email, password_hash, full_name)
        VALUES (%s, %s, %s, %s)
    """
    return run_query(query, (username, email, password_hash, full_name), commit=True)


def update_last_login(admin_id):
    query = "UPDATE admin SET last_login = NOW() WHERE admin_id = %s"
    return run_query(query, (admin_id,), commit=True)


def update_password(admin_id, new_password_hash):
    query = "UPDATE admin SET password_hash = %s WHERE admin_id = %s"
    return run_query(query, (new_password_hash, admin_id), commit=True)


def count_admins():
    query = "SELECT COUNT(*) AS total FROM admin"
    row = run_query(query, fetch_one=True)
    return row["total"] if row else 0
