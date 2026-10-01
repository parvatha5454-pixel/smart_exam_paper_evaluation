"""
models/subject_model.py
------------------------
Data-access functions for the `subjects` table.
"""

from models.db import run_query


def get_all_subjects():
    query = "SELECT * FROM subjects ORDER BY subject_name ASC"
    return run_query(query, fetch=True) or []


def get_subject_by_id(subject_id):
    query = "SELECT * FROM subjects WHERE subject_id = %s"
    return run_query(query, (subject_id,), fetch_one=True)


def get_subject_by_code(subject_code):
    query = "SELECT * FROM subjects WHERE subject_code = %s"
    return run_query(query, (subject_code,), fetch_one=True)


def create_subject(subject_code, subject_name, department, semester):
    query = """
        INSERT INTO subjects (subject_code, subject_name, department, semester)
        VALUES (%s, %s, %s, %s)
    """
    return run_query(
        query, (subject_code, subject_name, department, semester), commit=True
    )


def update_subject(subject_id, subject_code, subject_name, department, semester):
    query = """
        UPDATE subjects
        SET subject_code = %s, subject_name = %s, department = %s, semester = %s
        WHERE subject_id = %s
    """
    return run_query(
        query,
        (subject_code, subject_name, department, semester, subject_id),
        commit=True,
    )


def delete_subject(subject_id):
    query = "DELETE FROM subjects WHERE subject_id = %s"
    return run_query(query, (subject_id,), commit=True)
