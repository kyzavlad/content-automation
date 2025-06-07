from flask import Flask, request, jsonify
rz9aqm-codex/настройка-автоматизации-контента-и-сервисов-на-сервере
import subprocess, traceback, os, glob, random

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

@app.route('/edit-shorts', methods=['POST'])
def edit_video():
    try:
        data = request.get_json(force=True)
rz9aqm-codex/настройка-автоматизации-контента-и-сервисов-на-сервере
        clips = data.get('clips', [])
        output_dir = data.get('outputDir', '/data/edited')
        if not clips or not isinstance(clips, list):
            return jsonify(error='Missing clips'), 400

        os.makedirs(output_dir, exist_ok=True)
        edited = []
        music_files = glob.glob('/root/media-library/music/*.mp3')

        for i, clip_path in enumerate(clips):
            output_path = os.path.join(output_dir, f'edited_{i}.mp4')
            music = random.choice(music_files) if music_files else None
            cmd = f'ffmpeg -y -i "{clip_path}"'
            if music:
                cmd += f' -i "{music}" -c:v copy -c:a aac -shortest'
            cmd += ' -vf "fade=t=in:st=0:d=0.5,fade=t=out:st=duration-0.5:d=0.5"'
            cmd += f' "{output_path}"'
            run(cmd)
            edited.append(output_path)

        return jsonify({'editedClips': edited})
    except Exception as e:
        traceback.print_exc()
        input_path = data.get('inputPath')
        if not input_path:
            return jsonify(error='Missing inputPath'), 400
        output_path = 'edited.mp4'
        run(f'ffmpeg -y -i "{input_path}" -vf scale=720:-1 "{output_path}"')
        return jsonify({'editedPath': output_path})
    except Exception as e:
        logger.exception("Internal error")
main
        return jsonify(error=str(e)), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3003)
