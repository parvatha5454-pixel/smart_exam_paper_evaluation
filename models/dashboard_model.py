"""
models/dashboard_model.py
--------------------------
Aggregate queries powering the admin dashboard cards.
"""

from models.db import run_query


def get_dashboard_stats():
    """Returns a dict of summary numbers for the dashboard cards.

    Uses table-existence-safe queries so the dashboard still loads
    cleanly even before later modules (answer keys, evaluations,
    etc.) have any data in them.
    """
    stats = {
        "total_students": 0,
        "total_answer_keys": 0,
        "total_evaluated_papers": 0,
        "average_marks": 0,
    }

    try:
        row = run_query("SELECT COUNT(*) AS total FROM students", fetch_one=True)
        stats["total_students"] = row["total"] if row else 0
    except Exception:
        pass

    try:
        row = run_query("SELECT COUNT(*) AS total FROM answer_keys", fetch_one=True)
        stats["total_answer_keys"] = row["total"] if row else 0
    except Exception:
        pass

    try:
        row = run_query(
            "SELECT COUNT(DISTINCT sheet_id) AS total FROM evaluations", fetch_one=True
        )
        stats["total_evaluated_papers"] = row["total"] if row else 0
    except Exception:
        pass

    try:
        row = run_query(
            """
            SELECT AVG(sheet_total) AS avg_marks FROM (
                SELECT sheet_id, SUM(marks_awarded) AS sheet_total
                FROM evaluations
                GROUP BY sheet_id
            ) AS totals
            """,
            fetch_one=True,
        )
        avg = row["avg_marks"] if row else None
        stats["average_marks"] = round(float(avg), 2) if avg is not None else 0
    except Exception:
        pass

    return stats


def get_recent_evaluations(limit=5):
    """Returns the most recently evaluated sheets with student + subject info."""
    query = """
        SELECT
            s.full_name AS student_name,
            s.roll_number AS roll_number,
            sub.subject_name AS subject_name,
            ak.exam_name AS exam_name,
            SUM(e.marks_awarded) AS total_marks,
            MAX(e.evaluated_at) AS evaluated_at
        FROM evaluations e
        JOIN scanned_sheets ss ON e.sheet_id = ss.sheet_id
        JOIN students s ON ss.student_id = s.student_id
        JOIN answer_keys ak ON ss.answer_key_id = ak.answer_key_id
        JOIN subjects sub ON ak.subject_id = sub.subject_id
        GROUP BY ss.sheet_id, s.full_name, s.roll_number, sub.subject_name, ak.exam_name
        ORDER BY evaluated_at DESC
        LIMIT %s
    """
    try:
        return run_query(query, (limit,), fetch=True) or []
    except Exception:
        return []
