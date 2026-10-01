import re

def split_questions(ocr_text):

    text = re.sub(r'\r', '', ocr_text)
    text = re.sub(r'\n+', '\n', text)

    pattern = r'(?=(?:^|\n)\s*(?:Q\s*\d+|Question\s+\d+|\d+\.\s|\d+\)\s|\d+\([a-zA-Z]\)))'

    blocks = re.split(pattern, text, flags=re.MULTILINE)

    questions = []

    for block in blocks:
        block = block.strip()

        if block:
            questions.append(block)

    return questions