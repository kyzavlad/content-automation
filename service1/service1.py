from flask import Flask, request, jsonify
import subprocess
import json
import logging
import os

app = Flask(__name__)

FFMPEG_BIN = os.getenv('FFMPEG_PATH', '/usr/bin/ffmpeg')
os.environ['PATH'] = os.path.dirname(FFMPEG_BIN) + ':' + os.environ.get('PATH', '')

DATA_DIR = '/data'
os.makedirs(DATA_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

def run(cmd: str) -> str:
    """Run shell command and return stdout or raise error with details."""
    logger.info("Running command: %s", cmd)
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if proc.returncode != 0:
        logger.error("Command failed with exit code %s: %s\nstdout:\n%s\nstderr:\n%s",
                     proc.returncode, cmd, proc.stdout, proc.stderr)
        raise RuntimeError(f"Command `{cmd}` failed: {proc.stderr.strip()}")
    logger.info("Command succeeded: %s", cmd)
    return proc.stdout

@app.route('/health', methods=['GET'])
def health():
    return jsonify(status='ok')

@app.route('/download-transcribe', methods=['POST'])
def download_transcribe():
    try:
        data = request.get_json(force=True)
        url = data.get('videoUrl')
        if not url:
            return jsonify(error="Missing 'videoUrl'"), 400

        logger.info(f"Received request to process: {url}")
        # Example: simulate download and transcription
        fake_transcript = "This is a fake transcript for testing."
        fake_segments = [{"start": 0, "end": 10, "text": "Segment 1"}]

        return jsonify({
            "inputPath": "/data/fake_path.mp4",
            "transcript": fake_transcript,
            "segments": fake_segments
        })
    except Exception as e:
        logger.exception("Failed to process video")
        return jsonify(error=str(e)), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3001)
