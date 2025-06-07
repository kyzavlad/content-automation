# Video Automation System

This repository contains a group of small Flask services that together form a video processing pipeline.  The workflow is controlled from n8n: a user supplies only a record ID from Airtable and the system handles downloading the source video, clipping it, editing the clips and publishing both short and long versions across many social‑media accounts.

## Requirements
- Docker and docker-compose
- A running n8n instance
- `.env` file with API keys (see `api-keys.env` for the list)

## Installation
1. Clone this repository.
2. Copy `api-keys.env` to `.env` and fill in all placeholders.
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

### accounts-config.json
The file `accounts-config.json` stores login data for all platforms.  It contains five sections – `tiktok`, `instagram`, `youtube`, `facebook` and `x`.  Each section lists ten account placeholders of the form:

```json
{
  "id": "platform_1",
  "username": "ЗАПОЛНИТЬ",
  "password": "ЗАПОЛНИТЬ",
  "cookies": "ЗАПОЛНИТЬ"
}
```
Replace the fields with real credentials and exported cookies for each account.

## Services
| Service  | Endpoint & Port              | Purpose |
|---------|------------------------------|---------|
| **service1** | `POST /download-transcribe` on port **3001** | Downloads a video using `yt-dlp` (with `cookies.txt`) and transcribes it via Whisper. |
| **service2** | `POST /clip-video` on port **3002** | Cuts viral moments from the long video. |
| **service3** | `POST /edit-shorts` on port **3003** | Adds subtitles, music and fades to clips. |
| **service4** | `POST /publish-shorts` on port **3004** | Publishes edited clips to TikTok, Instagram, YouTube Shorts, Facebook and X. |
| **service5** | `POST /publish-long` on port **3005** | Publishes the full video on YouTube. |

The containers `service1`, `service2` and `service3` share the volume `media_data` mounted to `/data` so that intermediate files are accessible between them.

## n8n workflow
Recreate the workflow in n8n using these node settings.  Each HTTP node uses `POST` with JSON bodies and should point at the corresponding service URL.

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

### Agent prompt
Use the following text in the *System Message* field of the AI Agent node. It describes the tools and how to orchestrate them:

```
You control eight tools to move a video from download to multi‑platform publishing:
1. Get Content Database – fetch records from Airtable
2. Update Text Info Database – store transcript and status
3. Update Clips Database – store clip metadata
4. Transcribe and Download Video – download & transcribe
5. Clip Long Video – cut viral moments
6. Edit Shorts Video – add captions, music and transitions
7. Publish Shorts – upload to TikTok, Instagram, YouTube Shorts, Facebook and X
8. Publish Long – upload the full video to YouTube

Typical commands:
* "transcribe video recXXX" – only download and transcribe
* "process video recXXX for shorts" – complete short‑form pipeline
* "publish long video recXXX" – upload the full version

Always describe which step you are running, show the data being passed and state the next action.
```

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

## Running the system
1. Ensure `.env` contains your API keys and that `accounts-config.json` lists 10 accounts for each platform.
2. Build and start the containers:
   ```bash
   docker-compose build
   docker-compose up -d
   ```
3. Open your n8n instance and recreate the workflow using the settings above.  In each node specify the credentials you created (Airtable token, OpenAI key, etc.).
4. In the AI Agent node paste the prompt text from this README into the System Message field.
5. Trigger the workflow by sending a chat message such as:
   `process video recXXXXXXXXXXXX for shorts`
6. Monitor container logs with `docker-compose logs -f` if troubleshooting is needed.

After pushing updates run on the server:
```bash
git fetch && git reset --hard origin/main
docker-compose build && docker-compose up -d
```
Then check the transcription service with:
```bash
curl -X POST http://localhost:3001/download-transcribe \
  -H 'Content-Type: application/json' \
  -d '{"videoUrl": "https://example.com/video.mp4"}'
```
