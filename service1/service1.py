import os
import json
import time
import subprocess
import logging
import whisper
import requests
from flask import Flask, request, jsonify
import uuid
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

app = Flask(__name__)

# Create data directory
os.makedirs('/data', exist_ok=True)

# Load models
logging.info("Loading Whisper models...")
model_base = whisper.load_model("base")
model_tiny = whisper.load_model("tiny")
logging.info("Whisper models loaded successfully")

def download_video(url, output_path):
    """Download video from any platform"""
    
    # Use yt-dlp for everything
    cmd = [
        'yt-dlp',
        '--no-check-certificate',
        '-o', output_path,
        '--no-playlist',
        '-f', 'best[ext=mp4]/best',
        '--merge-output-format', 'mp4',
        '--cookies', '/cookies.txt',
        '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        '--retries', '10',
        '--fragment-retries', '10',
        '--concurrent-fragments', '4',
        '--buffer-size', '16K',
        '--http-chunk-size', '10485760',
        '--no-warnings',
        '--quiet',
        '--no-progress',
        '--force-overwrites',
        url
    ]
    
    logging.info(f"Downloading from: {url}")
    
    # Run download
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)  # 2 hour timeout
    
    if proc.returncode != 0:
        logging.error(f"yt-dlp stderr: {proc.stderr}")
        raise RuntimeError(f"Download failed: {proc.stderr}")
    
    # Verify file exists
    if not os.path.exists(output_path):
        raise RuntimeError("Download completed but file not found")
    
    file_size = os.path.getsize(output_path)
    if file_size < 1000:
        raise RuntimeError(f"Downloaded file too small: {file_size} bytes")
    
    logging.info(f"Download successful: {output_path} ({file_size/1024/1024:.2f} MB)")
    return file_size

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'models_loaded': {
            'base': True,
            'tiny': True
        }
    })

@app.route('/transcribe', methods=['POST'])
def transcribe_sync():
    """Main endpoint - download and transcribe video"""
    data = request.json
    if not data or 'videoUrl' not in data:
        return jsonify({'error': 'videoUrl is required'}), 400
    
    url = data['videoUrl']
    job_id = str(uuid.uuid4().hex)[:8]
    temp_file = f"/data/{job_id}.mp4"
    
    try:
        # Download video
        logging.info(f"[{job_id}] Starting download from: {url}")
        start_time = time.time()
        
        file_size = download_video(url, temp_file)
        
        download_time = time.time() - start_time
        logging.info(f"[{job_id}] Downloaded in {download_time:.1f}s: {file_size/1024/1024:.1f} MB")
        
        # Choose model based on file size
        if file_size > 100 * 1024 * 1024:  # > 100MB
            logging.info(f"[{job_id}] Large file detected, using tiny model for speed")
            model = model_tiny
        else:
            model = model_base
        
        # Transcribe
        logging.info(f"[{job_id}] Starting transcription...")
        transcribe_start = time.time()
        
        # Use language detection for better results
        result = model.transcribe(
            temp_file, 
            fp16=False,
            language=None,  # Auto-detect language
            task='transcribe',
            verbose=False
        )
        transcribe_time = time.time() - transcribe_start
        logging.info(f'[{job_id}] Transcription completed in {transcribe_time:.1f}s')
        
        # Cleanup
        if os.path.exists(temp_file):
            # НЕ УДАЛЯЕМ ФАЙЛ - он нужен для service2
            # os.remove(temp_file) - закомментируйте эту строку если она есть
            pass
        
        return jsonify({
            'status': 'success',
            'transcript': result,
            'text': result['text'],
            'language': result.get('language', 'unknown'),
            'video_path': temp_file,  # ДОБАВЛЕНО: путь к видео
            'metadata': {
                'download_time': round(download_time, 1),
                'transcribe_time': round(transcribe_time, 1),
                'total_time': round(download_time + transcribe_time, 1),
                'file_size_mb': round(file_size/1024/1024, 1),
                'model_used': 'tiny' if file_size > 100 * 1024 + 1024 else 'base'
            }
        }), 200
    except Exception as e:
        logging.error(f"[{job_id}] Error: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        
        # Cleanup on error
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

# Legacy endpoints for compatibility
@app.route('/download-transcribe', methods=['POST'])
def download_transcribe():
    """Redirect to main endpoint"""
    return transcribe_sync()

@app.route('/process', methods=['POST'])
def process():
    """Another legacy endpoint"""
    return transcribe_sync()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3001, threaded=True)
