# Automation System

This repository contains a set of microservices running in Docker containers.
They implement a simple pipeline for downloading videos, generating clips,
editing them and finally publishing to social networks or YouTube.

## Services

1. **service1** – download a video using `yt-dlp` with cookies and transcribe it
   with Whisper. Endpoint: `POST /download-transcribe`.
2. **service2** – cut a clip from a video. Endpoint: `POST /clip`.
3. **service3** – basic editing of a short video. Endpoint: `POST /edit`.
4. **service4** – stub for publishing short videos to multiple accounts.
   Endpoint: `POST /publish-short`.
5. **service5** – stub for publishing long videos. Endpoint: `POST /publish-long`.

All services return JSON responses so they can be easily consumed from tools
like **n8n**.

## Usage

Build and run the stack:

```bash
docker-compose build
docker-compose up
```

## Configuration

Before running the workflow, make sure the required credentials are available:

* **OpenAI API key** – set the `OPENAI_API_KEY` environment variable so that
  Whisper can access OpenAI's transcription service.
* **Airtable token** – provide your Airtable API token in the
  `AIRTABLE_TOKEN` environment variable. This is used when recording
  information about processed videos.
* **Cookies** – place your `cookies.txt` file at the repository root. It will
  be copied into the service containers as `/cookies.txt` for `yt-dlp`.
* **Publishing credentials** – the example services for uploading content are
  stubs. When implementing real publishing logic you will need API keys or
  login tokens for the target platforms (e.g. YouTube or social networks).

## Example n8n workflow

1. **HTTP Request** – call `service1` with `{ "videoUrl": "..." }`. Save
   `inputPath` and `segments`.
2. **HTTP Request** – call `service2` with `{ "inputPath": "input.mp4", "start": 0,
   "end": 60 }`. Save `clipPath`.
3. **HTTP Request** – call `service3` with `{ "inputPath": "clip.mp4" }`.
4. **HTTP Request** – call `service4` or `service5` to publish the result.

The output of each step can be used as input for the next one inside n8n.

## Environment collection

Run `./collect_env.sh` to gather information about your Docker and Python
setup. The script will create `env_report.tar.gz` which can be attached to
support requests.
