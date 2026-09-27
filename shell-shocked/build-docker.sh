#!/bin/bash

set -eu

NAME="shell-shocked"
USER="k3rn4lp4n1c"

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
  docker login
  docker tag "$NAME:latest" "$USER/$NAME:latest"
  docker push "$USER/$NAME:latest"
fi