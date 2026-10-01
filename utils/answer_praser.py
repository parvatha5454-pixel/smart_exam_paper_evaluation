import re

def extract_answer(text):
    """
    Extract expected answer from OCR text.
    """

    answer = ""

    patterns = [

        r'Answer\s*[:\-]?\s*(.*?)(?:Keywords?|Mark Distribution|$)',

        r'Answer\s*/\s*Keywords?\s*[:\-]?\s*(.*)',

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE | re.DOTALL
        )

        if match:

            answer = match.group(1).strip()

            break

    return answer