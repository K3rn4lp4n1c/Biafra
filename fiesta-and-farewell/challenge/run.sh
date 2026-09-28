#!/bin/sh
set -eu

if [ ! -x /usr/local/bin/blackbox ]; then
    echo "[run] blackbox binary missing or not executable" >&2
    exit 1
fi

if [ ! -f flag.txt ]; then
    if [ -z "${FLAG:-}" ]; then
        FLAG="CTF{REDACTED}"
    fi

    printf '%s\n' "$FLAG" > flag.txt
fi

if [ -z "${PORT:-}" ]; then
    PORT=1337
fi

exec socat \
    TCP-LISTEN:1337,fork,reuseaddr \
    EXEC:"blackbox archives",pty,stderr,setsid,sigint,sane