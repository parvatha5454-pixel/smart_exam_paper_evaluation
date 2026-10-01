"""
routes/scanning_routes.py
----------------------------
Module 3: Answer Sheet Scanning Module
- Upload scanned/photographed answer sheets (JPG, PNG, JPEG, PDF)
- Preprocess images (grayscale, threshold, noise removal, deskew,
  resize, sharpening, contrast enhancement) via OpenCV
- Show original vs. processed image
- Manage students (add/update/delete/search) since every sheet
  belongs to a student.
"""

import os
import cv2
import numpy as np
from werkzeug.utils import secure_filename
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    send_from_directory,
)

from config import Config
from models.student_model import (
    get_all_students,
    get_student_by_id,
    get_student_by_roll_number,
    create_student,
    update_student,
    delete_student,
)
from models.answer_key_model import get_all_answer_keys, get_answer_key_by_id
from models.scanned_sheet_model import (
    get_all_scanned_sheets,
    get_scanned_sheet_by_id,
    create_scanned_sheet,
    delete_scanned_sheet,
)
from image_processing.preprocess import preprocess_image
from OCR.ocr_utils import extract_text_with_confidence
from utils.security import login_required
from utils.logger import log_activity

scanning_bp = Blueprint("scanning", __name__, url_prefix="/scanning")


def _merge_images_vertically(image_paths, output_path):
    """
    Stacks multiple page images (e.g. several photos of one student's
    answer script) into a single tall image, so multi-page uploads end
    up as ONE scanned sheet record instead of one row per page.
    Images are resized to a common width before stacking.
    """
    images = [cv2.imread(p, cv2.IMREAD_UNCHANGED) for p in image_paths]
    images = [img for img in images if img is not None]
    if not images:
        raise ValueError("No valid pages to merge.")

    target_width = min(img.shape[1] for img in images)
    resized = []
    for img in images:
        h, w = img.shape[:2]
        new_h = int(h * (target_width / w))
        resized.append(cv2.resize(img, (target_width, new_h), interpolation=cv2.INTER_AREA))

    # Pad with a thin white separator line between pages.
    separator_height = 12
    parts = []
    for i, img in enumerate(resized):
        if i > 0:
            if img.ndim == 3:
                sep = 255 * np.ones((separator_height, target_width, img.shape[2]), dtype=img.dtype)
            else:
                sep = 255 * np.ones((separator_height, target_width), dtype=img.dtype)
            parts.append(sep)
        parts.append(img)

    combined = cv2.vconcat(parts) if len(set(p.ndim for p in parts)) == 1 else cv2.vconcat(
        [p if p.ndim == 3 else cv2.cvtColor(p, cv2.COLOR_GRAY2BGR) for p in parts]
    )
    cv2.imwrite(output_path, combined)
    return output_path


# ---------------------------------------------------------------
# Scanned sheets: list / filter
# ---------------------------------------------------------------

@scanning_bp.route("/")
@login_required
def list_sheets():
    answer_key_id = request.args.get("answer_key_id", "").strip() or None
    student_search = request.args.get("search", "").strip() or None

    sheets = get_all_scanned_sheets(answer_key_id=answer_key_id, student_search=student_search)
    answer_keys = get_all_answer_keys()

    return render_template(
        "scanning/list.html",
        sheets=sheets,
        answer_keys=answer_keys,
        selected_answer_key_id=answer_key_id or "",
        search=student_search or "",
    )


# ---------------------------------------------------------------
# Scanned sheets: upload + preprocess
# ---------------------------------------------------------------

