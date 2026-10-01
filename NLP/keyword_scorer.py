"""
NLP/keyword_scorer.py
-----------------------
Very simple, deterministic scoring: for each question, count how many
of its answer-key keywords show up (case-insensitive substring match)
in the OCR'd text of the student's scanned answer sheet, and award
marks proportional to how many keywords were found.

This is intentionally simple (no semantic similarity, no ML model) -
it matches the "Question Number, Keywords, Marks" simplified answer
key format used elsewhere in this project. Admins can always
override the auto-awarded marks on the evaluation review screen.
"""

import re


def _normalize(text):
    """Lowercase and collapse whitespace for reliable substring matching."""
    return re.sub(r"\s+", " ", (text or "")).lower().strip()


def score_question(ocr_text, keywords_str, max_marks):
    """
    Returns a dict: {matched_count, total_keywords, marks_awarded, remarks}

    - No keywords defined for the question -> can't auto-grade; marks_awarded
      is left as 0 and the remarks flag it for manual review.
    - Otherwise: marks_awarded = (matched / total) * max_marks, rounded to
      the nearest 0.5 mark.
    """
    try:
        max_marks = float(max_marks or 0)
    except (TypeError, ValueError):
        max_marks = 0.0

    keywords = [k.strip() for k in (keywords_str or "").split(",") if k.strip()]

    if not keywords:
        return {
            "matched_count": 0,
            "total_keywords": 0,
            "marks_awarded": 0.0,
            "remarks": "No keywords set - needs manual review",
        }

    normalized_text = _normalize(ocr_text)
    matched = [kw for kw in keywords if _normalize(kw) in normalized_text]

    fraction = len(matched) / len(keywords)
    # Round to the nearest 0.5 so awarded marks look natural on a mark sheet.
    marks_awarded = round((fraction * max_marks) * 2) / 2

    remarks = f"{len(matched)}/{len(keywords)} keywords matched"

    return {
        "matched_count": len(matched),
        "total_keywords": len(keywords),
        "marks_awarded": marks_awarded,
        "remarks": remarks,
    }


def score_all_questions(ocr_text, questions):
    """
    questions: list of dicts with question_id, keywords, max_marks
    Returns a list of dicts, one per question, with the scoring result
    merged in (adds question_id, question_number to each result).
    """
    results = []
    for q in questions:
        result = score_question(ocr_text, q.get("keywords"), q.get("max_marks"))
        result["question_id"] = q["question_id"]
        result["question_number"] = q["question_number"]
        results.append(result)
    return results
