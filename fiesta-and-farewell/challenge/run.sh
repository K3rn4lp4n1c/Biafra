#!/bin/sh
set -eu

if [ ! -x /usr/local/bin/blackbox ]; then
    echo "[run] blackbox binary missing or not executable" >&2
    exit 1
fi

if [ ! -f flag.txt ]; then
    if [ -z "${FLAG:-}" ]; then
        echo "[run] FLAG variable is not set in container" >&2
        exit 1
    fi

    printf '%s\n' "$FLAG" > flag.txt
fi

exec socat \
    TCP-LISTEN:1337,fork,reuseaddr \
    EXEC:"blackbox archives",pty,stderr,setsid,sigint,sane