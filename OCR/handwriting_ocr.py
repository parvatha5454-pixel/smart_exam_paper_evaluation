"""
OCR/handwriting_ocr.py
-------------------------
EasyOCR-based text extraction, used specifically for photographed/
scanned STUDENT ANSWER SHEETS (handwriting).

EasyOCR uses a deep-learning text detector + recognizer, which reads
handwriting noticeably better than Tesseract (Tesseract is built
mainly for printed/typed text and struggles badly with handwriting -
that's what was happening in the Evaluation module before).

The Answer Key / Question Paper OCR (typed/printed documents) is left
alone and still uses Tesseract (OCR/ocr_utils.py) - it already works
well for printed text, no need to change it.

OFFLINE NOTE: EasyOCR downloads its pretrained model files (a few
hundred MB) the FIRST time it runs, which needs an internet
connection. After that first run, the models are cached on disk
(~/.EasyOCR by default) and everything works fully offline.
"""

import easyocr

# Loading the model is slow (a few seconds), so load it once and
# reuse it for every call instead of reloading per-request.
_reader = None


def _get_reader():
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(["en"], gpu=False)
    return _reader


def extract_handwritten_text(image_path):
    """
    Returns (text, avg_confidence, word_count):
      - text: all detected text joined together
      - avg_confidence: EasyOCR's average confidence, scaled to 0-100
        (same scale as Tesseract's, so it's a drop-in replacement
        anywhere the old confidence check was used)
      - word_count: total number of words detected across the sheet

    Same 3-value return shape as
    OCR.ocr_utils.extract_text_with_confidence, so both the upload
    quality-check and the Evaluation scoring code can use either one
    interchangeably.
    """
    reader = _get_reader()
    results = reader.readtext(image_path)  # list of (bbox, text, confidence)

    if not results:
        return "", 0.0, 0

    texts = [r[1] for r in results]
    confidences = [r[2] for r in results]

    full_text = "\n".join(texts)
    avg_confidence = (sum(confidences) / len(confidences)) * 100
    word_count = sum(len(t.split()) for t in texts)

    return full_text, avg_confidence, word_count
