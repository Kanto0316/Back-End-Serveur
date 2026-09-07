import re

from app.models.response import Article

# Codes must contain both letters and digits. Conservative matching avoids inventing rows.
CODE_PATTERN = re.compile(r"^(?=.{4,32}$)(?=.*[A-Z])(?=.*\d)[A-Z0-9][A-Z0-9._/-]*$", re.IGNORECASE)


def extract_articles(text: str) -> tuple[list[Article], list[str]]:
    articles: list[Article] = []
    seen: set[tuple[str, str]] = set()
    for raw_line in text.splitlines():
        line = " ".join(raw_line.strip().split())
        if not line:
            continue
        parts = line.split(" ", 1)
        if len(parts) != 2:
            continue
        code, designation = parts[0].strip("|:;"), parts[1].strip(" |:;-")
        if not CODE_PATTERN.fullmatch(code) or len(designation) < 3 or not any(char.isalpha() for char in designation):
            continue
        key = (code.upper(), designation)
        if key in seen:
            continue
        seen.add(key)
        # Phase 1 confidence reflects parser evidence, not a fabricated OCR probability.
        confidence = 0.92 if len(designation.split()) >= 2 else 0.80
        articles.append(Article(code=code.upper(), designation=designation, confidence=confidence))
    warnings = [] if articles else ["Aucune ligne article fiable détectée"]
    return articles, warnings
