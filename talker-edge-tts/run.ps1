param(
    [ValidateRange(1, 65535)][int]$Port = 8072,
    [ValidateNotNullOrEmpty()][string]$Voice = "ka-GE-EkaNeural",
    [switch]$Replace
)
$ErrorActionPreference = 'Stop'
docker image inspect edge-tts:local | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Image unavailable. Run build.ps1 first and check Docker is running.' }

$existing = docker container ls -a --filter 'name=^/edge-tts$' --format '{{.ID}}'
if ($LASTEXITCODE -ne 0) { throw 'Unable to check existing containers.' }
if ($existing) {
    if (-not $Replace) {
        throw 'Container edge-tts already exists. Use .\run.ps1 -Replace to recreate it from the current image.'
    }
    docker container rm --force edge-tts
    if ($LASTEXITCODE -ne 0) { throw 'Unable to remove the existing container.' }
}

docker run -d --name edge-tts --restart unless-stopped --init --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m,mode=1777 --env "EDGE_TTS_VOICE=$Voice" -p "127.0.0.1:${Port}:8080" edge-tts:local
if ($LASTEXITCODE -ne 0) { throw 'Container start failed. Check Docker, the image, port, and existing container name.' }
