param([ValidateNotNullOrEmpty()][string]$Ref = 'master')
$ErrorActionPreference = 'Stop'
$engine = docker info --format '{{.OSType}}'
if ($LASTEXITCODE -ne 0) { throw 'Docker is unavailable. Start Docker Desktop.' }
if ($engine -ne 'linux') { throw 'Docker must use Linux containers.' }
docker build --platform linux/amd64 --build-arg "RHVOICE_REF=$Ref" -t rhvoice-natia:local $PSScriptRoot
if ($LASTEXITCODE -ne 0) { throw 'Image build failed.' }
