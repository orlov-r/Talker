# Edge TTS Docker service

Standalone online Georgian speech synthesis using
[`edge-tts`](https://github.com/rany2/edge-tts). This is an alternative manual
speech service alongside [RHVoice/Natia](../talker-rhvoice/README.md).
It returns MP3 directly, without FFmpeg or WAV conversion.
The lesson app integrates MP3 playback. Compose runs two internal instances of
this image, configured for Eka and Giorgi. The first page selects either voice
or RHVoice/Natia, and the web app falls back to RHVoice if Edge fails. The speech
service itself keeps its fixed-voice request contract and has no fallback logic.

## Build and run

Run all commands from the repository root. Docker must be running Linux
containers; build scripts target Linux/amd64 and resolve the context from their
own directory. Internet access is required both to build and to synthesize.
No Microsoft account, Edge installation, or Azure key is required.

Windows PowerShell:

```powershell
.\talker-edge-tts\build.ps1
.\talker-edge-tts\run.ps1
```

Linux:

```sh
sh talker-edge-tts/build.sh
sh talker-edge-tts/run.sh
```

Continue only after the build succeeds. Open http://127.0.0.1:8072/ and click
**Read aloud**. The page accepts Georgian text and a speech rate, displays the
configured voice, and provides audio playback/replay. It is not the lesson UI.
Submitted text is sent to Microsoft's online service.

The image is `edge-tts:local`; the container is `edge-tts`. Default mapping:
`127.0.0.1:8072` to container port `8080`. The runtime uses UID/GID 65534,
a read-only filesystem, and a 64 MiB temporary `/tmp` mount. It exposes no
authentication or CORS; keep access on loopback or through a trusted SSH tunnel.

## Voice, port, and replacement

The default voice is `ka-GE-EkaNeural`. Use `ka-GE-GiorgiNeural` to compare a
male Georgian voice. Voice is a container setting, not a request field.

Windows, including explicit replacement of an existing container:

```powershell
.\talker-edge-tts\run.ps1 -Replace -Port 8072 -Voice ka-GE-GiorgiNeural
```

`-Replace` checks that the image exists before removing the old container.
Replacement interrupts requests and removes its logs. Without this switch an
existing container is preserved and the script reports an error.

Linux, after stopping/removing an existing container if necessary:

```sh
docker container rm --force edge-tts
PORT=8072 EDGE_TTS_VOICE=ka-GE-GiorgiNeural sh talker-edge-tts/run.sh
```

Only run the removal command when replacing an existing container. Rebuild and
recreate after runtime source or dependency changes. `requirements.txt` pins
`edge-tts`; transitive dependencies and the base-image tag are not fully pinned.
The build verifies the CLI loads, without making a synthesis request. Microsoft's
service can change independently of the pinned Python package.

## HTTP API and checks

```powershell
curl.exe --fail http://127.0.0.1:8072/health
curl.exe --fail http://127.0.0.1:8072/synthesize -H "Content-Type: application/json" --data-binary "@talker-edge-tts/sample.json" --output edge-hello.mp3
```

On Linux use `curl` instead of `curl.exe`. Listen to `edge-hello.mp3` to verify
pronunciation; health does not check Microsoft connectivity or fresh synthesis.

`GET /health` returns `{"status":"ok","voice":"ka-GE-EkaNeural"}` for the
default configuration. `POST /synthesize` accepts:

```json
{"text":"გამარჯობა! როგორ ხარ?","rate":100}
```

- `text`: nonempty string, up to 3000 characters.
- `rate`: optional integer 50–200, default 100. Converted to Edge's relative
  percentage: 80 becomes `-20%`, 100 becomes `+0%`, 120 becomes `+20%`.
- Body: JSON object, with `Content-Length` of 1–32768 bytes.
- Success: HTTP 200, `Content-Type: audio/mpeg`, nonempty MP3 up to 4 MiB.
- Invalid JSON/fields: 400; body size outside bounds: 413; unknown routes: 404.
- Synthesis failure or empty/oversized output: 500; 60-second synthesis timeout:
  504. Errors return `{"error":"message"}` without upstream diagnostic details.

Requests are serialized. There is no application retry loop, cache, persistent
storage, or guaranteed request-per-minute quota. Temporary input and audio files
are deleted on success and failure; the subprocess is killed on timeout.
Nonempty output is size-checked but not decoded to validate MP3 frames.
Frequent requests may be throttled; failures can also result from Microsoft
protocol changes. See the [upstream rate-limit discussion](https://github.com/rany2/edge-tts/issues/201).

## Validation

Run the committed HTTP tests from the repository root, without external services:

```sh
python -m unittest discover -s talker-edge-tts -p test_server.py -v
```

These tests simulate the synthesis subprocess and cover validation, status and
content type, voice/rate forwarding, errors, timeouts, output bounds, and temporary
cleanup. They do not prove valid MP3 decoding, real synthesis, or pronunciation.
For real validation, build/start the image, run both HTTP commands above, and
listen. Generated MP3s and image archives must not be committed.

In this workspace the simulated HTTP tests, PowerShell/Linux shell syntax
checks, and test-page JavaScript syntax check passed. The image built with
`edge-tts` 7.3.1; the non-root, read-only container passed `/health` and real
synthesis of `sample.json`, returning HTTP 200 with `audio/mpeg` and 20,448 bytes.
Pronunciation and audible playback still need listening validation.
