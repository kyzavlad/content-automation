from flask import Flask, request, jsonify
rz9aqm-codex/настройка-автоматизации-контента-и-сервисов-на-сервере
import traceback, time, random

app = Flask(__name__)

import logging

app = Flask(__name__)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

main
@app.route('/publish-long', methods=['POST'])
def publish_long():
    try:
        data = request.get_json(force=True)
rz9aqm-codex/настройка-автоматизации-контента-и-сервисов-на-сервере
        video = data.get('video')
        variations = data.get('seo_variations', [])
        if not video or not variations:
            return jsonify(error='Missing video or seo_variations'), 400

        results = []
        for v in variations:
            time.sleep(random.randint(30, 60))
            results.append({'variation': v, 'status': 'ok'})

        return jsonify({'results': results})
    except Exception as e:
        traceback.print_exc()
        video_path = data.get('videoPath')
        accounts = data.get('accounts', [])
        if not video_path or not accounts:
            return jsonify(error='Missing videoPath or accounts'), 400
        return jsonify({'status': 'ok', 'accounts': accounts})
    except Exception as e:
        logger.exception("Internal error")
main
        return jsonify(error=str(e)), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3005)
