"""
OCR/ocr_utils.py
------------------
Text extraction from images using Tesseract OCR.
Used by:
  - Module 2 (Answer Key Upload): extract expected answer text from
    a photo of a printed/handwritten answer key.
  - Module 4 (OCR Text Extraction): extract student answers from
    scanned answer sheets.
"""

import pytesseract
from PIL import Image
from config import Config

# Point pytesseract at the Tesseract engine location, if configured.
if Config.TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = Config.TESSERACT_CMD


def extract_text_with_confidence(image_path):
    """
    Like extract_text_from_image, but also returns:
      - avg_confidence: Tesseract's own average confidence (0-100)
      - word_count: how many words it actually detected
    """
    image = Image.open(image_path)
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

    confidences = []
    for i, word in enumerate(data.get("text", [])):
        if word.strip():
            conf = data["conf"][i]
            if str(conf).strip() not in ("", "-1"):
                confidences.append(int(float(conf)))

    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
    word_count = len(confidences)
    text = pytesseract.image_to_string(image).strip()
    return text, avg_confidence, word_count

def extract_text_from_image(image_path):
    """
    Runs OCR on the given image file and returns the extracted text.
    Raises pytesseract.TesseractNotFoundError if the Tesseract engine
    isn't installed / configured correctly.
    """
    image = Image.open(image_path)
    text = pytesseract.image_to_string(image)
    return text.strip()


def extract_text_from_pdf(pdf_path):
    """
    Converts each page of the PDF to an image and OCRs every page,
    joining the results together. Used when an answer key is uploaded
    as a PDF instead of a photo/scan image.
    """
    from pdf2image import convert_from_path

    pages = convert_from_path(pdf_path, dpi=200)
    full_text = []
    for page in pages:
        full_text.append(pytesseract.image_to_string(page))
    return "\n".join(full_text).strip()


def extract_text(file_path):
    """
    Entry point used by the answer-key upload flow: figures out
    whether the uploaded file is a PDF or an image and routes it to
    the right extractor.
    """
    import os

    ext = os.path.splitext(file_path)[1].lower().lstrip(".")
    if ext == "pdf":
        return extract_text_from_pdf(file_path)
    return extract_text_from_image(file_path)


# ------------------------------------------------------------------
# Handwritten text extraction (EasyOCR) - used for scanned STUDENT
# answer sheets (Scanning + Evaluation modules), since Tesseract
# above is built for printed/typed text and reads handwriting poorly.
# Tesseract is still used for the Answer Key upload flow, since answer
# keys are typically typed/printed documents where it works well.
#
# EasyOCR downloads its recognition model (~100MB) the FIRST time it
# runs - that needs an internet connection once. After that, the
# model is cached on disk and everything runs fully offline.
# ------------------------------------------------------------------

_easyocr_reader = None


def _get_easyocr_reader():
    """Loads the EasyOCR model once and reuses it (loading it is slow)."""
    global _easyocr_reader
    if _easyocr_reader is None:
        import easyocr

        _easyocr_reader = easyocr.Reader(["en"], gpu=False)
    return _easyocr_reader


def extract_handwritten_text(image_path):
    """Returns just the recognized text from a handwritten scanned sheet."""
    reader = _get_easyocr_reader()
    results = reader.readtext(image_path, detail=0)
    return "\n".join(results).strip()


def extract_handwritten_text_with_confidence(image_path):
    """
    Like extract_handwritten_text, but also returns:
      - avg_confidence: EasyOCR's own average confidence (0-100) across
        every text region it detected
      - word_count: total number of words detected

    Used by the scanned-sheet upload quality check (reject blurry/
    unreadable photos) and by the Evaluation module's keyword scoring.
    """
    reader = _get_easyocr_reader()
    results = reader.readtext(image_path, detail=1)  # [(bbox, text, confidence), ...]

    if not results:
        return "", 0.0, 0

    texts = [r[1] for r in results]
    confidences = [r[2] * 100 for r in results]  # EasyOCR gives 0-1, scale to 0-100
    avg_confidence = sum(confidences) / len(confidences)
    word_count = sum(len(t.split()) for t in texts)

    return "\n".join(texts).strip(), avg_confidence, word_count
