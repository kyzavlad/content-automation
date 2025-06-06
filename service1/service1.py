from flask import Flask, request, jsonify
import subprocess
import json
import logging

app = Flask(__name__)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


def run(cmd: str) -> str:
    """Run shell command and return stdout or raise error with details."""
    logger.info("Running command: %s", cmd)
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if proc.returncode != 0:
        logger.error(
            "Command failed with exit code %s: %s\nstdout:\n%s\nstderr:\n%s",
            proc.returncode,
            cmd,
            proc.stdout,
            proc.stderr,
        )
        raise RuntimeError(
            f"Command `{cmd}` failed with exit code {proc.returncode}. "
            f"{proc.stderr.strip()}"
        )
    logger.info("Command succeeded: %s", cmd)
    return proc.stdout

@app.route('/download-transcribe', methods=['POST'])
def download_transcribe():
    try:
        data = request.get_json(force=True)
        url = data.get('videoUrl')
        if not url:
            return jsonify(error="Missing 'videoUrl'"), 400

        # 1) Скачиваем видео с куками
        run(f'yt-dlp --cookies /cookies.txt -o input.mp4 "{url}"')

        # 2) Транскрибируем через Whisper
        run('whisper input.mp4 --model small --output_format json --output transcript.json')

        # 3) Читаем результат и возвращаем
        out = json.load(open('transcript.json'))
        return jsonify({
            'transcript': out.get('text'),
            'segments':   out.get('segments'),
            'inputPath':  'input.mp4'
        })
    except Exception as e:
        logger.exception("Internal error")
        return jsonify(error=str(e)), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3001)