@scanning_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload_sheet():
    students = get_all_students()
    answer_keys = get_all_answer_keys()

    if request.method == "POST":
        student_id = request.form.get("student_id")
        answer_key_id = request.form.get("answer_key_id")
        files = [f for f in request.files.getlist("sheet_images") if f and f.filename]

        if not student_id or not answer_key_id:
            flash("Please select both a student and an answer key.", "danger")
            return render_template("scanning/upload.html", students=students, answer_keys=answer_keys)

        if not files:
            flash("Please choose at least one answer sheet file to upload.", "danger")
            return render_template("scanning/upload.html", students=students, answer_keys=answer_keys)

        os.makedirs(Config.SCANNED_ANSWERS_FOLDER, exist_ok=True)

        original_paths = []
        processed_paths = []
        failed_files = []

        for index, file in enumerate(files, start=1):
            ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
            if ext not in Config.ALLOWED_IMAGE_EXTENSIONS:
                failed_files.append(f"{file.filename} (unsupported type)")
                continue

            filename = secure_filename(file.filename)
            original_filename = f"sheet_{student_id}_{answer_key_id}_{index}_{filename}"
            original_path = os.path.join(Config.SCANNED_ANSWERS_FOLDER, original_filename)
            file.save(original_path)

            # PDFs are converted to an image (first page) before preprocessing.
            image_source_path = original_path
            if ext == "pdf":
                try:
                    from pdf2image import convert_from_path

                    pages = convert_from_path(original_path, dpi=200)
                    image_source_path = original_path.rsplit(".", 1)[0] + "_page1.png"
                    pages[0].save(image_source_path, "PNG")
                except Exception as e:
                    failed_files.append(f"{file.filename} (PDF conversion failed: {e})")
                    continue

            processed_filename = (
                "processed_" + os.path.basename(image_source_path).rsplit(".", 1)[0] + ".png"
            )
            processed_path = os.path.join(Config.SCANNED_ANSWERS_FOLDER, processed_filename)

            try:
                preprocess_image(image_source_path, processed_path)
            except Exception as e:
                failed_files.append(f"{file.filename} (preprocessing failed: {e})")
                continue

            original_paths.append(image_source_path)
            processed_paths.append(processed_path)

        if not original_paths:
            if failed_files:
                flash("None of the files could be processed: " + "; ".join(failed_files), "danger")
            return render_template("scanning/upload.html", students=students, answer_keys=answer_keys)

        # Multiple pages -> merge them into ONE combined image, so the
        # whole answer script becomes a single scanned_sheets record
        # instead of one row per page.
        if len(original_paths) > 1:
            combined_tag = f"sheet_{student_id}_{answer_key_id}_{os.urandom(4).hex()}"
            final_original_path = os.path.join(
                Config.SCANNED_ANSWERS_FOLDER, f"{combined_tag}_original_combined.png"
            )
            final_processed_path = os.path.join(
                Config.SCANNED_ANSWERS_FOLDER, f"{combined_tag}_processed_combined.png"
            )
            _merge_images_vertically(original_paths, final_original_path)
            _merge_images_vertically(processed_paths, final_processed_path)
        else:
            final_original_path = original_paths[0]
            final_processed_path = processed_paths[0]

        # Quality gate: check EasyOCR's own confidence in what it can
        # read from the photo. Reject uploads that are too
        # blurry/dark/skewed to OCR reliably, instead of silently
        # accepting garbage that would later score 0 on everything.
        # Uses the ORIGINAL (not the black/white "processed") image -
        # EasyOCR's deep-learning model reads natural photos better
        # than a harshly binarized one.
        try:
          _, confidence, word_count = extract_text_with_confidence(final_processed_path)
        except Exception as e:
            print(f"!!! OCR CONFIDENCE CHECK FAILED: {e}")
            confidence, word_count = 0.0, 0

        if confidence < Config.MIN_OCR_CONFIDENCE or word_count < Config.MIN_OCR_WORD_COUNT:
            flash(
                f"This photo is too unclear for OCR to read reliably "
                f"(confidence {confidence:.0f}%, {word_count} word(s) detected). "
                f"Please retake the photo with better lighting, a straighter angle, and "
                f"make sure it's in focus, then upload again.",
                "danger",
            )
            return render_template("scanning/upload.html", students=students, answer_keys=answer_keys)

        new_id = create_scanned_sheet(
            student_id, answer_key_id, final_original_path, final_processed_path
        )

        log_activity(
            session.get("admin_id"),
            "UPLOAD_SCANNED_SHEET",
            f"Uploaded and preprocessed answer sheet #{new_id} "
            f"({len(original_paths)} page(s)) for student #{student_id}, exam #{answer_key_id}",
        )
        flash(
            f"Answer sheet uploaded and preprocessed ({len(original_paths)} page(s) combined).",
            "success",
        )
        if failed_files:
            flash("Some files could not be processed: " + "; ".join(failed_files), "warning")

        return redirect(url_for("scanning.preview_sheet", sheet_id=new_id))

    return render_template("scanning/upload.html", students=students, answer_keys=answer_keys)


