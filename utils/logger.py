"""
utils/logger.py
----------------
Writes entries to the activity_logs table so admin actions
(logins, uploads, evaluations, etc.) are auditable.
"""

from models.db import run_query


def log_activity(admin_id, action, details=None):
    query = """
        INSERT INTO activity_logs (admin_id, action, details)
        VALUES (%s, %s, %s)
    """
    try:
        run_query(query, (admin_id, action, details), commit=True)
    except Exception:
        # Logging should never break the main request flow.
        pass
