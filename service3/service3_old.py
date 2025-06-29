import os
import json
import random
import logging
import subprocess
import re
import shutil
from flask import Flask, request, jsonify
from datetime import datetime
import glob

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

app = Flask(__name__)

# Create directories
os.makedirs('/data/edited', exist_ok=True)
os.makedirs('/data/temp', exist_ok=True)
os.makedirs('/var/www/clips', exist_ok=True)

# Media library paths
MUSIC_DIR = '/media_upload/music'
BROLL_DIR = '/media_upload/music/broll'

# Professional subtitle styles
SUBTITLE_STYLES = {
    'modern': {
        'font': 'Montserrat Black',
        'size': 32,
        'primary': '&HFFFFFF',
        'outline': '&H000000',
        'shadow': 2,
        'border': 4,
        'margin_v': 150
    },
    'tiktok': {
        'font': 'Arial Black', 
        'size': 36,
        'primary': '&HFFFFFF',
        'outline': '&HFF0000',
        'shadow': 0,
        'border': 3,
        'margin_v': 200
    },
    'youtube': {
        'font': 'Bebas Neue',
        'size': 34,
        'primary': '&H00FFFF',
        'outline': '&H000000', 
        'shadow': 3,
        'border': 4,
        'margin_v': 180
    }
}

def copy_to_public(file_path):
    """Copy file to public directory and return URL"""
    try:
        filename = os.path.basename(file_path)
        public_path = f"/var/www/clips/{filename}"
        
        logging.info(f"Copying {file_path} to {public_path}")
        
        # Check source
        if not os.path.exists(file_path):
            logging.error(f"Source file does not exist: {file_path}")
            return None
            
        source_size = os.path.getsize(file_path)
        if source_size == 0:
            logging.error(f"Source file is empty: {file_path}")
            return None
            
        # Copy file
        shutil.copy2(file_path, public_path)
        
        # Verify
        if os.path.exists(public_path) and os.path.getsize(public_path) == source_size:
            logging.info(f"Successfully copied to {public_path}, size: {source_size} bytes")
            return f"http://165.227.84.254:8888/clips/{filename}"
        
        return None
    except Exception as e:
        logging.error(f"Error in copy_to_public: {str(e)}")
        return None

def get_video_info(video_path):
    """Get video information using ffprobe"""
    cmd = f'''ffprobe -v quiet -print_format json -show_format -show_streams "{video_path}"'''
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        return json.loads(result.stdout)
    return None

def select_music_by_content(text, music_files):
    """Select appropriate music based on content analysis"""
    text_lower = text.lower()
    
    # Content-based selection
    if any(word in text_lower for word in ['money', 'rich', 'millionaire', 'success', 'business', 'hustle']):
        category = 'hard'
    elif any(word in text_lower for word in ['mindset', 'discipline', 'warrior', 'fight', 'grind']):
        category = 'motivational'
    elif any(word in text_lower for word in ['peace', 'calm', 'relax', 'meditation']):
        category = 'calm'
    elif any(word in text_lower for word in ['trending', 'viral', 'tiktok']):
        category = 'trending'
    elif any(word in text_lower for word in ['dark', 'sigma', 'alpha']):
        category = 'phonk'
    else:
        category = 'instrumental'
    
    # Get appropriate music
    available = music_files.get(category, [])
    if not available:
        all_music = []
        for tracks in music_files.values():
            all_music.extend(tracks)
        available = all_music
    
    return random.choice(available) if available else None

def generate_dynamic_subtitles(transcript, output_path, style='modern'):
    """Generate professional animated subtitles"""
    segments = transcript.get('segments', [])
    if not segments:
        return None
    
    style_config = SUBTITLE_STYLES.get(style, SUBTITLE_STYLES['modern'])
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, segment in enumerate(segments):
            # SRT index
            f.write(f"{i+1}\n")
            
            # Timing with slight overlap for smooth transitions
            start_time = segment['start']
            end_time = segment['end']
            
            # Convert to SRT format
            start_srt = f"{int(start_time//3600):02d}:{int((start_time%3600)//60):02d}:{int(start_time%60):02d},{int((start_time%1)*1000):03d}"
            end_srt = f"{int(end_time//3600):02d}:{int((end_time%3600)//60):02d}:{int(end_time%60):02d},{int((end_time%1)*1000):03d}"
            
            f.write(f"{start_srt} --> {end_srt}\n")
            
            # Format text for impact
            text = segment['text'].strip()
            words = text.split()
            
            # Emphasize key words
            formatted_words = []
            for word in words:
                if any(pattern in word.lower() for pattern in ['money', 'million', 'success', 'never', 'always', 'must']):
                    # Make important words stand out
                    formatted_words.append(word.upper())
                else:
                    formatted_words.append(word)
            
            # Create lines (max 3-4 words per line for readability)
            lines = []
            current_line = []
            
            for word in formatted_words:
                current_line.append(word)
                if len(current_line) >= 3:
                    lines.append(' '.join(current_line))
                    current_line = []
            
            if current_line:
                lines.append(' '.join(current_line))
            
            # Max 2 lines at once
            if len(lines) > 2:
                text = '\n'.join(lines[:2])
            else:
                text = '\n'.join(lines)
            
            f.write(f"{text}\n\n")
    
    return output_path

