import os
import json
import subprocess
import logging
import re
from flask import Flask, request, jsonify
import whisper
import numpy as np
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

app = Flask(__name__)

# Initialize Whisper model
model = whisper.load_model("base")

# Create directories
os.makedirs('/data/clips', exist_ok=True)
os.makedirs('/data/temp', exist_ok=True)

# Viral content patterns
HOOK_PATTERNS = [
    r'\b(listen|watch this|important|secret|truth|never|always|must|need to know|shocking|crazy)\b',
    r'\b(million|thousand|dollars|money|rich|wealth|success)\b',
    r'\b(nobody tells you|they don\'t want you to know|hidden|revealed)\b',
    r'\b(how to|why you|what if|imagine|think about)\b',
    r'\b(mistake|wrong|failed|lost)\b',
    r'\b(life.?changing|game.?changer|breakthrough|transform)\b'
]

EMOTION_WORDS = {
    'high_energy': ['amazing', 'incredible', 'unbelievable', 'insane', 'crazy', 'boom', 'wow'],
    'urgency': ['now', 'today', 'immediately', 'quick', 'fast', 'hurry'],
    'exclusive': ['only', 'secret', 'exclusive', 'special', 'unique'],
    'social_proof': ['everyone', 'million', 'viral', 'trending', 'popular'],
}

def analyze_audio_levels(video_path):
    """Analyze audio levels to detect speech and silence"""
    cmd = f'''ffmpeg -i "{video_path}" -af "volumedetect" -f null - 2>&1 | grep -E "mean_volume|max_volume"'''
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    # Extract volume info
    mean_volume = -30  # Default
    max_volume = -20
    
    for line in result.stdout.split('\n'):
        if 'mean_volume' in line:
            mean_volume = float(re.findall(r'-?\d+\.?\d*', line)[0])
        elif 'max_volume' in line:
            max_volume = float(re.findall(r'-?\d+\.?\d*', line)[0])
    
    return mean_volume, max_volume

def detect_scene_changes(video_path):
    """Detect scene changes for better cut points"""
    output_file = f"/data/temp/scenes_{os.path.basename(video_path)}.txt"
    
    cmd = f'''ffmpeg -i "{video_path}" -filter:v "select='gt(scene,0.3)',showinfo" -f null - 2>&1 | grep showinfo > "{output_file}"'''
    subprocess.run(cmd, shell=True)
    
    scene_changes = []
    if os.path.exists(output_file):
        with open(output_file, 'r') as f:
            for line in f:
                match = re.search(r'pts_time:(\d+\.?\d*)', line)
                if match:
                    scene_changes.append(float(match.group(1)))
        os.remove(output_file)
    
    return scene_changes

def find_speech_start(segments, start_time=0):
    """Find when actual speech starts (not just entering frame)"""
    for segment in segments:
        # Skip if before our start time
        if segment['end'] < start_time:
            continue
            
        text = segment['text'].strip()
        # Skip short utterances, fillers, or silence
        if len(text) > 3 and not text.lower() in ['um', 'uh', 'ah', 'oh', 'so', 'and']:
            # Return slightly before to capture the full word
            return max(0, segment['start'] - 0.2)
    
    return start_time

def calculate_engagement_score(text, position_percent, segment_duration):
    """Calculate engagement score for a text segment"""
    score = 0
    text_lower = text.lower()
    
    # Check for hook patterns (더 높은 점수)
    for pattern in HOOK_PATTERNS:
        if re.search(pattern, text_lower):
            score += 25
    
    # Check emotion words
    for category, words in EMOTION_WORDS.items():
        for word in words:
            if word in text_lower:
                score += 15
    
    # Questions get bonus
    if '?' in text:
        score += 20
    
    # Numbers and statistics
    if re.search(r'\b\d+\b', text):
        score += 15
    
    # Length bonus (not too short, not too long)
    word_count = len(text.split())
    if 10 <= word_count <= 30:
        score += 10
    
    # Position bonus (beginning is crucial)
    if position_percent < 0.1:  # First 10%
        score *= 1.5
    elif position_percent < 0.3:  # First 30%
        score *= 1.2
    
    # Penalize very short segments
    if segment_duration < 2:
        score *= 0.5
    
    return int(score)

def find_viral_moments(transcript, video_duration):
    """Find the most viral-worthy moments in the transcript"""
    segments = transcript.get('segments', [])
    if not segments:
        return []
    
    moments = []
    
    # Analyze each segment
    for i, segment in enumerate(segments):
        text = segment['text'].strip()
        start = segment['start']
        end = segment['end']
        duration = end - start
        position_percent = start / video_duration if video_duration > 0 else 0
        
        # Calculate engagement score
        score = calculate_engagement_score(text, position_percent, duration)
        
        # Look for complete thoughts (combine with next segments if needed)
        combined_text = text
        combined_end = end
        j = i + 1
        
        # Combine segments until we hit punctuation or max duration
        while j < len(segments) and (combined_end - start) < 60:
            next_segment = segments[j]
            combined_text += ' ' + next_segment['text'].strip()
            combined_end = next_segment['end']
            
            # Check if we have a complete thought
            if any(p in combined_text for p in ['.', '!', '?']) or (combined_end - start) > 30:
                break
            j += 1
        
        # Find actual speech start (not just presence in frame)
        actual_start = find_speech_start(segments[i:j+1], start)
        
        moments.append({
            'start': actual_start,
            'end': combined_end,
            'score': score,
            'text': combined_text,
            'segments': segments[i:j+1]
        })
    
    # Sort by score and remove overlaps
    moments.sort(key=lambda x: x['score'], reverse=True)
    
    # Remove overlapping moments
    filtered_moments = []
    for moment in moments:
        # Check if overlaps with already selected moments
        overlap = False
        for selected in filtered_moments:
            if (moment['start'] < selected['end'] and moment['end'] > selected['start']):
                overlap = True
                break
        
        if not overlap and moment['score'] > 20:  # Minimum score threshold
            filtered_moments.append(moment)
    
    # Sort by start time
    filtered_moments.sort(key=lambda x: x['start'])
    
    return filtered_moments

