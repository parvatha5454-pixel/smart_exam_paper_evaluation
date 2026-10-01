"""
models/evaluation_model.py
----------------------------
Data-access functions for the `evaluations` table.
One row per (scanned sheet, question) - the auto (or manually
corrected) marks awarded for that question on that student's sheet.
"""

from models.db import run_query


def get_evaluations_for_sheet(sheet_id):
    """All evaluation rows for a sheet, joined with question info."""
    query = """
        SELECT e.*, q.question_number, q.keywords, q.max_marks
        FROM evaluations e
        JOIN questions q ON e.question_id = q.question_id
        WHERE e.sheet_id = %s
        ORDER BY q.question_number
    """
    return run_query(query, (sheet_id,), fetch=True) or []


def get_evaluation_count(sheet_id):
    """Used by the list page to show an 'Evaluated' / 'Not evaluated' badge."""
    query = "SELECT COUNT(*) AS cnt FROM evaluations WHERE sheet_id = %s"
    row = run_query(query, (sheet_id,), fetch_one=True)
    return row["cnt"] if row else 0


def delete_evaluations_for_sheet(sheet_id):
    """Clears old results before a re-run, so re-evaluating doesn't duplicate rows."""
    query = "DELETE FROM evaluations WHERE sheet_id = %s"
    return run_query(query, (sheet_id,), commit=True)


def create_evaluation(sheet_id, question_id, keyword_score, marks_awarded, remarks):
    query = """
        INSERT INTO evaluations (sheet_id, question_id, keyword_score, marks_awarded, remarks)
        VALUES (%s, %s, %s, %s, %s)
    """
    return run_query(
        query, (sheet_id, question_id, keyword_score, marks_awarded, remarks), commit=True
    )


def update_marks_awarded(evaluation_id, marks_awarded, remarks):
    """Lets the admin manually correct an auto-awarded score."""
    query = "UPDATE evaluations SET marks_awarded = %s, remarks = %s WHERE evaluation_id = %s"
    return run_query(query, (marks_awarded, remarks, evaluation_id), commit=True)


def get_evaluation_by_id(evaluation_id):
    query = "SELECT * FROM evaluations WHERE evaluation_id = %s"
    return run_query(query, (evaluation_id,), fetch_one=True)