def detect_content_style(text):
    """Auto-detect best style based on content"""
    text_lower = text.lower()
    
    # TikTok style for trending/viral content
    if any(word in text_lower for word in ['tiktok', 'viral', 'trending', 'hack', 'tips', 'quick']):
        return 'tiktok'
    
    # YouTube style for educational/longer content  
    elif any(word in text_lower for word in ['tutorial', 'how to', 'guide', 'explain', 'learn']):
        return 'youtube'
    
    # Modern style for business/motivational
    else:
        return 'modern'

def create_professional_edit(clip_info, transcript, style='auto'):
    """Create viral-ready edit with all professional features"""
    input_path = clip_info['path']
    clip_index = clip_info.get('index', 1)
    output_path = f"/data/edited/edited_clip_{clip_index:02d}.mp4"
    
    # Get video info
    video_info = get_video_info(input_path)
    if not video_info:
        logging.error(f"Failed to get video info for {input_path}")
        return None
    
    # Auto-detect style if set to 'auto'
    clip_text = clip_info.get('text', '')
    if style == 'auto':
        style = detect_content_style(clip_text)
        logging.info(f"Auto-detected style: {style}")
    
    # Get media files
    music_files = {
        'motivational': glob.glob(f'{MUSIC_DIR}/*motivational*.mp3'),
        'hard': glob.glob(f'{MUSIC_DIR}/hard_*.mp3'),
        'calm': glob.glob(f'{MUSIC_DIR}/calm_*.mp3'),
        'instrumental': glob.glob(f'{MUSIC_DIR}/instrumental_*.mp3'),
        'phonk': glob.glob(f'{MUSIC_DIR}/*phonk*.mp3'),
        'trending': glob.glob(f'{MUSIC_DIR}/trending_*.mp3')
    }
    
    # Select music based on content
    clip_text = clip_info.get('text', '')
    music_path = select_music_by_content(clip_text, music_files)
    
    # Generate dynamic subtitles with detected style
    srt_path = f"/data/temp/subtitles_{clip_index}.srt"
    generate_dynamic_subtitles(transcript, srt_path, style)
    
    # Build complex FFmpeg command
    inputs = [f'-i "{input_path}"']
    
    # Audio mixing setup with proper levels
    if music_path and os.path.exists(music_path):
        inputs.append(f'-i "{music_path}"')
        # Mix audio: voice at 85%, music at 15% (ducked)
        audio_filter = '''[0:a]volume=0.85[a1];[1:a]volume=0.15[a2];[a1][a2]amerge=inputs=2[aout]'''
    else:
        audio_filter = '[0:a]volume=1.0[aout]'
    
    # Video filters for viral effect
    video_filters = []
    
    # 1. Scale to 9:16 with smart crop
    video_filters.append("scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black")
    
    # 2. Enhance contrast and saturation for pop
    video_filters.append("eq=contrast=1.15:brightness=0.02:saturation=1.2")
    
    # 3. Add subtle vignette
    video_filters.append("vignette=PI/4:mode=backward")
    
    # 4. Sharpen for clarity
    video_filters.append("unsharp=5:5:0.8:3:3:0.4")
    
    # 5. Add dynamic zoom (subtle Ken Burns effect)
    duration = clip_info.get('duration', 30)
    if duration > 10:
        video_filters.append(f"zoompan=z='min(zoom+0.0002,1.1)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(duration*30)}:s=1080x1920:fps=30")
    
    # 6. Add fade in
    video_filters.append("fade=t=in:st=0:d=0.3")
    
    # Combine video filters
    video_filter_string = ','.join(video_filters)
    
    # Subtitle filter with style
    style_config = SUBTITLE_STYLES[style]
    if os.path.exists(srt_path) and os.path.getsize(srt_path) > 0:
        subtitle_filter = f''',subtitles={srt_path}:force_style='FontName={style_config["font"]},FontSize={style_config["size"]},PrimaryColour={style_config["primary"]},OutlineColour={style_config["outline"]},BorderStyle=3,Outline={style_config["border"]},Shadow={style_config["shadow"]},MarginV={style_config["margin_v"]},Alignment=2,Bold=1' '''
    else:
        subtitle_filter = ""
    
    # Build complete filter complex
    filter_complex = f'''{audio_filter};[0:v]{video_filter_string}{subtitle_filter}[vout]'''
    
    # Complete FFmpeg command
    cmd = f'''ffmpeg -y {' '.join(inputs)} \
    -filter_complex "{filter_complex}" \
    -map "[vout]" -map "[aout]" \
    -c:v libx264 -preset medium -crf 21 \
    -profile:v high -level 4.0 \
    -c:a aac -b:a 256k -ar 48000 \
    -movflags +faststart \
    -metadata title="Viral Short #{clip_index}" \
    -metadata comment="Professional Edit" \
    "{output_path}"'''
    
    logging.info(f"Creating professional edit for clip {clip_index}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        logging.error(f"FFmpeg error: {result.stderr}")
        # Try simpler version
        return create_fallback_edit(clip_info, transcript, style)
    
    # Clean up
    if os.path.exists(srt_path):
        os.remove(srt_path)
    
    # Verify output
    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        return output_path
    
    return None

def create_fallback_edit(clip_info, transcript, style='modern'):
    """Simplified edit if professional fails"""
    input_path = clip_info['path']
    clip_index = clip_info.get('index', 1)
    output_path = f"/data/edited/edited_clip_{clip_index:02d}_simple.mp4"
    
    # Generate subtitles with specified style
    srt_path = f"/data/temp/subtitles_{clip_index}.srt"
    generate_dynamic_subtitles(transcript, srt_path, style)
    
    # Simple but effective edit
    filters = [
        "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black",
        "eq=contrast=1.1:brightness=0.01:saturation=1.1"
    ]
    
    if os.path.exists(srt_path) and os.path.getsize(srt_path) > 0:
        filters.append(f"subtitles={srt_path}:force_style='FontName=Arial Black,FontSize=32,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,BorderStyle=3,Outline=3,Bold=1,MarginV=150'")
    
    filter_string = ','.join(filters)
    
    cmd = f'''ffmpeg -y -i "{input_path}" \
    -vf "{filter_string}" \
    -c:v libx264 -preset fast -crf 22 \
    -c:a aac -b:a 192k \
    "{output_path}"'''
    
    subprocess.run(cmd, shell=True)
    
    if os.path.exists(srt_path):
        os.remove(srt_path)
    
    return output_path if os.path.exists(output_path) else None

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'service': 'professional-video-editor',
        'features': [
            'dynamic_subtitles',
            'audio_ducking',
            'visual_effects',
            'content_aware_music'
        ]
    })

