import os
import io
import json
import socket

HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", 1337))

def send_req(rfile: io.TextIOWrapper, wfile: io.TextIOWrapper, obj: dict) -> dict[str, list[dict[str, str]]]:
    wfile.write(json.dumps(obj) + "\n")
    wfile.flush()
    return json.loads(rfile.readline())

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        rfile = s.makefile("r", encoding="utf-8", newline="\n")
        wfile = s.makefile("w", encoding="utf-8", newline="\n")

        print(json.dumps(send_req(rfile, wfile, {"method": "OPTIONS"}), indent=2))

        while True:
            print()
            print("1. (g)et recent messages")
            print("2. (p)ost a message")
            print("3. (o)ptions again")
            print("4. (q)uit")

            choice = input("Choose an option: ").strip().lower()

            if choice == "g":
                resp = send_req(rfile, wfile, {"method": "GET"})
                if not resp.get("ok"):
                    print(resp)
                    continue

                print()
                for msg in resp["messages"]:
                    sender = msg.get("sender", "?")
                    date = msg.get("date", "?")
                    start = msg.get("start", "???")
                    content = msg.get("content", "")
                    print(f"{sender} ({date}) [{start}]: {content}")

            elif choice == "p":
                start = input("Enter 3-letter start (e.g. AAA): ").strip().upper()
                content = input("Enter encrypted message: ").strip()

                pd = { "method": "POST", "sender": "You", "start": start, "content": content}
                resp = send_req(rfile, wfile, pd)
                print(resp)

            elif choice == "o":
                print(json.dumps(send_req(rfile, wfile, {"method": "OPTIONS"}), indent=2))

            elif choice == "q": break

if __name__ == "__main__":
    main()