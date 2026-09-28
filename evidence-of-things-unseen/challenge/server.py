from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import RequestEntityTooLarge
from pathlib import Path

import os
import cv2
import py7zr

from helpers.imager import evaluate_invoice, read_image_from_upload
from helpers.utils import allowed_file

BASE_DIR = Path('/home')
ASSETS_DIR = BASE_DIR / "assets"
STATIC_DIR = BASE_DIR / "static"
TEMPLATE_DIR = BASE_DIR / "views"
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", 80))

TARGET_IMAGE_PATH = ASSETS_DIR / "target_invoice.png"
WORN_IMAGE_PATH = STATIC_DIR / "img" / "source_invoice.png"

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MiB

FLAG = os.getenv("FLAG", "CTF{REDACTED}")

app = Flask(
    __name__,
    template_folder=str(TEMPLATE_DIR),
    static_folder=str(STATIC_DIR),
)

app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE

@app.errorhandler(RequestEntityTooLarge)
def handle_large_upload(_):
    return jsonify({
            "error": "Uploaded file exceeds the 10 MiB limit.",
            "feedback": ["Use a smaller image and try again."],
        }), 413

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200

@app.post("/submit")
def submit():
    if "file" not in request.files:
        return jsonify({
                "error": "No file was provided.",
                "feedback": ["Attach an image file before submitting."],
            }), 400

    file_storage = request.files["file"]
    filename = (file_storage.filename or "").strip()

    if not filename:
        return jsonify({
                "error": "No filename was provided.",
                "feedback": ["Choose an image and try again."],
            }), 400

    if not allowed_file(filename):
        return jsonify({
                "error": "Unsupported file type.",
                "feedback": ["Use PNG, JPG, JPEG, or WEBP."],
            }), 400

    image = read_image_from_upload(file_storage)
    if image is None:
        return jsonify({
                "error": "The uploaded file could not be decoded as an image.",
                "feedback": ["Make sure the file is a valid image."],
            }), 400

    try:
        if not TARGET_IMAGE_PATH.is_file():
            raise RuntimeError(f"Missing target image at {TARGET_IMAGE_PATH}")
        if not WORN_IMAGE_PATH.is_file():
            raise RuntimeError(f"Missing worn image at {WORN_IMAGE_PATH}")
        TARGET_IMAGE = cv2.imread(str(TARGET_IMAGE_PATH))
        WORN_IMAGE = cv2.imread(str(WORN_IMAGE_PATH))
        if TARGET_IMAGE is None or WORN_IMAGE is None:
            raise RuntimeError("Server configuration error: missing target or worn image.")
        result = evaluate_invoice(image, TARGET_IMAGE, WORN_IMAGE, FLAG)
    except Exception as exc:
        app.logger.exception("Verification failure: %s", exc)
        return jsonify({
                "error": "The server failed while processing the invoice.",
                "feedback": ["Check the images and server logs, then try again."],
            }), 500

    return jsonify(result), 200

if __name__ == "__main__":
    password = os.getenv("ASSETS_PASSWORD")
    if password is None: raise RuntimeError("ASSETS_PASSWORD environment variable is not set.")
    with py7zr.SevenZipFile(ASSETS_DIR / "assets.7z", mode="r", password=password) as archive:
        archive.extractall(path=ASSETS_DIR)
    app.run(host=HOST, port=PORT)