"""
models/scanned_sheet_model.py
--------------------------------
Data-access functions for the `scanned_sheets` table.
"""

from models.db import run_query


def get_all_scanned_sheets(answer_key_id=None, student_search=None):
    query = """
        SELECT ss.*, st.full_name AS student_name, st.roll_number,
               ak.exam_name, sub.subject_name
        FROM scanned_sheets ss
        JOIN students st ON ss.student_id = st.student_id
        JOIN answer_keys ak ON ss.answer_key_id = ak.answer_key_id
        JOIN subjects sub ON ak.subject_id = sub.subject_id
        WHERE 1=1
    """
    params = []
    if answer_key_id:
        query += " AND ss.answer_key_id = %s"
        params.append(answer_key_id)
    if student_search:
        query += " AND (st.full_name LIKE %s OR st.roll_number LIKE %s)"
        like = f"%{student_search}%"
        params += [like, like]
    query += " ORDER BY ss.uploaded_at DESC"
    return run_query(query, tuple(params), fetch=True) or []


def get_scanned_sheet_by_id(sheet_id):
    query = """
        SELECT ss.*, st.full_name AS student_name, st.roll_number,
               ak.exam_name, sub.subject_name
        FROM scanned_sheets ss
        JOIN students st ON ss.student_id = st.student_id
        JOIN answer_keys ak ON ss.answer_key_id = ak.answer_key_id
        JOIN subjects sub ON ak.subject_id = sub.subject_id
        WHERE ss.sheet_id = %s
    """
    return run_query(query, (sheet_id,), fetch_one=True)


def create_scanned_sheet(student_id, answer_key_id, original_image_path, processed_image_path):
    query = """
        INSERT INTO scanned_sheets (student_id, answer_key_id, original_image_path, processed_image_path)
        VALUES (%s, %s, %s, %s)
    """
    return run_query(
        query,
        (student_id, answer_key_id, original_image_path, processed_image_path),
        commit=True,
    )


def delete_scanned_sheet(sheet_id):
    query = "DELETE FROM scanned_sheets WHERE sheet_id = %s"
    return run_query(query, (sheet_id,), commit=True)
