import json
import os
import tempfile
import logging
from functools import wraps
from pathlib import Path
from subprocess import CalledProcessError, TimeoutExpired, run, PIPE

from flask import Flask, jsonify, make_response, render_template, request
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MiB
EXIFTOOL_TIMEOUT_SECONDS = 10

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "views"),
    static_folder=str(BASE_DIR / "static"),
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
app.logger.setLevel(logging.INFO)

TEST_ASSET = "flag"
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE

def log_req(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        client = request.headers.get("X-Forwarded-For", request.remote_addr)
        app.logger.info(f"-> {request.method} {request.full_path} from {client}")
        resp = make_response(f(*args, **kwargs))
        app.logger.info(f"<- {resp.status_code} {request.path}")
        return resp
    return wrapper

@app.errorhandler(RequestEntityTooLarge)
def handle_large_upload(e):
    return jsonify({"ok": False,"error": "Uploaded file exceeds the 50 MiB limit."}) , 413
    
@app.get("/")
@log_req
def index(): return render_template("index.html")

@app.post("/metadata")
@log_req
def metadata():
    if "file" not in request.files: return jsonify({"ok": False, "error": "Malformed request"}), 400

    file_storage = request.files["file"]
    if not file_storage.filename: return jsonify({"ok": False, "error": "Invalid file"}), 400
    
    path = file_storage.filename
    create_temp = False
    try:
        if TEST_ASSET not in path:
            path = secure_filename(file_storage.filename)
            _, ext = os.path.splitext(path)
            with tempfile.NamedTemporaryFile(delete=False, prefix="upload_", suffix=(ext or ""), dir=None) as tmp:
                create_temp = True  
                path = tmp.name
            file_storage.save(path)
    except Exception as e:
        app.logger.error(f"Error saving uploaded file: {str(e)}")
        os.remove(path) if create_temp and os.path.exists(path) else None
        return jsonify({"ok": False, "error": "Failed to save uploaded file."}), 500
    
    error_msg = None
    proc = None

    try:
        proc = run(
        f"exiftool -j {path}",
        stdout=PIPE,
        stderr=PIPE,
        shell=True,
        check=True,
        text=True,
        timeout=EXIFTOOL_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        error_msg = "Exiftool is not installed or not found in PATH."
    except TimeoutExpired:
        error_msg = f"Exiftool timed out after {EXIFTOOL_TIMEOUT_SECONDS} seconds."
    except CalledProcessError as exc:
        app.logger.error(f"Exiftool error. Stdout: {exc.stdout}, Stderr: {exc.stderr}")
        error_msg = "Exiftool failed to process the file."
    except Exception as exc:
        app.logger.error(f"Unexpected error running Exiftool: {str(exc)}")
        error_msg = "Unexpected error processing the file."
    finally:
        if create_temp and os.path.exists(path):
            try:
                os.remove(path)
            except Exception as exc:
                app.logger.warning(f"Failed to delete temporary file {path}: {str(exc)}")

    if error_msg is not None or proc is None:
        return jsonify({"ok": False, "error": error_msg}), 500

    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        app.logger.error(f"Error decoding Exiftool. Stdout: {proc.stdout}, Stderr: {proc.stderr}")
        return jsonify({"ok": False,"error": "Exiftool output is invalid",}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error parsing Exiftool output: {str(e)}.")
        return jsonify({"ok": False,"error": "Unexpected error parsing Exiftool output",}), 500
    
    is_image = False
    try:
        first = mime = None
        if isinstance(payload, list) and len(payload) > 0 and isinstance(payload[0], dict): first = payload[0]
        elif isinstance(payload, dict): first = payload

        if isinstance(first, dict): mime = first.get("MIMEType", "")
        if isinstance(mime, str) and mime.lower().startswith("image/"): is_image = True
    except Exception: is_image = False

    diagnostics = "Unavailable" if TEST_ASSET not in file_storage.filename else "Stable" if not is_image else "Unstable"
    return jsonify({"ok": True, "is_image": is_image, "diagnostics": diagnostics}), 200

@app.get("/health")
def health(): return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    with open(BASE_DIR / "flag", "w") as f: f.write(os.environ['FLAG'])
    os.environ.pop("FLAG", None)
    app.run(host="0.0.0.0", port=80)