from flask import Flask, request, jsonify
import subprocess, traceback

app = Flask(__name__)

def run(cmd):
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if proc.returncode != 0:
        raise Exception(f"Command `{cmd}` failed:\n{proc.stderr.strip()}")
    return proc.stdout

@app.route('/clip-video', methods=['POST'])
def clip_video():
    try:
        data = request.get_json(force=True)
        input_path = data.get('inputPath')
        start = data.get('start')
        end = data.get('end')
        if not input_path or start is None or end is None:
            return jsonify(error='Missing inputPath, start or end'), 400
        output_path = 'clip.mp4'
        run(f'ffmpeg -y -i "{input_path}" -ss {start} -to {end} -c copy "{output_path}"')
        return jsonify({'clipPath': output_path})
    except Exception as e:
        traceback.print_exc()
        return jsonify(error=str(e)), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3002)
