"""
routes/answer_key_routes.py
------------------------------
Module 2: Answer Key Upload Module
- Add / Update / Delete / Search / Preview answer keys
- Each answer key holds subject/exam metadata plus a list of
  questions (expected answer, keywords, max marks).
- Subjects can also be managed here (add/update/delete).
- Questions can also be filled in by uploading a photo of the
  answer key; text is extracted automatically via OCR.
"""

import os
import uuid
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
from models.subject_model import (
    get_all_subjects,
    get_subject_by_id,
    get_subject_by_code,
    create_subject,
    update_subject,
    delete_subject,
)
from models.answer_key_model import (
    get_all_answer_keys,
    get_answer_key_by_id,
    create_answer_key,
    update_answer_key,
    update_question_paper_path,
    delete_answer_key,
    get_questions_for_answer_key,
    get_question_by_id,
    create_question,
    create_questions_bulk,
    update_question,
    delete_question,
)
from utils.security import login_required
from utils.logger import log_activity
from OCR.ocr_utils import extract_text
from NLP.question_parser import parse_questions_from_text

answer_key_bp = Blueprint("answer_key", __name__, url_prefix="/answer-keys")


# ---------------------------------------------------------------
# Answer Keys: list / search / filter
# ---------------------------------------------------------------

@answer_key_bp.route("/")
@login_required
def list_answer_keys():
    search = request.args.get("search", "").strip() or None
    department = request.args.get("department", "").strip() or None
    semester = request.args.get("semester", "").strip() or None

    keys = get_all_answer_keys(search=search, department=department, semester=semester)
    subjects = get_all_subjects()

    return render_template(
        "answer_keys/list.html",
        keys=keys,
        subjects=subjects,
        search=search or "",
        department=department or "",
        semester=semester or "",
    )


# ---------------------------------------------------------------
# Answer Keys: add
# ---------------------------------------------------------------

@answer_key_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_answer_key():
    subjects = get_all_subjects()

    if request.method == "POST":
        subject_id = request.form.get("subject_id")
        exam_name = request.form.get("exam_name", "").strip()
        department = request.form.get("department", "").strip()
        semester = request.form.get("semester", "").strip()

        if not subject_id or not exam_name:
            flash("Subject and exam name are required.", "danger")
            return render_template("answer_keys/form.html", subjects=subjects, key=None)

        new_id = create_answer_key(
            subject_id, exam_name, department, semester, session.get("admin_id")
        )
        log_activity(
            session.get("admin_id"), "CREATE_ANSWER_KEY", f"Created answer key '{exam_name}'"
        )
        flash("Answer key created. Now add its questions below.", "success")
        return redirect(url_for("answer_key.preview_answer_key", answer_key_id=new_id))

    return render_template("answer_keys/form.html", subjects=subjects, key=None)


# ---------------------------------------------------------------
# Answer Keys: edit
# ---------------------------------------------------------------

@answer_key_bp.route("/<int:answer_key_id>/edit", methods=["GET", "POST"])
@login_required
def edit_answer_key(answer_key_id):
    key = get_answer_key_by_id(answer_key_id)
    if not key:
        flash("Answer key not found.", "danger")
        return redirect(url_for("answer_key.list_answer_keys"))

    subjects = get_all_subjects()

    if request.method == "POST":
        subject_id = request.form.get("subject_id")
        exam_name = request.form.get("exam_name", "").strip()
        department = request.form.get("department", "").strip()
        semester = request.form.get("semester", "").strip()

        if not subject_id or not exam_name:
            flash("Subject and exam name are required.", "danger")
            return render_template("answer_keys/form.html", subjects=subjects, key=key)

        update_answer_key(answer_key_id, subject_id, exam_name, department, semester)
        log_activity(
            session.get("admin_id"), "UPDATE_ANSWER_KEY", f"Updated answer key #{answer_key_id}"
        )
        flash("Answer key updated.", "success")
        return redirect(url_for("answer_key.list_answer_keys"))

    return render_template("answer_keys/form.html", subjects=subjects, key=key)


# ---------------------------------------------------------------
# Answer Keys: delete
# ---------------------------------------------------------------

