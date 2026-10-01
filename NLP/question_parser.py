"""
NLP/question_parser.py
-----------------------
Takes the raw OCR text of a printed answer key (which is one big blob)
and splits it into a list of individual questions, each with:
    - question_number
    - expected_answer   (the answer/definition text)
    - keywords          (comma-separated keywords for evaluation)
    - max_marks         (parsed from "(2 Marks)" style annotations)

This is deliberately rule-based (regex) rather than ML-based, because
answer-key sheets follow a fairly predictable layout:

    5. Difference between List and Tuple. (2 Marks)
    Mark Distribution: 1 Mark - List, 1 Mark - Tuple
    Answer / Keywords: + Can be modified ... + Uses square brackets ...

If OCR quality varies, this will not be perfect — that's why the upload
flow shows an editable review screen before anything is saved to the
database, instead of silently trusting the parse.
"""

import re

# Matches a question number wherever it appears in the (often
# continuous, wrapped) OCR text - e.g. "5. Difference...", "10) What...".
# OCR output from a scanned/photographed page rarely has one question
# per line, so we can't anchor on line-start; instead we look for
# "<1-2 digits>. " or "<1-2 digits>) " immediately followed by a
# capital letter, which is a reasonable signal for "new question"
# rather than a stray number inside marks/keywords text.
QUESTION_START_RE = re.compile(r"(?<!\d)(\d{1,2})[\.\)]\s+(?=[A-Z])")

# Pulls the question number off the front of a block: "5. Difference..."
QUESTION_NUMBER_RE = re.compile(r"^\s*(\d{1,2})[\.\)]\s*(.*)", re.DOTALL)

# "(2 Marks)" / "(2 Mark)" anywhere in the block.
MARKS_RE = re.compile(r"\(\s*(\d+(?:\.\d+)?)\s*Marks?\s*\)", re.IGNORECASE)

# Everything after "Answer / Keywords:" or "Keywords:" up to the end
# of the block (or the next labelled section, if any).
KEYWORDS_RE = re.compile(
    r"(?:Answer\s*/\s*Keywords|Keywords)\s*:\s*(.*)", re.IGNORECASE | re.DOTALL
)

# "Mark Distribution: ..." section, captured separately so it isn't
# lumped into the main answer text.
MARK_DISTRIBUTION_RE = re.compile(
    r"Mark\s*Distribution\s*:\s*(.*?)(?=(?:Answer\s*/\s*Keywords|Keywords)\s*:|$)",
    re.IGNORECASE | re.DOTALL,
)


def _clean(text):
    """Collapse whitespace/line-breaks that OCR tends to scatter around."""
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip(" .,-|_")


def split_into_blocks(raw_text):
    """
    Split the full OCR text into one chunk per question, based on
    every "<number>. <Capital letter>" occurrence found anywhere in
    the text (see QUESTION_START_RE above). Each block runs from one
    match up to the start of the next one.
    """
    if not raw_text or not raw_text.strip():
        return []

    matches = list(QUESTION_START_RE.finditer(raw_text))
    if not matches:
        return []

    blocks = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw_text)
        block = raw_text[start:end].strip()
        if block:
            blocks.append(block)

    return blocks


def parse_question_block(block):
    """
    Parse a single question's raw text block into a structured dict.
    Falls back to sensible defaults if a piece (marks/keywords) isn't found,
    so the admin can fill in gaps on the review screen rather than losing
    the question entirely.
    """
    num_match = QUESTION_NUMBER_RE.match(block)
    if num_match:
        question_number = num_match.group(1)
        rest = num_match.group(2)
    else:
        question_number = ""
        rest = block

    marks_match = MARKS_RE.search(rest)
    max_marks = float(marks_match.group(1)) if marks_match else 0.0

    keywords_match = KEYWORDS_RE.search(rest)
    keywords = _clean(keywords_match.group(1)) if keywords_match else ""

    dist_match = MARK_DISTRIBUTION_RE.search(rest)
    mark_distribution = _clean(dist_match.group(1)) if dist_match else ""

    # The "expected answer" is just the question text itself - the
    # mark distribution and keywords are kept in their own fields so
    # nothing is duplicated across columns on the review screen.
    answer_source = rest
    if keywords_match:
        answer_source = rest[: keywords_match.start()]
    if dist_match:
        answer_source = answer_source[: dist_match.start()]

    expected_answer = MARKS_RE.sub("", answer_source)
    expected_answer = _clean(expected_answer)

    return {
        "question_number": question_number,
        "expected_answer": expected_answer or _clean(rest),
        "keywords": keywords,
        "max_marks": max_marks,
        "mark_distribution": mark_distribution,
    }


def parse_questions_from_text(raw_text):
    """
    Full pipeline: raw OCR text in, list of question dicts out.
    Blocks that don't start with a recognisable question number are
    skipped (they're usually running headers/footers like
    "CS0118 - PYTHON PROGRAMMING ANSWER KEY").
    """
    blocks = split_into_blocks(raw_text)
    questions = []

    for block in blocks:
        if not QUESTION_NUMBER_RE.match(block):
            continue
        parsed = parse_question_block(block)
        if parsed["question_number"]:
            questions.append(parsed)

    return questions
