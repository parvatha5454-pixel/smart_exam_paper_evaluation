import re

def extract_marks(text):
    """
    Extract marks from OCR text.
    Supports:
      (2)
      (5 Marks)
      2 Marks
      Max Marks: 10
      Marks : 5
    """

    patterns = [
        r'\((\d+)\)',                         # (2)
        r'\((\d+)\s*Marks?\)',                # (5 Marks)
        r'(\d+)\s*Marks?',                    # 2 Marks
        r'Max\s*Marks?\s*[:=-]?\s*(\d+)',     # Max Marks: 10
        r'Marks?\s*[:=-]?\s*(\d+)'            # Marks : 5
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))

    return 0