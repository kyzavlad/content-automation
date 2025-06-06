from flask import Flask, request, jsonify
import subprocess, traceback

app = Flask(__name__)

def run(cmd):
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if proc.returncode != 0:
        raise Exception(f"Command `{cmd}` failed:\n{proc.stderr.strip()}")
    return proc.stdout

@app.route('/edit-shorts', methods=['POST'])
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
        traceback.print_exc()
        return jsonify(error=str(e)), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3003)
