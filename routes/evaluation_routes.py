"""
routes/evaluation_routes.py
------------------------------
Module 5: Evaluation
- Pick a scanned answer sheet, run OCR on it, and auto-score every
  question in its answer key by keyword matching (NLP/keyword_scorer.py).
- Admin can review the auto-awarded marks and manually correct any of
  them before finalizing.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from models.scanned_sheet_model import (
    get_all_scanned_sheets,
    get_scanned_sheet_by_id,
)
from models.answer_key_model import get_questions_for_answer_key
from models.evaluation_model import (
    get_evaluations_for_sheet,
    get_evaluation_count,
    delete_evaluations_for_sheet,
    create_evaluation,
    update_marks_awarded,
)
from OCR.ocr_utils import extract_text
from NLP.keyword_scorer import score_all_questions
from utils.security import login_required
from utils.logger import log_activity

evaluation_bp = Blueprint("evaluation", __name__, url_prefix="/evaluation")


# ---------------------------------------------------------------
# Evaluation: list scanned sheets, with evaluated/not-evaluated status
# ---------------------------------------------------------------

@evaluation_bp.route("/")
@login_required
def list_sheets_for_evaluation():
    search = request.args.get("search", "")
    sheets = get_all_scanned_sheets(student_search=search or None)

    for s in sheets:
        s["is_evaluated"] = get_evaluation_count(s["sheet_id"]) > 0

    return render_template("evaluation/list.html", sheets=sheets, search=search)


# ---------------------------------------------------------------
# Evaluation: view a sheet's results (or the "run evaluation" prompt
# if it hasn't been evaluated yet)
# ---------------------------------------------------------------

@evaluation_bp.route("/<int:sheet_id>")
@login_required
def view_evaluation(sheet_id):
    sheet = get_scanned_sheet_by_id(sheet_id)
    if not sheet:
        flash("Scanned sheet not found.", "danger")
        return redirect(url_for("evaluation.list_sheets_for_evaluation"))

    results = get_evaluations_for_sheet(sheet_id)
    total_awarded = sum(float(r["marks_awarded"] or 0) for r in results)
    total_max = sum(float(r["max_marks"] or 0) for r in results)

    return render_template(
        "evaluation/result.html",
        sheet=sheet,
        results=results,
        total_awarded=total_awarded,
        total_max=total_max,
    )


@evaluation_bp.route("/<int:sheet_id>/ocr-preview")
@login_required
def ocr_preview(sheet_id):
    """
    Debug helper: shows exactly what OCR read from the scanned sheet,
    without saving anything. Useful for checking why keyword matches
    are low - handwritten sheets are much harder for Tesseract to
    read accurately than typed/printed text.
    """
    sheet = get_scanned_sheet_by_id(sheet_id)
    if not sheet:
        flash("Scanned sheet not found.", "danger")
        return redirect(url_for("evaluation.list_sheets_for_evaluation"))

    image_path = sheet.get("processed_image_path") or sheet.get("original_image_path")

    try:
        ocr_text = extract_text(image_path)
    except Exception as e:
        ocr_text = f"[OCR failed: {e}]"

    return render_template("evaluation/ocr_preview.html", sheet=sheet, ocr_text=ocr_text)


# ---------------------------------------------------------------
# Evaluation: run (or re-run) auto-evaluation for a sheet
# ---------------------------------------------------------------

@evaluation_bp.route("/<int:sheet_id>/run", methods=["POST"])
@login_required
def run_evaluation(sheet_id):
    sheet = get_scanned_sheet_by_id(sheet_id)
    if not sheet:
        flash("Scanned sheet not found.", "danger")
        return redirect(url_for("evaluation.list_sheets_for_evaluation"))

    image_path = sheet.get("processed_image_path") or sheet.get("original_image_path")

    try:
        ocr_text = extract_text(image_path)
    except Exception as e:
        flash(
            "Could not read text from the scanned sheet. Make sure Tesseract OCR "
            f"is installed and configured in config.py. ({e})",
            "danger",
        )
        return redirect(url_for("evaluation.view_evaluation", sheet_id=sheet_id))

    if not ocr_text or not ocr_text.strip():
        flash(
            "OCR could not read any text from this sheet (often happens with messy "
            "handwriting). All scores will be 0 - use the raw OCR text box below to "
            "check what was read, and correct marks manually.",
            "warning",
        )

    questions = get_questions_for_answer_key(sheet["answer_key_id"])
    if not questions:
        flash("This exam's answer key has no questions to evaluate against yet.", "warning")
        return redirect(url_for("evaluation.view_evaluation", sheet_id=sheet_id))

    scored = score_all_questions(ocr_text, questions)

    # Clear any previous run so re-evaluating doesn't create duplicate rows.
    delete_evaluations_for_sheet(sheet_id)
    for r in scored:
        create_evaluation(
            sheet_id,
            r["question_id"],
            r["matched_count"],  # keyword_score = number of keywords matched
            r["marks_awarded"],
            r["remarks"],
        )

    log_activity(
        session.get("admin_id"),
        "RUN_EVALUATION",
        f"Ran auto-evaluation for scanned sheet #{sheet_id} ({len(scored)} question(s))",
    )
    flash("Evaluation complete. Review the marks below and correct anything that looks off.", "success")
    return redirect(url_for("evaluation.view_evaluation", sheet_id=sheet_id))


# ---------------------------------------------------------------
# Evaluation: manually correct one question's awarded marks
# ---------------------------------------------------------------

@evaluation_bp.route("/results/<int:evaluation_id>/update", methods=["POST"])
@login_required
def update_evaluation(evaluation_id):
    sheet_id = request.form.get("sheet_id")
    marks_awarded = request.form.get("marks_awarded", "0").strip()
    remarks = request.form.get("remarks", "").strip()

    try:
        marks_val = float(marks_awarded)
    except ValueError:
        flash("Marks must be a number.", "danger")
        return redirect(url_for("evaluation.view_evaluation", sheet_id=sheet_id))

    update_marks_awarded(evaluation_id, marks_val, remarks or "Manually corrected")
    flash("Marks updated.", "success")
    return redirect(url_for("evaluation.view_evaluation", sheet_id=sheet_id))