@answer_key_bp.route("/<int:answer_key_id>/delete", methods=["POST"])
@login_required
def delete_answer_key_route(answer_key_id):
    key = get_answer_key_by_id(answer_key_id)
    if key:
        delete_answer_key(answer_key_id)
        log_activity(
            session.get("admin_id"),
            "DELETE_ANSWER_KEY",
            f"Deleted answer key '{key['exam_name']}'",
        )
        flash("Answer key deleted.", "info")
    return redirect(url_for("answer_key.list_answer_keys"))


# ---------------------------------------------------------------
# Question Paper: plain upload + view (independent of the OCR /
# answer-key questions flow - just stores the exam's question
# paper file so it can be opened alongside the answer key/scans)
# ---------------------------------------------------------------

@answer_key_bp.route("/<int:answer_key_id>/question-paper", methods=["GET"])
@login_required
def question_paper_page(answer_key_id):
    key = get_answer_key_by_id(answer_key_id)
    if not key:
        flash("Answer key not found.", "danger")
        return redirect(url_for("answer_key.list_answer_keys"))
    return render_template("answer_keys/question_paper.html", key=key)


@answer_key_bp.route("/<int:answer_key_id>/question-paper/upload", methods=["POST"])
@login_required
def upload_question_paper(answer_key_id):
    key = get_answer_key_by_id(answer_key_id)
    if not key:
        flash("Answer key not found.", "danger")
        return redirect(url_for("answer_key.list_answer_keys"))

    file = request.files.get("question_paper_file")
    if not file or file.filename == "":
        flash("Please choose a file to upload.", "danger")
        return redirect(url_for("answer_key.question_paper_page", answer_key_id=answer_key_id))

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in Config.ALLOWED_IMAGE_EXTENSIONS:
        flash("Only JPG, JPEG, PNG, or PDF files are supported.", "danger")
        return redirect(url_for("answer_key.question_paper_page", answer_key_id=answer_key_id))

    os.makedirs(Config.ANSWER_KEYS_FOLDER, exist_ok=True)
    filename = secure_filename(file.filename)
    saved_filename = f"qpaper_{answer_key_id}_{uuid.uuid4().hex}_{filename}"
    saved_path = os.path.join(Config.ANSWER_KEYS_FOLDER, saved_filename)
    file.save(saved_path)

    update_question_paper_path(answer_key_id, saved_path)
    log_activity(
        session.get("admin_id"),
        "UPLOAD_QUESTION_PAPER",
        f"Uploaded question paper for answer key #{answer_key_id}",
    )
    flash("Question paper uploaded.", "success")
    return redirect(url_for("answer_key.question_paper_page", answer_key_id=answer_key_id))


@answer_key_bp.route("/<int:answer_key_id>/question-paper/view", methods=["GET"])
@login_required
def view_question_paper(answer_key_id):
    key = get_answer_key_by_id(answer_key_id)
    if not key or not key.get("question_paper_path"):
        flash("No question paper uploaded for this answer key yet.", "warning")
        return redirect(url_for("answer_key.question_paper_page", answer_key_id=answer_key_id))

    folder = os.path.dirname(key["question_paper_path"])
    filename = os.path.basename(key["question_paper_path"])
    return send_from_directory(folder, filename)


# ---------------------------------------------------------------
# Answer Keys: preview (shows questions, allows add/edit/delete)
# ---------------------------------------------------------------

@answer_key_bp.route("/<int:answer_key_id>")
@login_required
def preview_answer_key(answer_key_id):
    key = get_answer_key_by_id(answer_key_id)
    if not key:
        flash("Answer key not found.", "danger")
        return redirect(url_for("answer_key.list_answer_keys"))

    questions = get_questions_for_answer_key(answer_key_id)
    total_marks = sum(float(q["max_marks"]) for q in questions) if questions else 0

    return render_template(
        "answer_keys/preview.html",
        key=key,
        questions=questions,
        total_marks=total_marks,
    )


# ---------------------------------------------------------------
# Questions: upload an image/PDF of the answer key -> OCR -> auto-split
# into individual questions -> review screen -> bulk save
# ---------------------------------------------------------------

