# Video Automation System

This repository contains a collection of small Flask services used in a single n8n workflow. The goal is to automate downloading a long video, splitting it into short clips, editing and finally publishing on multiple accounts.

## Requirements
- Docker and docker-compose
- A running n8n instance
- `.env` file with API keys (see `api-keys.env` for the list)

## Installation
1. Clone this repository.
2. Copy `api-keys.env` to `.env` and fill in all placeholders.
3. Add account details in `accounts-config.json`.
4. Build and start the services:
   ```bash
   docker-compose build
   docker-compose up -d
   ```
## Configuration
Create a `.env` file based on `api-keys.env` and provide the following variables:
- `OPENAI_API_KEY` – used by service1 for transcription.
- `AIRTABLE_API_KEY` – Airtable access token.
- `AIRTABLE_BASE_ID` and `AIRTABLE_TABLE_ID` – IDs of your base and table.
- `YOUTUBE_API_KEY` – for publishing videos.
- Place your authenticated browser cookies in `cookies.txt`; the file is copied into service1.

## Services
| Service  | Endpoint & Port              | Purpose |
|---------|------------------------------|---------|
| **service1** | `POST /download-transcribe` on port **3001** | Downloads a video using `yt-dlp` (with `cookies.txt`) and transcribes it via Whisper. |
| **service2** | `POST /clip-video` on port **3002** | Cuts viral moments from the long video. |
| **service3** | `POST /edit-shorts` on port **3003** | Adds subtitles, music and fades to clips. |
rz9aqm-codex/настройка-автоматизации-контента-и-сервисов-на-сервере
| **service4** | `POST /publish-shorts` on port **3004** | Publishes edited clips to TikTok, Instagram, YouTube Shorts, Facebook and X. |
=======
| **service4** | `POST /publish-shorts` on port **3004** | Publishes edited clips to TikTok, Instagram, YouTube Shorts and X. |
main
| **service5** | `POST /publish-long` on port **3005** | Publishes the full video on YouTube. |

The containers `service1`, `service2` and `service3` share the volume `media_data` mounted to `/data` so that intermediate files are accessible between them.

## n8n workflow
Import `workflow.json` into n8n and connect each node to the credentials you created. The workflow expects the following tools:

1. **Get Content Database** – Airtable search
   - Base: `appLSGPYXB4dTJiay`
   - Table: `tblXJe5tLOcKXpPLT`
   - Filter By Formula: `{{ $fromAI('Filter_By_Formula', '', 'string') }}`
2. **Update Text Info Database** – Airtable update
   - Columns: `id`, `Title`, `Description`, `Script`, `Status` (values from `$fromAI()`)
3. **Update Clips Database** – Airtable create
   - Column `Clips`: `{{ $fromAI('clips') }}`
4. **Transcribe and Download Video** – HTTP POST
   - URL: `http://165.227.84.254:3001/download-transcribe`
   - Headers: `{ "Content-Type": "application/json" }`
   - Body: `{ "videoUrl": "{{ $fromAI('videoUrl', '', 'string') }}" }`
5. **Clip Long Video** – HTTP POST
   - URL: `http://165.227.84.254:3002/clip-video`
   - Body: `{ "inputPath": "{{$json.inputPath}}", "segments": "{{$json.segments}}" }`
6. **Edit Shorts Video** – HTTP POST
   - URL: `http://165.227.84.254:3003/edit-shorts`
   - Body:
     ```json
     {
       "clips": "{{$json.clips}}",
       "metadata": {
         "title": "{{$json.title}}",
         "hashtags": "{{$json.hashtags}}"
       }
     }
     ```
7. **Publish Shorts** – HTTP POST
   - URL: `http://165.227.84.254:3004/publish-shorts`
   - Body: `{ "clips": "{{ $json.clips }}", "titles": "{{ $json.titles }}" }`
8. **Publish Long** – HTTP POST
   - URL: `http://165.227.84.254:3005/publish-long`
   - Body: `{ "video": "{{ $json.video }}", "seo_variations": "{{ $json.seo_variations }}" }`

The agent prompt used in the workflow is stored in `ai-agent-prompt.txt` and `agent-system-prompt.txt`. Paste the contents into the AI Agent node's system message field.

### Airtable table
The table `Content Base` in Airtable contains the following fields:
- **ID** – record identifier
- **Post URL** – link to the source video
- **Title** – title of the video
- **Description** – long description
- **Script** – transcript text
- **Video** – attachment (not used by services)
- **Clips** – array of produced clip metadata
- **Status** – current workflow status

## Example scenarios
The agent handles three main scenarios:
1. **Transcription only** – fetch a record, transcribe the video and update Status to `transcribed`.
2. **Shorts workflow** – download, transcribe, generate clips, edit the first clip, create viral titles, publish it and store the rest of the clips in Airtable.
3. **Publish long video** – ensure transcript exists, generate SEO metadata, then publish the long video to ten YouTube accounts.

## Environment collection
Run `./collect_env.sh` to produce `env_report.tar.gz` with Docker and Python info if you need to troubleshoot the setup.
rz9aqm-codex/настройка-автоматизации-контента-и-сервисов-на-сервере
main
