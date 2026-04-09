"""Production-ready Flask API to convert PDF files to Word (.docx)."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from flask import Flask, after_this_request, jsonify, request, send_file
from flask_cors import CORS
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from pdf2docx import Converter

# Flask app object used by Gunicorn/Render (`gunicorn app:app`).
app = Flask(__name__)

# Enable Cross-Origin Resource Sharing for frontend clients.
CORS(app)

# Limit upload size to 20 MB for safer production behavior.
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024

# Allowed file extensions.
ALLOWED_EXTENSIONS = {".pdf"}


@app.get("/")
def healthcheck():
    """Simple health route for Render/monitoring checks."""
    return jsonify({"status": "ok", "message": "PDF to DOCX API is running"})


@app.errorhandler(RequestEntityTooLarge)
def handle_large_file(_error):
    """Return a clear error when file size exceeds MAX_CONTENT_LENGTH."""
    return jsonify({"status": "error", "message": "File too large. Maximum size is 20 MB."}), 413


@app.post("/convert")
def convert_pdf_to_docx():
    """Accept a PDF file and return the converted DOCX file."""
    # Validate multipart form-data contains key "file".
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No file provided (key must be 'file')."}), 400

    uploaded_file = request.files["file"]

    # Validate selected file exists.
    if not uploaded_file or uploaded_file.filename == "":
        return jsonify({"status": "error", "message": "No file selected."}), 400

    original_name = secure_filename(uploaded_file.filename)
    suffix = Path(original_name).suffix.lower()

    # Validate file extension.
    if suffix not in ALLOWED_EXTENSIONS:
        return jsonify({"status": "error", "message": "Invalid file type. Please upload a PDF file."}), 400

    # Create a unique temporary directory for this request.
    temp_dir = tempfile.mkdtemp(prefix="pdf_to_docx_")

    # Build temporary file paths.
    pdf_path = os.path.join(temp_dir, "input.pdf")
    docx_path = os.path.join(temp_dir, "output.docx")

    try:
        # Save uploaded PDF temporarily.
        uploaded_file.save(pdf_path)

        # Convert PDF to DOCX using pdf2docx.
        converter = Converter(pdf_path)
        try:
            converter.convert(docx_path)
        finally:
            converter.close()

        # Ensure output was created before returning.
        if not os.path.exists(docx_path):
            return jsonify({"status": "error", "message": "Conversion failed. Could not generate DOCX file."}), 500

        output_name = f"{Path(original_name).stem}.docx"

        @after_this_request
        def cleanup_temp_files(response):
            """Delete temporary directory and files after response is sent."""
            shutil.rmtree(temp_dir, ignore_errors=True)
            return response

        # Return generated DOCX as downloadable file.
        return send_file(
            docx_path,
            as_attachment=True,
            download_name=output_name,
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    except Exception:
        # Best-effort cleanup on failures before response finalization.
        shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify({"status": "error", "message": "Invalid or unreadable PDF file."}), 400


if __name__ == "__main__":
    # For local development. Render/Gunicorn should use: gunicorn app:app
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
