from flask import Flask, request, jsonify
import subprocess, traceback, os, glob, random

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
        return jsonify(error=str(e)), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3003)
