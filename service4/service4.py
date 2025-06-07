from flask import Flask, request, jsonify
rz9aqm-codex/настройка-автоматизации-контента-и-сервисов-на-сервере
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
import logging

app = Flask(__name__)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

@app.route('/publish-short', methods=['POST'])
def publish_short():
    try:
        data = request.get_json(force=True)
        video_path = data.get('videoPath')
        platform = data.get('platform')
        accounts = data.get('accounts', [])
        if not video_path or not platform or not accounts:
            return jsonify(error='Missing videoPath, platform or accounts'), 400
        # Here would be the real upload logic
        return jsonify({'status': 'ok', 'platform': platform, 'accounts': accounts})
    except Exception as e:
        logger.exception("Internal error")
main
        return jsonify(error=str(e)), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3004)
