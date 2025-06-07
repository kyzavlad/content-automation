from flask import Flask, request, jsonify
import traceback, time, random

app = Flask(__name__)

@app.route('/publish-shorts', methods=['POST'])
def publish_short():
    try:
        data = request.get_json(force=True)
        clips = data.get('clips', [])
        titles = data.get('titles', [])
        platforms = data.get('platforms', [])
        if not clips or not platforms:
            return jsonify(error='Missing clips or platforms'), 400

        results = []
        for clip in clips:
            for platform in platforms:
                time.sleep(random.randint(30, 60))
                results.append({'clip': clip, 'platform': platform, 'status': 'ok'})

        return jsonify({'results': results})
    except Exception as e:
        traceback.print_exc()
        return jsonify(error=str(e)), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3004)
