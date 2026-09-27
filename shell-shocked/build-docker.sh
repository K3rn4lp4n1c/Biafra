#!/bin/bash

set -eu

NAME="shell-shocked"
CAMPAIGN="biafra"
USER="k3rn4lp4n1c"

docker rm -f "$CAMPAIGN:$NAME" >/dev/null 2>&1 || true
docker build --no-cache --pull --tag="$CAMPAIGN:$NAME" .

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
  docker tag "$CAMPAIGN:$NAME" "$USER/$CAMPAIGN:$NAME"
  docker push "$USER/$CAMPAIGN:$NAME"
fi