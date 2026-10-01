import re

def extract_keywords(text):
    """
    Extract keywords from OCR text.
    Supports:
    Keywords:
    Keyword:
    Keywords -
    """

    keywords = []

    match = re.search(
        r'Keywords?\s*[:\-]?\s*(.*?)(?:Answer|Mark Distribution|$)',
        text,
        re.IGNORECASE | re.DOTALL
    )

    if match:
        keyword_text = match.group(1)

        keyword_text = keyword_text.replace("*", ",")
        keyword_text = keyword_text.replace("•", ",")
        keyword_text = keyword_text.replace("+", ",")

        for word in re.split(r'[,\n]', keyword_text):
            word = word.strip()

            if len(word) > 1:
                keywords.append(word)

    return keywords