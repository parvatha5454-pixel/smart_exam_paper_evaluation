"""
models/report_model.py
-------------------------
Data-access functions for the `reports` table - just an audit trail
of generated PDF/Excel report files (when, for which sheet, what the
final score was). The actual file generation lives in
routes/report_routes.py.
"""

from models.db import run_query


def create_report(sheet_id, report_type, file_path, total_marks, percentage):
    query = """
        INSERT INTO reports (sheet_id, report_type, file_path, total_marks, percentage)
        VALUES (%s, %s, %s, %s, %s)
    """
    return run_query(
        query, (sheet_id, report_type, file_path, total_marks, percentage), commit=True
    )


def get_reports_for_sheet(sheet_id):
    query = "SELECT * FROM reports WHERE sheet_id = %s ORDER BY generated_at DESC"
    return run_query(query, (sheet_id,), fetch=True) or []
