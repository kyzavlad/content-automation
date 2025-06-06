from flask import Flask, request, jsonify
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
    return proc.stdout

@app.route('/edit', methods=['POST'])
def edit_video():
    try:
        data = request.get_json(force=True)
        input_path = data.get('inputPath')
        if not input_path:
            return jsonify(error='Missing inputPath'), 400
        output_path = 'edited.mp4'
        run(f'ffmpeg -y -i "{input_path}" -vf scale=720:-1 "{output_path}"')
        return jsonify({'editedPath': output_path})
    except Exception as e:
        logger.exception("Internal error")
        return jsonify(error=str(e)), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3003)
