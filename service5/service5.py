from flask import Flask, request, jsonify
import logging

app = Flask(__name__)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

@app.route('/publish-long', methods=['POST'])
def publish_long():
    try:
        data = request.get_json(force=True)
        video_path = data.get('videoPath')
        accounts = data.get('accounts', [])
        if not video_path or not accounts:
            return jsonify(error='Missing videoPath or accounts'), 400
        return jsonify({'status': 'ok', 'accounts': accounts})
    except Exception as e:
        logger.exception("Internal error")
        return jsonify(error=str(e)), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3005)
