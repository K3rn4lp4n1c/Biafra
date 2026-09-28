from datetime import datetime, timezone
from collections import deque

import json
import os
import socket
import random
import string
import threading

letters = random.sample(string.ascii_uppercase, 20)

KEYSHEET = {
    "rotors": " ".join(random.sample(["I", "II", "III", "IV", "V"], 3)),
    "reflector": random.choice(["B", "C"]),
    "ring_settings": " ".join(str(random.randint(1, 26)) for _ in range(3)),
    "plugboard_settings": " ".join(
        letters[i] + letters[i + 1]
        for i in range(0, 20, 2)
    )
}
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 1337))
MAX_MESSAGES = 100

messages = deque(maxlen=MAX_MESSAGES)
messages_lock = threading.Lock()

def options() -> dict:
    return {
        "ok": True,
        "commands": {
            "GET": "Retrieve all stored messages exactly as posted",
            "POST": "Post a message with sender, start, and content",
            "OPTIONS": "Show protocol help"
        },
        "keysheet": KEYSHEET, 
        "protocol": {
            "framing": "newline-delimited JSON",
            "post_fields": ["method", "sender", "start", "content"],
            "start_format": "exactly 3 uppercase letters A-Z",
            "note": "Messages are stored and returned exactly as posted. The service does not encrypt or decrypt content."
        }
    }

def get_messages() -> dict[str, bool|list[dict[str, str]]]:
    with messages_lock: return {"ok": True, "messages": list(messages)}

def post_message(payload: dict[str, str]) -> dict[str, str|bool]:
    sender = str(payload.get("sender", "")).strip()
    content = str(payload.get("content", "")).strip()
    start = str(payload.get("start", "")).strip().upper()

    if not sender or not content or not start:
        return {"ok": False, "error": "sender, start, and content are required"}

    if len(start) != 3 or not start.isalpha():
        return {"ok": False, "error": "start must be exactly 3 letters A-Z"}

    msg = {
        "date": datetime.now(timezone.utc).isoformat(),
        "sender": sender,
        "start": start,
        "content": content,
    }

    with messages_lock: messages.append(msg)

    return {"ok": True}

def resolve_line(line: str) -> dict:
    try:
        req: dict[str, str] = json.loads(line)
        method = str(req.get("method", "")).upper()

        if method == "GET": return get_messages()
        elif method == "POST": return post_message(req)
        elif method == "OPTIONS": return options()
        else: return {"ok": False, "error": f"unknown method: {method}"}
    except json.JSONDecodeError:
        return {"ok": False, "error": "invalid json"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def handle_client(conn: socket.socket, addr):
    print(f"Connected by {addr}")
    try:
        rfile = conn.makefile("r", encoding="utf-8", newline="\n")
        wfile = conn.makefile("w", encoding="utf-8", newline="\n")

        for line in rfile:
            line = line.strip()
            if not line: continue

            resp = resolve_line(line)
            wfile.write(json.dumps(resp) + "\n")
            wfile.flush()

    except BrokenPipeError:
        print(f"Connection with {addr} closed")
    except Exception as e:
        print(f"Error with {addr}: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        print(f"Listening on {HOST}:{PORT}")

        while True:
            conn, addr = s.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()

if __name__ == "__main__":
    main()