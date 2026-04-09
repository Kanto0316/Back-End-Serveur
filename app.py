"""Flask API for uploading and processing PDF files.

This module exposes:
- `POST /upload`: accepts a PDF in multipart/form-data using key `file`
  and returns the first 1000 characters extracted with PyPDF2.

Designed to be compatible with Render/Gunicorn deployments.
"""

from __future__ import annotations

import io
import os

from flask import Flask, jsonify, request
from flask_cors import CORS
from PyPDF2 import PdfReader

# Flask application object used by Gunicorn/Render: `gunicorn app:app`
app = Flask(__name__)

# Enable CORS for frontend communication.
CORS(app)

# Limit output text length for performance.
MAX_OUTPUT_CHARS = 1000


@app.get("/")
def healthcheck():
    """Simple health endpoint to verify the service is running."""
    return jsonify({"status": "ok", "message": "Service is running"})


@app.post("/upload")
def upload_pdf():
    """Receive a PDF file and return extracted text (truncated)."""
    # Validate that the form-data contains a file entry.
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No file provided (key must be 'file')."}), 400

    file_storage = request.files["file"]

    # Validate selected file.
    if not file_storage or file_storage.filename == "":
        return jsonify({"status": "error", "message": "No file selected."}), 400

    # Basic file type validation by extension.
    filename = file_storage.filename.lower()
    if not filename.endswith(".pdf"):
        return jsonify({"status": "error", "message": "Invalid file type. Please upload a PDF."}), 400

    try:
        # Read file content into memory then parse with PyPDF2.
        pdf_bytes = file_storage.read()
        if not pdf_bytes:
            return jsonify({"status": "error", "message": "Uploaded file is empty."}), 400

        reader = PdfReader(io.BytesIO(pdf_bytes))

        # Extract text page by page.
        extracted_parts: list[str] = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            extracted_parts.append(page_text)

        extracted_text = "\n".join(extracted_parts).strip()

        return jsonify(
            {
                "status": "ok",
                "content": extracted_text[:MAX_OUTPUT_CHARS],
            }
        )
    except Exception:
        # Avoid leaking internal exception details in production responses.
        return jsonify({"status": "error", "message": "Invalid or unreadable PDF file."}), 400


if __name__ == "__main__":
    # Local development server. In production, use gunicorn: `gunicorn app:app`.
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
