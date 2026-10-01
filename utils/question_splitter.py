import re

def split_questions(text):
    """
    Split OCR text into individual question blocks.
    Supports:
      1.
      1)
      Q1
      Question 1
      2(a)
      2(b)
    """

    # Normalize newlines
    text = text.replace("\r", "")

    # Pattern for detecting the start of a question
    pattern = r'(?=^\s*(?:Q\s*\d+|Question\s+\d+|\d+\.|\d+\)|\d+\([a-zA-Z]\)))'

    blocks = re.split(pattern, text, flags=re.MULTILINE)

    questions = []

    for block in blocks:
        block = block.strip()
        if block:
            questions.append(block)

    return questions