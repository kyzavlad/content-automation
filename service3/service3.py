# service3.py - Профессиональный сервис для создания Shorts
from flask import Flask, request, jsonify, send_file
import os
import logging
import subprocess
import json
import random
from datetime import datetime
import shutil
import tempfile

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

def get_video_info(video_path):
    """Получить информацию о видео"""
    cmd = [
        'ffprobe', '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height,duration,r_frame_rate',
        '-of', 'json', video_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        info = json.loads(result.stdout)
        stream = info['streams'][0]
        
        width = int(stream.get('width', 1920))
        height = int(stream.get('height', 1080))
        
        return {
            'width': width,
            'height': height,
            'is_vertical': height > width,
            'aspect_ratio': width / height
        }
    except Exception as e:
        logging.error(f"Error getting video info: {e}")
        return {
            'width': 1920,
            'height': 1080,
            'is_vertical': False,
            'aspect_ratio': 16/9
        }

def create_synchronized_subtitles(clip_info, transcript, output_path):
    """Создаем синхронизированные субтитры ТОЛЬКО для конкретного клипа"""
    clip_start = clip_info['start']
    clip_end = clip_info['end']
    
    segments = transcript.get('segments', []) if isinstance(transcript, dict) else []
    
    # Фильтруем только те сегменты, которые попадают в временной диапазон клипа
    relevant_segments = []
    for segment in segments:
        seg_start = segment.get('start', 0)
        seg_end = segment.get('end', seg_start)
        
        # Проверяем пересечение с клипом
        if seg_end > clip_start and seg_start < clip_end:
            relevant_segments.append({
                'start': max(0, seg_start - clip_start),  # Приводим к времени относительно начала клипа
                'end': min(clip_end - clip_start, seg_end - clip_start),
                'text': segment.get('text', '').strip()
            })
    
    # Создаем ASS файл для более точного контроля над субтитрами
    ass_content = """[Script Info]
Title: Shorts Subtitles
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Black,48,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,3,1,2,20,20,50,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    # Добавляем события субтитров
    for seg in relevant_segments:
        if seg['text']:
            start_time = self._format_ass_time(seg['start'])
            end_time = self._format_ass_time(seg['end'])
            
            # Разбиваем на слова для лучшей читаемости
            words = seg['text'].split()
            if len(words) > 4:
                # Для длинных фраз - делим на строки
                mid = len(words) // 2
                text = ' '.join(words[:mid]) + '\\N' + ' '.join(words[mid:])
            else:
                text = seg['text']
            
            ass_content += f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}\n"
    
    # Сохраняем ASS файл
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(ass_content)
    
    logging.info(f"Created synchronized subtitles for clip {clip_start}-{clip_end}s")
    return output_path

def _format_ass_time(seconds):
    """Форматируем время для ASS формата"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centisecs = int((seconds % 1) * 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"

def create_professional_edit(clip_path, clip_info, transcript):
    """Создаем профессиональный монтаж без излишеств"""
    try:
        # Получаем информацию о видео
        video_info = get_video_info(clip_path)
        
        # Создаем уникальное имя файла
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f"shorts_clip_{timestamp}.mp4"
        output_path = os.path.join('/data/edited', output_filename)
        
        # Временные файлы
        temp_dir = tempfile.mkdtemp()
        subtitle_path = os.path.join(temp_dir, 'subtitles.ass')
        
        # Создаем синхронизированные субтитры
        create_synchronized_subtitles(clip_info, transcript, subtitle_path)
        
        # Строим команду FFmpeg
        video_filters = []
        
        # 1. Конвертируем в вертикальный формат 9:16
        if not video_info['is_vertical']:
            # Для горизонтального видео - умный кроп с фокусом на центре
            video_filters.append('scale=1920:1080')  # Сначала нормализуем размер
            video_filters.append('crop=608:1080')    # Кропаем до 9:16 (608x1080)
            video_filters.append('scale=1080:1920')  # Масштабируем до нужного размера
        else:
            # Для вертикального - просто масштабируем
            video_filters.append('scale=1080:1920:force_original_aspect_ratio=decrease')
            video_filters.append('pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black')
        
        # 2. Легкое улучшение качества (без агрессивных фильтров)
        video_filters.append('unsharp=5:5:0.8:3:3:0.4')  # Легкая резкость
        
        # 3. Минимальная цветокоррекция
        video_filters.append('eq=brightness=0.03:contrast=1.05:saturation=1.1')
        
        # Объединяем фильтры
        filter_complex = ','.join(video_filters)
        
        # Добавляем субтитры если есть
        if os.path.exists(subtitle_path):
            filter_complex += f",ass={subtitle_path}"
        
        # Команда FFmpeg
        cmd = [
            'ffmpeg', '-y',
            '-i', clip_path,
            '-vf', filter_complex,
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '22',
            '-profile:v', 'high',
            '-level', '4.2',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-ar', '44100',
            '-movflags', '+faststart',
            '-pix_fmt', 'yuv420p',
            '-t', str(clip_info['duration']),  # Ограничиваем длительность
            output_path
        ]
        
        logging.info(f"Running FFmpeg command for professional edit")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logging.error(f"FFmpeg error: {result.stderr}")
            raise Exception(f"FFmpeg failed: {result.stderr}")
        
        # Удаляем временные файлы
        shutil.rmtree(temp_dir)
        
        # Копируем в публичную папку
        os.makedirs('/var/www/clips', exist_ok=True)
        public_path = os.path.join('/var/www/clips', output_filename)
        shutil.copy2(output_path, public_path)
        
        return {
            'path': output_path,
            'public_url': f"http://165.227.84.254:8888/clips/{output_filename}",
            'size_mb': os.path.getsize(output_path) / (1024 * 1024)
        }
        
    except Exception as e:
        logging.error(f"Error creating professional edit: {str(e)}")
        raise

@app.route('/edit-shorts', methods=['POST'])
def edit_shorts():
    try:
        data = request.json
        clips = data.get('clips', [])
        transcript = data.get('transcript', {})
        
        if not clips:
            return jsonify({'error': 'No clips provided'}), 400
        
        edited_clips = []
        
        for clip in clips:
            clip_path = clip.get('path')
            
            if not clip_path or not os.path.exists(clip_path):
                logging.error(f"Clip not found: {clip_path}")
                continue
            
            try:
                # Создаем профессиональную версию
                result = create_professional_edit(clip_path, clip, transcript)
                
                edited_clips.append({
                    'index': clip.get('index', 1),
                    'original': clip_path,
                    'path': result['path'],
                    'public_url': result['public_url'],
                    'size_mb': result['size_mb'],
                    'start_time': clip.get('start', 0),
                    'end_time': clip.get('end', 0),
                    'status': 'success'
                })
                
                logging.info(f"Professional edit created: {result['public_url']}")
                
            except Exception as e:
                logging.error(f"Error editing clip {clip_path}: {str(e)}")
                edited_clips.append({
                    'index': clip.get('index', 1),
                    'original': clip_path,
                    'status': 'error',
                    'error': str(e)
                })
        
        return jsonify({
            'status': 'success',
            'edited_clips': edited_clips,
            'total_edited': len([c for c in edited_clips if c.get('status') == 'success'])
        })
        
    except Exception as e:
        logging.error(f"Error in edit_shorts: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    # Создаем необходимые папки
    os.makedirs('/data/edited', exist_ok=True)
    os.makedirs('/var/www/clips', exist_ok=True)
    
    app.run(host='0.0.0.0', port=3003)
