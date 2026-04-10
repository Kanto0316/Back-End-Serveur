"""Flask API to extract table rows (Ref, Designation, Quantite, Unite) from a PDF."""

from __future__ import annotations

import io
import os
import re
from typing import Dict, List

import pdfplumber
from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import RequestEntityTooLarge

app = Flask(__name__)
CORS(app)

# Protect the API from very large uploads.
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB

# Pattern tuned for lines like:
# 001BOLB8X40 BOULON BICHROMATE M8X40 32 PIE
ROW_PATTERN = re.compile(
    r"^(?P<ref>\S+)\s+(?P<designation>.+?)\s+(?P<quantite>\d+(?:[.,]\d+)?)\s+(?P<unite>[A-Za-zÀ-ÿ]{2,10})$"
)


def normalize_text(value: str) -> str:
    """Trim and collapse duplicated spaces in text."""
    return re.sub(r"\s+", " ", value).strip()


def parse_row(line: str) -> Dict[str, str] | None:
    """Parse a candidate line and return a normalized row if it matches expected columns."""
    cleaned_line = normalize_text(line)
    match = ROW_PATTERN.match(cleaned_line)
    if not match:
        return None

    return {
        "Ref": normalize_text(match.group("ref")),
        "Designation": normalize_text(match.group("designation")),
        "Quantite": normalize_text(match.group("quantite")).replace(",", "."),
        "Unite": normalize_text(match.group("unite")).upper(),
    }


def extract_rows_from_pdf(file_bytes: bytes) -> List[Dict[str, str]]:
    """Extract and parse rows from all pages of a PDF file represented as bytes."""
    rows: List[Dict[str, str]] = []

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for raw_line in text.splitlines():
                parsed = parse_row(raw_line)
                if parsed:
                    rows.append(parsed)

    return rows


@app.errorhandler(RequestEntityTooLarge)
def handle_large_file(_error):
    return jsonify({"status": "error", "message": "Fichier trop volumineux (max 20 MB)."}), 413


@app.post("/")
def extract_pdf_data():
    """Receive a PDF and return extracted table data as JSON."""
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "Aucun fichier reçu (clé attendue: 'file')."}), 400

    uploaded_file = request.files["file"]

    if not uploaded_file or uploaded_file.filename == "":
        return jsonify({"status": "error", "message": "Aucun fichier sélectionné."}), 400

    if not uploaded_file.filename.lower().endswith(".pdf"):
        return jsonify({"status": "error", "message": "Fichier invalide. Merci d'envoyer un PDF."}), 400

    try:
        pdf_content = uploaded_file.read()
        if not pdf_content:
            return jsonify({"status": "error", "message": "Le fichier PDF est vide."}), 400

        rows = extract_rows_from_pdf(pdf_content)

        if not rows:
            return jsonify(
                {
                    "status": "error",
                    "message": "Aucune ligne exploitable trouvée (colonnes Ref, Designation, Quantite, Unite).",
                }
            ), 422

        return jsonify(rows), 200

    except pdfplumber.pdfminer.pdfparser.PDFSyntaxError:
        return jsonify({"status": "error", "message": "PDF invalide ou corrompu."}), 400
    except Exception:
        return jsonify({"status": "error", "message": "Erreur interne lors de l'extraction du PDF."}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