@answer_key_bp.route("/<int:answer_key_id>/upload-ocr", methods=["POST"])
@login_required
def upload_answer_key_image(answer_key_id):
    key = get_answer_key_by_id(answer_key_id)
    if not key:
        flash("Answer key not found.", "danger")
        return redirect(url_for("answer_key.list_answer_keys"))

    file = request.files.get("answer_key_file")
    if not file or file.filename == "":
        flash("Please choose an image or PDF file to upload.", "danger")
        return redirect(url_for("answer_key.preview_answer_key", answer_key_id=answer_key_id))

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in Config.ALLOWED_IMAGE_EXTENSIONS:
        flash("Only JPG, JPEG, PNG, or PDF files are supported.", "danger")
        return redirect(url_for("answer_key.preview_answer_key", answer_key_id=answer_key_id))

    os.makedirs(Config.ANSWER_KEYS_FOLDER, exist_ok=True)
    filename = secure_filename(file.filename)
    saved_path = os.path.join(
        Config.ANSWER_KEYS_FOLDER, f"key{answer_key_id}_{uuid.uuid4().hex}_{filename}"
    )
    file.save(saved_path)

    try:
        raw_text = extract_text(saved_path)
    except Exception as e:
        flash(
            "Could not read text from that file. Make sure Tesseract OCR "
            f"(and Poppler, for PDFs) is installed and configured in config.py. ({e})",
            "danger",
        )
        return redirect(url_for("answer_key.preview_answer_key", answer_key_id=answer_key_id))

    parsed_questions = parse_questions_from_text(raw_text)

    if not parsed_questions:
        flash(
            "No questions could be detected in that file. Try a clearer scan, "
            "or add questions manually below.",
            "warning",
        )
        return redirect(url_for("answer_key.preview_answer_key", answer_key_id=answer_key_id))

    log_activity(
        session.get("admin_id"),
        "OCR_UPLOAD_ANSWER_KEY",
        f"Uploaded '{file.filename}' for answer key #{answer_key_id}, "
        f"detected {len(parsed_questions)} question(s)",
    )

    # Nothing is saved to the questions table yet - the admin reviews
    # and corrects the OCR result first, then confirms on this screen.
    return render_template(
        "answer_keys/ocr_review.html",
        key=key,
        parsed_questions=parsed_questions,
        raw_text=raw_text,
    )


@answer_key_bp.route("/<int:answer_key_id>/questions/bulk-save", methods=["POST"])
@login_required
def bulk_save_questions(answer_key_id):
    key = get_answer_key_by_id(answer_key_id)
    if not key:
        flash("Answer key not found.", "danger")
        return redirect(url_for("answer_key.list_answer_keys"))

    numbers = request.form.getlist("question_number[]")
    answers = request.form.getlist("expected_answer[]")
    keywords_list = request.form.getlist("keywords[]")
    marks_list = request.form.getlist("max_marks[]")
    include_flags = request.form.getlist("include[]")

    # "include[]" is only submitted for rows whose checkbox is checked,
    # so match rows by index and only keep the ones flagged as included.
    included_indexes = {int(i) for i in include_flags if i.isdigit()}

    questions = []
    for i, number in enumerate(numbers):
        if i not in included_indexes:
            continue
        questions.append(
            {
                "question_number": number,
                "expected_answer": answers[i] if i < len(answers) else "",
                "keywords": keywords_list[i] if i < len(keywords_list) else "",
                "max_marks": marks_list[i] if i < len(marks_list) else 0,
            }
        )

    inserted = create_questions_bulk(answer_key_id, questions)

    log_activity(
        session.get("admin_id"),
        "BULK_ADD_QUESTIONS",
        f"Added {inserted} question(s) to answer key #{answer_key_id} via OCR upload",
    )
    flash(f"{inserted} question(s) added from the uploaded file.", "success")
    return redirect(url_for("answer_key.preview_answer_key", answer_key_id=answer_key_id))


# ---------------------------------------------------------------
# Questions: add
# ---------------------------------------------------------------

