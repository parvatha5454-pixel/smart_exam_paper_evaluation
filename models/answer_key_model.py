"""
models/answer_key_model.py
----------------------------
Module 2: Answer Key Upload
Data-access functions for the `answer_keys` and `questions` tables.
"""

from models.db import run_query


# ---------------------------------------------------------------
# Answer Keys
# ---------------------------------------------------------------

def get_all_answer_keys(search=None, department=None, semester=None):
    """Returns answer keys joined with subject info, with optional filters."""
    query = """
        SELECT ak.*, s.subject_name, s.subject_code,
               (SELECT COUNT(*) FROM questions q WHERE q.answer_key_id = ak.answer_key_id) AS question_count,
               (SELECT COALESCE(SUM(max_marks), 0) FROM questions q WHERE q.answer_key_id = ak.answer_key_id) AS total_marks
        FROM answer_keys ak
        JOIN subjects s ON ak.subject_id = s.subject_id
        WHERE 1=1
    """
    params = []

    if search:
        query += " AND (ak.exam_name LIKE %s OR s.subject_name LIKE %s OR s.subject_code LIKE %s)"
        like = f"%{search}%"
        params += [like, like, like]

    if department:
        query += " AND ak.department = %s"
        params.append(department)

    if semester:
        query += " AND ak.semester = %s"
        params.append(semester)

    query += " ORDER BY ak.created_at DESC"

    return run_query(query, tuple(params), fetch=True) or []


def get_answer_key_by_id(answer_key_id):
    query = """
        SELECT ak.*, s.subject_name, s.subject_code
        FROM answer_keys ak
        JOIN subjects s ON ak.subject_id = s.subject_id
        WHERE ak.answer_key_id = %s
    """
    return run_query(query, (answer_key_id,), fetch_one=True)


def create_answer_key(subject_id, exam_name, department, semester, created_by):
    query = """
        INSERT INTO answer_keys (subject_id, exam_name, department, semester, created_by)
        VALUES (%s, %s, %s, %s, %s)
    """
    return run_query(
        query, (subject_id, exam_name, department, semester, created_by), commit=True
    )


def update_answer_key(answer_key_id, subject_id, exam_name, department, semester):
    query = """
        UPDATE answer_keys
        SET subject_id = %s, exam_name = %s, department = %s, semester = %s
        WHERE answer_key_id = %s
    """
    return run_query(
        query,
        (subject_id, exam_name, department, semester, answer_key_id),
        commit=True,
    )


def update_question_paper_path(answer_key_id, question_paper_path):
    """
    Stores the path to the uploaded question-paper file (a plain
    upload + view feature, independent of the answer-key/OCR flow).
    """
    query = "UPDATE answer_keys SET question_paper_path = %s WHERE answer_key_id = %s"
    return run_query(query, (question_paper_path, answer_key_id), commit=True)


def delete_answer_key(answer_key_id):
    # ON DELETE CASCADE in the schema removes its questions automatically.
    query = "DELETE FROM answer_keys WHERE answer_key_id = %s"
    return run_query(query, (answer_key_id,), commit=True)


# ---------------------------------------------------------------
# Questions
# ---------------------------------------------------------------

def get_questions_for_answer_key(answer_key_id):
    query = """
        SELECT * FROM questions
        WHERE answer_key_id = %s
        ORDER BY question_number ASC
    """
    return run_query(query, (answer_key_id,), fetch=True) or []


def get_question_by_id(question_id):
    query = "SELECT * FROM questions WHERE question_id = %s"
    return run_query(query, (question_id,), fetch_one=True)


def create_question(answer_key_id, question_number, expected_answer, keywords, max_marks):
    query = """
        INSERT INTO questions (answer_key_id, question_number, expected_answer, keywords, max_marks)
        VALUES (%s, %s, %s, %s, %s)
    """
    return run_query(
        query,
        (answer_key_id, question_number, expected_answer, keywords, max_marks),
        commit=True,
    )


def update_question(question_id, question_number, expected_answer, keywords, max_marks):
    query = """
        UPDATE questions
        SET question_number = %s, expected_answer = %s, keywords = %s, max_marks = %s
        WHERE question_id = %s
    """
    return run_query(
        query,
        (question_number, expected_answer, keywords, max_marks, question_id),
        commit=True,
    )


def delete_question(question_id):
    query = "DELETE FROM questions WHERE question_id = %s"
    return run_query(query, (question_id,), commit=True)


def create_questions_bulk(answer_key_id, questions):
    """
    Insert several questions at once (used by the OCR/image-upload flow,
    where one uploaded answer-key file produces many parsed questions).

    `questions` is a list of dicts with keys:
        question_number, expected_answer, keywords, max_marks
    Returns the number of questions inserted.
    """
    inserted = 0
    for q in questions:
        question_number = (q.get("question_number") or "").strip()
        expected_answer = (q.get("expected_answer") or "").strip()
        keywords = (q.get("keywords") or "").strip()
        try:
            max_marks = float(q.get("max_marks") or 0)
        except (TypeError, ValueError):
            max_marks = 0.0

        if not question_number:
            continue

        create_question(answer_key_id, question_number, expected_answer, keywords, max_marks)
        inserted += 1

    return inserted
