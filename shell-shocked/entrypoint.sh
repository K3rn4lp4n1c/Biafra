#!/bin/sh

echo $FLAG > /home/flag
exec gosu ctf:ctf "$@"