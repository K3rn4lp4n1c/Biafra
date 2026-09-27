from pathlib import Path
import os
import py7zr
import shutil
import hashlib
import tempfile
import subprocess

BASE_DIR = Path(os.environ.get("BASE_DIR", Path(__file__).resolve().parent.parent))
ASSETS_DIR = BASE_DIR / "assets"

TEMPLATE_SOURCE = ASSETS_DIR / "client.7z"
TEMPLATE_C = BASE_DIR / "client.c"
TEMPLATE_H = BASE_DIR / "client.h"

def _decrypt_and_extract_templates():
    password = os.environ["PASSWORD"]
    if not TEMPLATE_SOURCE.is_file():
        print(f"[compile] missing client template archive {TEMPLATE_SOURCE}")
        return False

    try:
        with py7zr.SevenZipFile(TEMPLATE_SOURCE, mode='r', password=password) as archive:
            archive.extractall(path=BASE_DIR).env
        return True
    except Exception as e:
        print(f"[compile] failed to extract templates: {e}")
        return False

def _c_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )

def _build_fingerprint(enc_path: str, enc_key: str) -> str:
    h = hashlib.sha256()
    h.update(TEMPLATE_C.read_bytes())
    h.update(TEMPLATE_H.read_bytes())
    h.update(b"\x00")
    h.update(enc_path.encode("utf-8"))
    h.update(b"\x00")
    h.update(enc_key.encode("utf-8"))
    return h.hexdigest()

def compile_code(enc_path: str, enc_key: str, base: str) -> bool:
    if not isinstance(enc_path, str) or not enc_path: return False
    if not isinstance(enc_key, str) or not enc_key: return False

    if not TEMPLATE_C.is_file() or not TEMPLATE_H.is_file():
        if _decrypt_and_extract_templates(): TEMPLATE_SOURCE.unlink()
        if not TEMPLATE_C.is_file() or not TEMPLATE_H.is_file():
            print(f"[compile] missing client template files in {BASE_DIR}")
            return False

    target = ASSETS_DIR / "an-eastern-fisherman"

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    build_id = _build_fingerprint(enc_path, enc_key)
    build_id_file = target.with_name(f"{target.name}.buildid")

    # Reuse the current binary if it matches the current config + templates
    if target.is_file() and build_id_file.is_file():
        if build_id_file.read_text(encoding="utf-8").strip() == build_id:
            target.chmod(0o755)
            return True

    try:
        with tempfile.TemporaryDirectory(prefix="an-eastern-fisherman-build-") as tmp:
            tmpdir = Path(tmp)

            rendered_c = TEMPLATE_C.read_text(encoding="utf-8")
            rendered_h = TEMPLATE_H.read_text(encoding="utf-8")

            rendered_c = rendered_c.replace("{{ENCRYPTED_PATH}}", _c_escape(enc_path))
            rendered_c = rendered_c.replace("{{AES_KEY}}", _c_escape(enc_key))
            rendered_c = rendered_c.replace("{{SERVER_URL}}", _c_escape(base))

            tmp_c = tmpdir / "client.c"
            tmp_h = tmpdir / "client.h"
            out_bin = tmpdir / "an-eastern-fisherman"

            tmp_c.write_text(rendered_c, encoding="utf-8")
            tmp_h.write_text(rendered_h, encoding="utf-8")

            cmd = [
                "gcc", "-O2", "-rdynamic",
                "-o", str(out_bin), str(tmp_c), "-I", str(tmpdir),
                "-lcurl", "-lssl", "-lcrypto",
            ]

            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)

            if proc.returncode != 0:
                print("[compile] gcc failed")
                if proc.stdout: print(proc.stdout)
                if proc.stderr: print(proc.stderr)
                return False

            shutil.copy2(out_bin, target)
            target.chmod(0o755)
            build_id_file.write_text(build_id, encoding="utf-8")
            return True

    except Exception as exc:
        print(f"[compile] unexpected failure: {exc}")
        return False