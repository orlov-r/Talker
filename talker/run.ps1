param([ValidateRange(1, 65535)][int]$Port = 8071)
$ErrorActionPreference = 'Stop'
docker run -d --name rhvoice-natia --restart unless-stopped --init --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m,mode=1777 -p "127.0.0.1:${Port}:8080" rhvoice-natia:local
if ($LASTEXITCODE -ne 0) { throw 'Container start failed. Check Docker, the image, port, and existing container name.' }
