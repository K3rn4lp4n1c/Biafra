from enigma.machine import EnigmaMachine
from pathlib import Path

import os
import io
import json
import py7zr
import socket
import random
import string
import asyncio

HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", 1337))

FLAG = f"I heard you were looking for me. Here is the flag: {os.getenv('FLAG', 'CTF{REDACTED}')}"
HELP = "Stop spamming the chat and look at the chat history! My juniors and I don't have a flag"
ASSETS_DIR = Path(__file__).parent / "assets"
ASSETS_DIR.parent.mkdir(parents=True, exist_ok=True)
BOT_CHAT_FILE = Path(__file__).parent / "assets" / "bot_chat.txt"

BOT_SENDERS = {"quartermaster", "signals", "courier-3", "clerk", "aide", "general"}
FLAG_KEYWORDS = [kw.strip().lower() for kw in os.environ["FLAG_KEYWORDS"].split(",") if kw.strip()]

def rand_start():
    return "".join(random.choice(string.ascii_uppercase) for _ in range(3))

def encrypt_message(machine: EnigmaMachine, message: str, start: str) -> str:
    machine.set_display(start)
    return machine.process_text(message)

def decrypt_message(machine: EnigmaMachine, ciphertext: str, start: str) -> str:
    machine.set_display(start)
    return machine.process_text(ciphertext)

def send_req(rfile: io.TextIOWrapper, wfile: io.TextIOWrapper, obj: dict) -> dict:
    wfile.write(json.dumps(obj) + "\n")
    wfile.flush()
    return json.loads(rfile.readline())

def load_bot_chat(machine: EnigmaMachine, symbols: dict) -> list[dict[str, str]]:
    password = os.getenv("ASSETS_PASSWORD")
    if password is None: raise RuntimeError("ASSETS_PASSWORD environment variable is not set.")
    with py7zr.SevenZipFile(ASSETS_DIR / "assets.7z", mode="r", password=password) as archive:
        archive.extractall(path=BOT_CHAT_FILE.parent)
    if not BOT_CHAT_FILE.exists(): raise FileNotFoundError(f"Bot chat file not found: {BOT_CHAT_FILE}")
    with open(BOT_CHAT_FILE, "r", encoding="utf-8") as f:
        pds: list[dict[str, str]] = []
        for line in f:
            line = line.strip()
            if not line: continue

            sender, content = line.split(": ", 1)
            start = rand_start()
            content = content.strip().format(**symbols)
            if not sender or not content or not start: continue
            encrypted = encrypt_message(machine, content, start)

            pd = {"method": "POST", "sender": sender, "start": start, "content": encrypted}
            pds.append(pd)
        return pds

async def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        rfile = s.makefile("r", encoding="utf-8", newline="\n")
        wfile = s.makefile("w", encoding="utf-8", newline="\n")

        resp = send_req(rfile, wfile, {"method": "OPTIONS"})
        if not resp.get("ok"): raise RuntimeError(f"Failed to get options: {resp}")
        keysheet = resp["keysheet"]
        machine = EnigmaMachine.from_key_sheet(**keysheet)
        symbols: dict = {
            'KEYSHEET': keysheet,
            "GENERAL": {
                "title": "General", "salute": "Biafra Kwenu",
                "address": "General Sir", "language": "English",
            },

            "PROTOCOL": {
                "options_command": "OPTIONS",
                "request_style": "one short line",
            }
        }
        bots_convo = load_bot_chat(machine, symbols)
        seen: set[tuple[str, str, str]] = set()
        

        while True:
            for pd in bots_convo:
                await asyncio.sleep(random.uniform(1, 5))
                resp = send_req(rfile, wfile, pd)
                if resp.get("ok"): seen.add((pd["sender"], pd["content"], pd["start"]))

                resp = send_req(rfile, wfile, {"method": "GET"})
                if not resp.get("ok"): continue
                messages: list[dict[str, str]] = resp.get("messages", [])

                for msg in messages:
                    sender = msg.get("sender", "")
                    content = msg.get("content", "")
                    start = msg.get("start", "")

                    key = (sender, content, start)
                    if key in seen: continue
                    seen.add(key)

                    if len(start) != 3 or not start.isalpha(): continue

                    if sender.lower() in BOT_SENDERS: continue
                    try: plaintext = decrypt_message(machine, content, start)
                    except Exception: continue
                    reply_start = rand_start()
                    win = all(kw in plaintext.lower() for kw in FLAG_KEYWORDS)
                    reply, addresser = (FLAG, "General") if win else (HELP, "Quartermaster")
                    reply_cipher = encrypt_message(machine, reply, reply_start)

                    send_req(rfile, wfile, {
                        "method": "POST",
                        "sender": addresser,
                        "start": reply_start,
                        "content": reply_cipher
                    })
            bots_convo = load_bot_chat(machine, symbols)  # Reloads allow for dynamic updates

if __name__ == "__main__":
    asyncio.run(main())