def extract_clip(video_path, start_time, end_time, output_path, fade_in=True):
    """Extract a clip with optional fade in/out"""
    duration = end_time - start_time
    
    # Build filter string
    filters = []
    
    if fade_in:
        filters.append("fade=t=in:st=0:d=0.5")
    
    # Add fade out only if clip is long enough
    if duration > 3:
        filters.append(f"fade=t=out:st={duration-0.5}:d=0.5")
    
    filter_string = ",".join(filters) if filters else None
    
    # Build ffmpeg command
    cmd = f'ffmpeg -y -ss {start_time} -i "{video_path}" -t {duration}'
    
    if filter_string:
        cmd += f' -vf "{filter_string}"'
    
    cmd += f' -c:v libx264 -preset fast -crf 23 -c:a aac -b:a 192k "{output_path}"'
    
    logging.info(f"Extracting clip: {start_time:.1f}s - {end_time:.1f}s")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        logging.error(f"FFmpeg error: {result.stderr}")
        return False
    
    return os.path.exists(output_path) and os.path.getsize(output_path) > 0

def create_clips_from_video(video_path, transcript, max_clips=5):
    """Create viral clips from video using smart detection"""
    # Get video duration
    probe_cmd = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{video_path}"'
    duration_result = subprocess.run(probe_cmd, shell=True, capture_output=True, text=True)
    video_duration = float(duration_result.stdout.strip())
    
    # Find viral moments
    moments = find_viral_moments(transcript, video_duration)
    
    if not moments:
        logging.warning("No viral moments found, creating default clips")
        # Fallback: create clips from beginning
        moments = [{
            'start': 0,
            'end': min(30, video_duration),
            'score': 50,
            'text': 'Default clip'
        }]
    
    # Create clips
    clips = []
    for i, moment in enumerate(moments[:max_clips]):
        clip_start = moment['start']
        clip_end = min(moment['end'] + 1, video_duration)  # Add 1 second buffer
        
        # Ensure minimum clip length
        if clip_end - clip_start < 15:
            clip_end = min(clip_start + 30, video_duration)
        
        # Ensure maximum clip length for shorts
        if clip_end - clip_start > 60:
            clip_end = clip_start + 60
        
        output_filename = f"clip_{i+1:02d}_score{moment['score']}.mp4"
        output_path = f"/data/clips/{output_filename}"
        
        success = extract_clip(
            video_path,
            clip_start,
            clip_end,
            output_path,
            fade_in=(i == 0)  # Only fade in on first clip
        )
        
        if success:
            clips.append({
                'path': output_path,
                'filename': output_filename,
                'start': clip_start,
                'end': clip_end,
                'duration': clip_end - clip_start,
                'score': moment['score'],
                'text': moment['text'][:200],  # First 200 chars
                'index': i + 1
            })
            logging.info(f"Created clip {i+1}: {clip_start:.1f}s - {clip_end:.1f}s (score: {moment['score']})")
    
    return clips

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'service': 'intelligent-clip-extractor',
        'features': [
            'speech_detection',
            'viral_moment_analysis', 
            'engagement_scoring',
            'smart_cut_points'
        ]
    })

@app.route('/clip-video', methods=['POST'])
def clip_video():
    """Extract viral clips from video"""
    try:
        video_path = request.json.get('video_path')
        transcript = request.json.get('transcript')
        max_clips = request.json.get('max_clips', 5)
        
        if not video_path:
            return jsonify({'error': 'No video path provided'}), 400
        
        logging.info(f"Processing video: {video_path}")
        
        # Generate transcript if not provided
        if not transcript:
            logging.info("No transcript provided, generating...")
            result = model.transcribe(video_path, language='en')
            transcript = {
                'text': result['text'],
                'segments': result['segments']
            }
        
        # Analyze transcript for insights
        logging.info("Analyzing transcript for viral moments...")
        logging.info(f"Found {len(transcript.get('segments', []))} segments")
        
        # Create clips
        clips = create_clips_from_video(video_path, transcript, max_clips)
        
        if not clips:
            return jsonify({
                'status': 'error',
                'message': 'Failed to create clips'
            }), 500
        
        # Return results with transcript for next service
        return jsonify({
            'status': 'success',
            'clips': clips,
            'transcript': transcript,
            'total_clips': len(clips),
            'insights': {
                'total_segments': len(transcript.get('segments', [])),
                'video_path': video_path
            }
        }), 200
        
    except Exception as e:
        logging.error(f"Error in clip_video: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3002, threaded=True)
