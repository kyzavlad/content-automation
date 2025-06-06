from flask import Flask, request, jsonify
import traceback

app = Flask(__name__)

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
        traceback.print_exc()
        return jsonify(error=str(e)), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3004)