# ---------------------------------------------------------------
# Scanned sheets: preview (original vs. processed)
# ---------------------------------------------------------------

@scanning_bp.route("/<int:sheet_id>")
@login_required
def preview_sheet(sheet_id):
    sheet = get_scanned_sheet_by_id(sheet_id)
    if not sheet:
        flash("Scanned sheet not found.", "danger")
        return redirect(url_for("scanning.list_sheets"))
    return render_template("scanning/preview.html", sheet=sheet)


# ---------------------------------------------------------------
# Serve scanned sheet images (they live outside /static)
# ---------------------------------------------------------------

@scanning_bp.route("/file/<path:filename>")
@login_required
def serve_scanned_file(filename):
    return send_from_directory(Config.SCANNED_ANSWERS_FOLDER, filename)


# ---------------------------------------------------------------
# Scanned sheets: delete
# ---------------------------------------------------------------

@scanning_bp.route("/<int:sheet_id>/delete", methods=["POST"])
@login_required
def delete_sheet(sheet_id):
    sheet = get_scanned_sheet_by_id(sheet_id)
    if sheet:
        delete_scanned_sheet(sheet_id)
        log_activity(session.get("admin_id"), "DELETE_SCANNED_SHEET", f"Deleted sheet #{sheet_id}")
        flash("Scanned sheet deleted.", "info")
    return redirect(url_for("scanning.list_sheets"))


# ---------------------------------------------------------------
# Students: list / add / edit / delete
# ---------------------------------------------------------------

@scanning_bp.route("/students")
@login_required
def list_students():
    search = request.args.get("search", "").strip() or None
    students = get_all_students(search=search)
    return render_template("scanning/students.html", students=students, search=search or "")


@scanning_bp.route("/students/add", methods=["POST"])
@login_required
def add_student():
    roll_number = request.form.get("roll_number", "").strip()
    full_name = request.form.get("full_name", "").strip()
    department = request.form.get("department", "").strip()
    semester = request.form.get("semester", "").strip()
    email = request.form.get("email", "").strip()

    if not roll_number or not full_name:
        flash("Roll number and name are required.", "danger")
        return redirect(url_for("scanning.list_students"))

    if get_student_by_roll_number(roll_number):
        flash(f"Roll number '{roll_number}' already exists.", "danger")
        return redirect(url_for("scanning.list_students"))

    create_student(roll_number, full_name, department, semester, email)
    flash("Student added.", "success")
    return redirect(url_for("scanning.list_students"))


@scanning_bp.route("/students/<int:student_id>/edit", methods=["POST"])
@login_required
def edit_student(student_id):
    roll_number = request.form.get("roll_number", "").strip()
    full_name = request.form.get("full_name", "").strip()
    department = request.form.get("department", "").strip()
    semester = request.form.get("semester", "").strip()
    email = request.form.get("email", "").strip()

    if not roll_number or not full_name:
        flash("Roll number and name are required.", "danger")
        return redirect(url_for("scanning.list_students"))

    update_student(student_id, roll_number, full_name, department, semester, email)
    flash("Student updated.", "success")
    return redirect(url_for("scanning.list_students"))


@scanning_bp.route("/students/<int:student_id>/delete", methods=["POST"])
@login_required
def delete_student_route(student_id):
    delete_student(student_id)
    flash("Student deleted.", "info")
    return redirect(url_for("scanning.list_students"))
