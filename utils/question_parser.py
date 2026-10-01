import re

def extract_question(text):
    """
    Extract question number and question text.
    """

    result = {
        "question_no": "",
        "question": ""
    }

    # Split into lines
    lines = text.strip().split("\n")

    if not lines:
        return result

    first_line = lines[0].strip()

    # Extract question number
    q = re.match(
        r'^(Q\s*\d+|Question\s+\d+|\d+\([a-zA-Z]\)|\d+\.|\d+\))',
        first_line,
        re.IGNORECASE
    )

    if q:
        number = q.group(0)

        number = number.replace("Question", "")
        number = number.replace("Q", "")
        number = number.replace(".", "")
        number = number.replace(")", "")

        result["question_no"] = number.strip()

        question = first_line[q.end():].strip()

        # Remove marks like (2), (5 Marks)
        question = re.sub(r'\(\d+\s*Marks?\)', '', question, flags=re.IGNORECASE)
        question = re.sub(r'\(\d+\)', '', question)

        result["question"] = question.strip()

    return result