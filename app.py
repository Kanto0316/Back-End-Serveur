"""Flask backend for secure file transfer (upload + unique download link)."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from uuid import uuid4

from flask import Flask, jsonify, request, send_file, url_for
from flask_cors import CORS
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# Security: 20 MB max upload size.
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024

UPLOAD_DIR = Path("uploads")
INDEX_FILE = Path("file_index.json")
# Bonus: files expire after 24h.
FILE_TTL_SECONDS = 24 * 60 * 60


def ensure_storage() -> None:
    """Create storage directory and metadata index file when missing."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    if not INDEX_FILE.exists():
        INDEX_FILE.write_text("{}", encoding="utf-8")


def load_index() -> dict:
    """Load metadata index from JSON file."""
    ensure_storage()
    try:
        return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_index(index: dict) -> None:
    """Persist metadata index to JSON file."""
    INDEX_FILE.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def cleanup_expired_files(index: dict) -> dict:
    """Delete expired files and remove them from index."""
    now = int(time.time())
    updated = dict(index)

    for file_id, record in index.items():
        created_at = int(record.get("created_at", 0))
        if now - created_at > FILE_TTL_SECONDS:
            file_path = Path(record.get("path", ""))
            if file_path.exists():
                try:
                    file_path.unlink()
                except OSError:
                    pass
            updated.pop(file_id, None)

    return updated


@app.errorhandler(RequestEntityTooLarge)
def handle_large_file(_error):
    return jsonify({"status": "error", "message": "Fichier trop volumineux (max 20 MB)."}), 413


@app.post("/upload")
def upload_file():
    """Receive a file, store it, and return a unique download URL."""
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "Aucun fichier reçu (clé attendue: 'file')."}), 400

    uploaded_file = request.files["file"]
    if not uploaded_file or uploaded_file.filename == "":
        return jsonify({"status": "error", "message": "Aucun fichier sélectionné."}), 400

    original_filename = secure_filename(uploaded_file.filename)
    if not original_filename:
        return jsonify({"status": "error", "message": "Nom de fichier invalide."}), 400

    ensure_storage()
    index = cleanup_expired_files(load_index())

    file_id = uuid4().hex
    unique_name = f"{file_id}_{original_filename}"
    destination = UPLOAD_DIR / unique_name

    try:
        uploaded_file.save(destination)
    except OSError:
        return jsonify({"status": "error", "message": "Impossible de sauvegarder le fichier."}), 500

    created_at = int(time.time())
    index[file_id] = {
        "id": file_id,
        "filename": original_filename,
        "path": str(destination),
        "created_at": created_at,
    }
    save_index(index)

    download_url = request.url_root.rstrip("/") + url_for("download_file", id=file_id)
    return jsonify({"download_url": download_url}), 201


@app.get("/download/<id>")
def download_file(id: str):
    """Download a file by its unique id."""
    index = cleanup_expired_files(load_index())
    save_index(index)

    record = index.get(id)
    if not record:
        return jsonify({"status": "error", "message": "ID invalide ou fichier expiré."}), 404

    file_path = Path(record.get("path", ""))
    if not file_path.exists():
        index.pop(id, None)
        save_index(index)
        return jsonify({"status": "error", "message": "Fichier introuvable."}), 404

    return send_file(file_path, as_attachment=True, download_name=record.get("filename", file_path.name))


@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
