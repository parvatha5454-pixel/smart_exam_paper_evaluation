"""
models/ocr_result_model.py
-----------------------------
Module 4: OCR Text Extraction Module
Data-access functions for the `ocr_results` table.

Each row holds the OCR'd (and admin-corrected) text for ONE question
on ONE scanned sheet, so a student's answers can be matched up
question-by-question before evaluation.
"""

from models.db import run_query


def get_ocr_results_for_sheet(sheet_id):
    """
    Returns every question belonging to the sheet's answer key,
    left-joined with any existing OCR result for that question —
    so questions with no OCR text yet still show up (with NULLs).
    """
    query = """
        SELECT
            q.question_id,
            q.question_number,
            q.expected_answer,
            q.max_marks,
            o.ocr_id,
            o.extracted_text,
            o.corrected_text,
            o.ocr_confidence
        FROM scanned_sheets ss
        JOIN questions q ON q.answer_key_id = ss.answer_key_id
        LEFT JOIN ocr_results o ON o.sheet_id = ss.sheet_id AND o.question_id = q.question_id
        WHERE ss.sheet_id = %s
        ORDER BY q.question_number ASC
    """
    return run_query(query, (sheet_id,), fetch=True) or []


def get_ocr_result(sheet_id, question_id):
    query = "SELECT * FROM ocr_results WHERE sheet_id = %s AND question_id = %s"
    return run_query(query, (sheet_id, question_id), fetch_one=True)


def upsert_ocr_result(sheet_id, question_id, extracted_text, corrected_text, ocr_confidence=None):
    """Creates the OCR result row for this sheet+question, or updates it if it already exists."""
    existing = get_ocr_result(sheet_id, question_id)
    if existing:
        query = """
            UPDATE ocr_results
            SET extracted_text = %s, corrected_text = %s, ocr_confidence = %s
            WHERE ocr_id = %s
        """
        return run_query(
            query,
            (extracted_text, corrected_text, ocr_confidence, existing["ocr_id"]),
            commit=True,
        )
    else:
        query = """
            INSERT INTO ocr_results (sheet_id, question_id, extracted_text, corrected_text, ocr_confidence)
            VALUES (%s, %s, %s, %s, %s)
        """
        return run_query(
            query,
            (sheet_id, question_id, extracted_text, corrected_text, ocr_confidence),
            commit=True,
        )
