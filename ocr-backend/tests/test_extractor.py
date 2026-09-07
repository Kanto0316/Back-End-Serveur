from app.ocr.extractor import extract_articles


def test_extractor_ignores_unreliable_lines_and_duplicates() -> None:
    articles, warnings = extract_articles("Titre du document\nABC123 Pompe hydraulique\nABC123 Pompe hydraulique\n12345 sans lettres")
    assert [(item.code, item.designation) for item in articles] == [("ABC123", "Pompe hydraulique")]
    assert warnings == []


def test_extractor_empty() -> None:
    articles, warnings = extract_articles("")
    assert articles == []
    assert warnings == ["Aucune ligne article fiable détectée"]
