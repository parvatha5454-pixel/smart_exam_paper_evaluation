"""
routes/ocr_routes.py
-----------------------
Module 4: OCR Text Extraction Module
- Run OCR on a scanned answer sheet (whole page)
- Show the raw extracted text as a reference
- Let the admin split/paste/correct the text per question before
  evaluation (Module 5 will read from `corrected_text`)
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from models.scanned_sheet_model import get_scanned_sheet_by_id
from models.ocr_result_model import get_ocr_results_for_sheet, upsert_ocr_result
from OCR.ocr_utils import extract_text_with_confidence
from utils.security import login_required
from utils.logger import log_activity

ocr_bp = Blueprint("ocr", __name__, url_prefix="/ocr")


@ocr_bp.route("/<int:sheet_id>")
@login_required
def view_sheet_ocr(sheet_id):
    sheet = get_scanned_sheet_by_id(sheet_id)
    if not sheet:
        flash("Scanned sheet not found.", "danger")
        return redirect(url_for("scanning.list_sheets"))

    questions = get_ocr_results_for_sheet(sheet_id)

    # The full-page raw OCR text (if it was just run) is shown once
    # from the session so the admin can copy/paste from it below.
    raw_text = session.pop(f"raw_ocr_text_{sheet_id}", None)
    raw_confidence = session.pop(f"raw_ocr_confidence_{sheet_id}", None)

    return render_template(
        "ocr/view.html",
        sheet=sheet,
        questions=questions,
        raw_text=raw_text,
        raw_confidence=raw_confidence,
    )


@ocr_bp.route("/<int:sheet_id>/extract", methods=["POST"])
@login_required
def run_ocr(sheet_id):
    sheet = get_scanned_sheet_by_id(sheet_id)
    if not sheet:
        flash("Scanned sheet not found.", "danger")
        return redirect(url_for("scanning.list_sheets"))

    if not sheet.get("processed_image_path"):
        flash("This sheet has no processed image to run OCR on.", "danger")
        return redirect(url_for("ocr.view_sheet_ocr", sheet_id=sheet_id))

    try:
        text, confidence = extract_text_with_confidence(sheet["processed_image_path"])
    except Exception as e:
        flash(
            "Could not run OCR on this sheet. Make sure Tesseract OCR is "
            f"installed and configured in config.py. ({e})",
            "danger",
        )
        return redirect(url_for("ocr.view_sheet_ocr", sheet_id=sheet_id))

    if not text:
        flash("No readable text was found on this sheet.", "warning")
    else:
        session[f"raw_ocr_text_{sheet_id}"] = text
        session[f"raw_ocr_confidence_{sheet_id}"] = confidence
        flash(
            f"Text extracted (confidence: {confidence}%). Copy the relevant part into each "
            "question below, then save.",
            "success",
        )
        log_activity(session.get("admin_id"), "RUN_OCR", f"Ran OCR on sheet #{sheet_id}")

    return redirect(url_for("ocr.view_sheet_ocr", sheet_id=sheet_id))


@ocr_bp.route("/<int:sheet_id>/questions/<int:question_id>/save", methods=["POST"])
@login_required
def save_question_text(sheet_id, question_id):
    corrected_text = request.form.get("corrected_text", "").strip()
    extracted_text = request.form.get("extracted_text", "").strip() or None

    upsert_ocr_result(sheet_id, question_id, extracted_text, corrected_text)
    log_activity(
        session.get("admin_id"),
        "SAVE_OCR_TEXT",
        f"Saved answer text for question #{question_id} on sheet #{sheet_id}",
    )
    flash("Answer text saved.", "success")
    return redirect(url_for("ocr.view_sheet_ocr", sheet_id=sheet_id))
