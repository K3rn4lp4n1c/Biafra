#!/bin/bash

set -eu

NAME="shell-shocked"

docker rm -f "$NAME" >/dev/null 2>&1 || true
docker build --no-cache --pull --tag="$NAME:latest" .

PUSH=false
while getopts "p" opt; do
  case $opt in
    p)
      PUSH=true
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      exit 1
      ;;
  esac
done

if [ "$PUSH" = true ]; then
  docker push "$NAME:latest" "k3rn4lpanic/$NAME:latest"
fi