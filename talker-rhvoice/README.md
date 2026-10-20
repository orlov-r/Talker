# RHVoice / Natia Docker service

Offline Georgian text-to-speech using RHVoice and the Natia voice.
The HTTP service accepts text and returns WAV audio.

This directory contains the speech service and its manual browser test page.
For project status and the implemented lesson web app, see the
[project README](../README.md) and [architecture](../docs/architecture.md).
Commands in this document assume the working directory is `talker-rhvoice/`, unless
otherwise stated.

## Requirements

- Docker running Linux containers.
- Linux/amd64 target architecture.
- Windows: Docker Desktop in Linux-container mode.
- Ubuntu server: Docker Engine; version 26.1.3 is sufficient.
- Internet access during the image build.
- Available host port, default: 8071.
- curl for testing.
- SSH/SCP for transferring the image to another machine.

Buildx is not required. Python, compilers, and RHVoice do not need
to be installed on the host.

Synthesis works offline after the image is built.

## Expected files

Place these files together in the project directory:

- Dockerfile — multi-stage image build and synthesis check.
- .dockerignore — excludes unnecessary build-context files.
- server.py — HTTP API using Python's standard library.
- index.html — browser testing page with text entry and audio playback.
- build.ps1 — Windows image-build script.
- run.ps1 — Windows container-start script.
- build.sh — Linux image-build script.
- run.sh — Linux container-start script.
- sample.json — sample Georgian synthesis request.
- README.md — this document.

These files must exist before running the steps below.
Generated files include hello.wav and rhvoice-natia.tar.
The build scripts only build the image; export it with `docker save`
as shown below. Scripts resolve the build context from their own directory.
On Windows, use `run.ps1 -Replace` to remove an existing container before
starting a replacement. The Linux run script requires manual removal.

## Build on Windows

Open PowerShell in the project directory:

```powershell
docker info --format '{{.OSType}}'
.\build.ps1
```

The first command must report `linux`.

Alternatively, build without the script:

```powershell
docker build --platform linux/amd64 -t rhvoice-natia:local .
```

The Dockerfile's build check synthesizes a Georgian phrase with Natia
and verifies that the resulting WAV contains audio.

## Run and test on Windows

After starting the container, open http://127.0.0.1:8071/ in a browser.
The testing page starts with the sample Georgian text. Edit it and click
**Read aloud** to synthesize and play it with Natia. Audio controls allow
replay, including when the browser requires a separate click to play.
The page uses the existing `/synthesize` API and needs no internet access.
Rebuild the image and recreate the container to include project changes.

To update an existing Windows installation, run these commands in order
(continue only if the build succeeds):

```powershell
.\build.ps1
.\run.ps1 -Replace -Port 8071
```

`-Replace` removes the existing container (running or stopped) and starts
a new one using `rhvoice-natia:local`. The script checks that the image
exists before removal. Replacement interrupts current requests and removes
the old container's logs. Images are retained; no image deletion is needed.

```powershell
.\run.ps1 -Port 8071

curl.exe --fail http://127.0.0.1:8071/health

curl.exe --fail http://127.0.0.1:8071/synthesize -H "Content-Type: application/json" --data-binary "@sample.json" --output hello.wav
```

Expected health response:

```json
{"status":"ok","voice":"Natia"}
```

Play hello.wav and check that the Georgian speech is audible.

Example sample.json:

```json
{"text":"გამარჯობა! როგორ ხარ?","rate":100}
```

The rate parameter is optional and accepts integers from 50 to 200.
Text must be nonempty and contain at most 3000 characters.
Requests must be JSON objects with a Content-Length of 1–32768 bytes.
Invalid JSON or fields return HTTP 400; invalid body sizes return 413.
Synthesis failures return 500, and a 60-second synthesis timeout returns 504.
Requests are processed one at a time. `/health` reports that the HTTP
server is running; it does not perform a new synthesis check.

## Transfer the image to Ubuntu

On Windows, replace SERVER with the server hostname or IP:

```powershell
docker save -o rhvoice-natia.tar rhvoice-natia:local
scp rhvoice-natia.tar main@SERVER:~/
scp run.sh sample.json main@SERVER:~/
```

On Ubuntu:

```sh
sudo docker load -i ~/rhvoice-natia.tar
cd ~
sudo sh run.sh
```

Alternatively, copy the project directory to Ubuntu and build there:

```sh
sudo sh build.sh
sudo sh run.sh
```

## Test on Ubuntu

From the directory containing sample.json:

```sh
curl --fail http://127.0.0.1:8071/health

curl --fail http://127.0.0.1:8071/synthesize \
  -H 'Content-Type: application/json' \
  --data-binary @sample.json \
  --output hello.wav

file hello.wav
sudo docker logs rhvoice-natia
sudo docker image ls rhvoice-natia
```

Copy hello.wav to your PC to listen:

```powershell
scp main@SERVER:~/hello.wav .
```

## Ports and remote access

The service listens on port 8080 inside the container.
The default host mapping is:

```text
127.0.0.1:8071 → container:8080
```

Change the host port without rebuilding:

Windows:

```powershell
.\run.ps1 -Replace -Port 8072
```

Linux:

```sh
sudo env PORT=8072 sh run.sh
```

On Linux, if the container already exists, stop and remove it before
starting with the new mapping:

```sh
sudo docker stop rhvoice-natia
sudo docker rm rhvoice-natia
```

On Windows, omit sudo.

To access the server through an SSH tunnel, run on Windows:

```powershell
ssh -N -L 8071:127.0.0.1:8071 main@SERVER
```

Keep the tunnel open and use http://127.0.0.1:8071 on your PC.
Do not run a local container on the same host port simultaneously.

The API has no authentication or CORS support. Its default mapping
allows access only through the host's loopback interface.

## Image size and reproducibility

The multi-stage build keeps compilers and Git out of the final image.
Only Georgian/Natia language and voice data are installed.

Inspect the actual image size after building:

```sh
docker image ls rhvoice-natia
docker history rhvoice-natia:local
```

The default RHVoice source ref is master. To fix the source version:

Windows:

```powershell
.\build.ps1 -Ref COMMIT
```

Linux:

```sh
sudo env RHVOICE_REF=COMMIT sh build.sh
```

Replace COMMIT with an RHVoice commit hash.
For fully fixed build inputs, pin the base-image digests as well.

## License and validation status

RHVoice flags its Georgian language data as non-free. Review the
language and Natia voice license terms before commercial use or
redistribution.

Upstream: https://github.com/RHVoice/RHVoice
Natia license: https://github.com/RHVoice/RHVoice/blob/master/doc/en/License.md#natia

PowerShell and Linux shell scripts passed syntax checks. Local HTTP checks
passed for health, request validation, WAV responses, synthesis failures,
and timeouts using a simulated synthesizer.

The Docker image build and real Natia synthesis have not been validated
in this workspace because the Docker Linux engine was not running.
A successful build checks synthesis; listening to hello.wav remains
necessary to assess pronunciation and quality.
