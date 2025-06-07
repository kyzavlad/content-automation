from flask import Flask, request, jsonify
rz9aqm-codex/настройка-автоматизации-контента-и-сервисов-на-сервере
import subprocess, traceback, os

DATA_DIR = '/data'
os.makedirs(DATA_DIR, exist_ok=True)

app = Flask(__name__)

def run(cmd):
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if proc.returncode != 0:
        raise Exception(f"Command `{cmd}` failed:\n{proc.stderr.strip()}")
import subprocess
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
main
    return proc.stdout

@app.route('/clip-video', methods=['POST'])
def clip_video():
    try:
        data = request.get_json(force=True)
        input_path = data.get('inputPath')
rz9aqm-codex/настройка-автоматизации-контента-и-сервисов-на-сервере
        segments = data.get('segments', [])
        if not input_path or not isinstance(segments, list):
            return jsonify(error='Missing inputPath or segments'), 400

        clips = []
        for i, seg in enumerate(segments):
            start = seg.get('start')
            end = seg.get('end')
            engagement = seg.get('engagement', 0)
            if start is None or end is None:
                continue
            duration = end - start
            if duration < 15 or duration > 90:
                continue
            if engagement < 0.7:
                continue
            output_path = os.path.join(DATA_DIR, f'clip_{i}.mp4')
            run(f'ffmpeg -y -i "{input_path}" -ss {start} -to {end} -c copy "{output_path}"')
            clips.append({'path': output_path, 'start': start, 'end': end})

        if not clips:
            return jsonify(error='no_clips_found'), 400

        return jsonify({'clips': clips, 'success': True})
    except Exception as e:
        traceback.print_exc()
        start = data.get('start')
        end = data.get('end')
        if not input_path or start is None or end is None:
            return jsonify(error='Missing inputPath, start or end'), 400
        output_path = 'clip.mp4'
        run(f'ffmpeg -y -i "{input_path}" -ss {start} -to {end} -c copy "{output_path}"')
        return jsonify({'clipPath': output_path})
    except Exception as e:
        logger.exception("Internal error")
main
        return jsonify(error=str(e)), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3002)
