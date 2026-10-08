#!/bin/sh
set -eu
port=${PORT:-8071}
case "$port" in
    ''|*[!0-9]*) echo 'PORT must be an integer from 1 to 65535.' >&2; exit 1 ;;
esac
if [ "${#port}" -gt 5 ] || [ "$port" -lt 1 ] || [ "$port" -gt 65535 ]; then
    echo 'PORT must be an integer from 1 to 65535.' >&2
    exit 1
fi
docker run -d --name rhvoice-natia --restart unless-stopped --init --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m,mode=1777 -p "127.0.0.1:$port:8080" rhvoice-natia:local