@app.route('/edit-shorts', methods=['POST'])
def edit_shorts():
    """Create viral-ready short videos"""
    try:
        data = request.json
        clips = data.get('clips', [])
        transcript = data.get('transcript', {})
        style = data.get('style', 'modern')
        
        if not clips:
            return jsonify({'error': 'No clips provided'}), 400
        
        edited_videos = []
        
        for clip in clips:
            if isinstance(clip, str):
                clip_info = {
                    'path': clip,
                    'index': len(edited_videos) + 1
                }
            else:
                clip_info = clip
            
            try:
                # Create professional edit
                output_path = create_professional_edit(clip_info, transcript, style)
                
                if output_path and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    # Copy to public
                    public_url = copy_to_public(output_path)
                    
                    if public_url:
                        edited_videos.append({
                            'path': output_path,
                            'original': clip_info['path'],
                            'index': clip_info.get('index', len(edited_videos) + 1),
                            'style': style,
                            'score': clip_info.get('score', 0),
                            'public_url': public_url
                        })
                        logging.info(f"Successfully edited: {output_path}, URL: {public_url}")
                
            except Exception as e:
                logging.error(f"Error editing clip: {str(e)}")
                continue
        
        return jsonify({
            'status': 'success',
            'edited_clips': edited_videos,
            'total_edited': len(edited_videos)
        }), 200
        
    except Exception as e:
        logging.error(f"Error in edit_shorts: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/edit-video', methods=['POST'])
def edit_video():
    """Alias for compatibility"""
    return edit_shorts()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3003, threaded=True)
