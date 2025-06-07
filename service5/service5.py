from flask import Flask, request, jsonify
import traceback, time, random

app = Flask(__name__)

@app.route('/publish-long', methods=['POST'])
def publish_long():
    try:
        data = request.get_json(force=True)
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
        return jsonify(error=str(e)), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3005)
