from flask import Flask, request, jsonify
import subprocess, json, traceback, os

FFMPEG_BIN = os.getenv('FFMPEG_PATH', '/usr/bin/ffmpeg')
os.environ['PATH'] = os.path.dirname(FFMPEG_BIN) + ':' + os.environ.get('PATH', '')

app = Flask(__name__)

DATA_DIR = '/data'
os.makedirs(DATA_DIR, exist_ok=True)

def run(cmd):
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if proc.returncode != 0:
        raise Exception(f"Command `{cmd}` failed:\n{proc.stderr.strip()}")
    return proc.stdout

@app.route('/download-transcribe', methods=['POST'])
def download_transcribe():
    try:
        data = request.get_json(force=True)
        url = data.get('videoUrl')
        if not url:
            return jsonify(error="Missing 'videoUrl'"), 400

        # 1) Скачиваем видео (поддержка Google Drive через gdown)
        input_file = os.path.join(DATA_DIR, 'input.mp4')
        transcript_file = os.path.join(DATA_DIR, 'transcript.json')
        if 'drive.google.com' in url:
            run(f'gdown --fuzzy -O "{input_file}" "{url}"')
        else:
            run(f'yt-dlp --cookies /cookies.txt -o "{input_file}" "{url}"')

        # 2) Транскрибируем через Whisper (модель "base")
        run(
            f'whisper "{input_file}" --model base --output_format json --output_dir "{DATA_DIR}"'
        )
        base = os.path.splitext(os.path.basename(input_file))[0]
        transcript_file = os.path.join(DATA_DIR, base + '.json')

        # 3) Читаем результат и возвращаем
        out = json.load(open(transcript_file))
        return jsonify({
            'transcript': out.get('text'),
            'segments':   out.get('segments'),
            'inputPath':  input_file
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify(error=str(e)), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3001)
