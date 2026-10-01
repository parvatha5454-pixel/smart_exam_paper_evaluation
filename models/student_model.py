"""
models/student_model.py
-------------------------
Data-access functions for the `students` table.
"""

from models.db import run_query


def get_all_students(search=None):
    query = "SELECT * FROM students WHERE 1=1"
    params = []
    if search:
        query += " AND (full_name LIKE %s OR roll_number LIKE %s)"
        like = f"%{search}%"
        params += [like, like]
    query += " ORDER BY full_name ASC"
    return run_query(query, tuple(params), fetch=True) or []


def get_student_by_id(student_id):
    query = "SELECT * FROM students WHERE student_id = %s"
    return run_query(query, (student_id,), fetch_one=True)


def get_student_by_roll_number(roll_number):
    query = "SELECT * FROM students WHERE roll_number = %s"
    return run_query(query, (roll_number,), fetch_one=True)


def create_student(roll_number, full_name, department, semester, email):
    query = """
        INSERT INTO students (roll_number, full_name, department, semester, email)
        VALUES (%s, %s, %s, %s, %s)
    """
    return run_query(
        query, (roll_number, full_name, department, semester, email), commit=True
    )


def update_student(student_id, roll_number, full_name, department, semester, email):
    query = """
        UPDATE students
        SET roll_number = %s, full_name = %s, department = %s, semester = %s, email = %s
        WHERE student_id = %s
    """
    return run_query(
        query,
        (roll_number, full_name, department, semester, email, student_id),
        commit=True,
    )


def delete_student(student_id):
    query = "DELETE FROM students WHERE student_id = %s"
    return run_query(query, (student_id,), commit=True)