@answer_key_bp.route("/<int:answer_key_id>/questions/add", methods=["POST"])
@login_required
def add_question(answer_key_id):
    question_number = request.form.get("question_number", "").strip()
    expected_answer = request.form.get("expected_answer", "").strip()
    keywords = request.form.get("keywords", "").strip()
    max_marks = request.form.get("max_marks", "0").strip()

    if not question_number or not expected_answer or not max_marks:
        flash("Question number, expected answer, and max marks are required.", "danger")
        return redirect(url_for("answer_key.preview_answer_key", answer_key_id=answer_key_id))

    try:
        max_marks_val = float(max_marks)
    except ValueError:
        flash("Max marks must be a number.", "danger")
        return redirect(url_for("answer_key.preview_answer_key", answer_key_id=answer_key_id))

    create_question(answer_key_id, question_number, expected_answer, keywords, max_marks_val)
    flash(f"Question {question_number} added.", "success")
    return redirect(url_for("answer_key.preview_answer_key", answer_key_id=answer_key_id))


# ---------------------------------------------------------------
# Questions: edit
# ---------------------------------------------------------------

@answer_key_bp.route("/questions/<int:question_id>/edit", methods=["POST"])
@login_required
def edit_question(question_id):
    question = get_question_by_id(question_id)
    if not question:
        flash("Question not found.", "danger")
        return redirect(url_for("answer_key.list_answer_keys"))

    question_number = request.form.get("question_number", "").strip()
    expected_answer = request.form.get("expected_answer", "").strip()
    keywords = request.form.get("keywords", "").strip()
    max_marks = request.form.get("max_marks", "0").strip()

    try:
        max_marks_val = float(max_marks)
    except ValueError:
        flash("Max marks must be a number.", "danger")
        return redirect(
            url_for("answer_key.preview_answer_key", answer_key_id=question["answer_key_id"])
        )

    update_question(question_id, question_number, expected_answer, keywords, max_marks_val)
    flash("Question updated.", "success")
    return redirect(
        url_for("answer_key.preview_answer_key", answer_key_id=question["answer_key_id"])
    )


# ---------------------------------------------------------------
# Questions: delete
# ---------------------------------------------------------------

@answer_key_bp.route("/questions/<int:question_id>/delete", methods=["POST"])
@login_required
def delete_question_route(question_id):
    question = get_question_by_id(question_id)
    if not question:
        flash("Question not found.", "danger")
        return redirect(url_for("answer_key.list_answer_keys"))

    answer_key_id = question["answer_key_id"]
    delete_question(question_id)
    flash("Question deleted.", "info")
    return redirect(url_for("answer_key.preview_answer_key", answer_key_id=answer_key_id))


# ---------------------------------------------------------------
# Subjects: list / add / edit / delete
# ---------------------------------------------------------------

@answer_key_bp.route("/subjects")
@login_required
def list_subjects():
    subjects = get_all_subjects()
    return render_template("answer_keys/subjects.html", subjects=subjects)


@answer_key_bp.route("/subjects/add", methods=["POST"])
@login_required
def add_subject():
    subject_code = request.form.get("subject_code", "").strip()
    subject_name = request.form.get("subject_name", "").strip()
    department = request.form.get("department", "").strip()
    semester = request.form.get("semester", "").strip()

    if not subject_code or not subject_name:
        flash("Subject code and name are required.", "danger")
        return redirect(url_for("answer_key.list_subjects"))

    if get_subject_by_code(subject_code):
        flash(f"Subject code '{subject_code}' already exists.", "danger")
        return redirect(url_for("answer_key.list_subjects"))

    create_subject(subject_code, subject_name, department, semester)
    flash("Subject added.", "success")
    return redirect(url_for("answer_key.list_subjects"))


@answer_key_bp.route("/subjects/<int:subject_id>/edit", methods=["POST"])
@login_required
def edit_subject(subject_id):
    subject_code = request.form.get("subject_code", "").strip()
    subject_name = request.form.get("subject_name", "").strip()
    department = request.form.get("department", "").strip()
    semester = request.form.get("semester", "").strip()

    if not subject_code or not subject_name:
        flash("Subject code and name are required.", "danger")
        return redirect(url_for("answer_key.list_subjects"))

    update_subject(subject_id, subject_code, subject_name, department, semester)
    flash("Subject updated.", "success")
    return redirect(url_for("answer_key.list_subjects"))


@answer_key_bp.route("/subjects/<int:subject_id>/delete", methods=["POST"])
@login_required
def delete_subject_route(subject_id):
    delete_subject(subject_id)
    flash("Subject deleted.", "info")
    return redirect(url_for("answer_key.list_subjects"))
