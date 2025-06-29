# service2.py - Универсальный сервис для извлечения вирусных моментов
from flask import Flask, request, jsonify
import os
import logging
import subprocess
import json
import shutil
from datetime import datetime
import numpy as np
import cv2

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

def get_video_info(video_path):
    """Получить информацию о видео"""
    cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'stream=width,height,duration,r_frame_rate',
        '-of', 'json', video_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        info = json.loads(result.stdout)
        video_stream = next((s for s in info['streams'] if s.get('width')), None)
        
        if video_stream:
            width = int(video_stream['width'])
            height = int(video_stream['height'])
            duration = float(video_stream.get('duration', 0))
            
            # Определяем ориентацию
            orientation = 'vertical' if height > width else 'horizontal'
            
            return {
                'width': width,
                'height': height,
                'duration': duration,
                'orientation': orientation
            }
    except Exception as e:
        logging.error(f"Error getting video info: {e}")
    
    return {'width': 1920, 'height': 1080, 'duration': 0, 'orientation': 'horizontal'}

def analyze_visual_activity(video_path, start_time, end_time):
    """Анализ визуальной активности в видео"""
    try:
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        # Переходим к начальному кадру
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(start_time * fps))
        
        prev_frame = None
        activity_scores = []
        
        current_time = start_time
        while current_time < end_time:
            ret, frame = cap.read()
            if not ret:
                break
                
            # Конвертируем в grayscale для анализа
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            if prev_frame is not None:
                # Считаем разницу между кадрами
                diff = cv2.absdiff(prev_frame, gray)
                activity_score = np.mean(diff)
                activity_scores.append(activity_score)
            
            prev_frame = gray
            current_time += 1/fps
        
        cap.release()
        
        # Возвращаем среднюю активность
        return np.mean(activity_scores) if activity_scores else 0
        
    except Exception as e:
        logging.error(f"Error analyzing visual activity: {e}")
        return 0

def analyze_audio_energy(video_path, start_time, end_time):
    """Анализ аудио энергии в сегменте"""
    try:
        cmd = [
            'ffmpeg', '-i', video_path,
            '-ss', str(start_time),
            '-t', str(end_time - start_time),
            '-af', 'volumedetect',
            '-f', 'null', '-'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stderr
        
        # Извлекаем среднюю громкость
        for line in output.split('\n'):
            if 'mean_volume:' in line:
                volume = float(line.split('mean_volume:')[1].split('dB')[0].strip())
                # Нормализуем (чем ближе к 0, тем громче)
                return max(0, 100 + volume)
                
    except Exception as e:
        logging.error(f"Error analyzing audio: {e}")
    
    return 0

def analyze_transcript_segment(segment):
    """Анализ текста сегмента на вирусность"""
    text = segment.get('text', '').lower()
    
    # Ключевые слова для вирусного контента
    viral_keywords = [
        # Деньги и успех
        'money', 'dollar', 'rich', 'wealth', 'million', 'thousand', 'profit',
        'деньги', 'доллар', 'богат', 'миллион', 'тысяч', 'прибыль',
        '10k', '100k', '1m', 'earn', 'make money', 'заработ',
        
        # Эмоции и шок
        'crazy', 'insane', 'unbelievable', 'shocking', 'amazing', 'wow',
        'безумн', 'невероятн', 'шок', 'офиген', 'ого', 'вау',
        
        # Призывы к действию
        'secret', 'trick', 'hack', 'tip', 'strategy', 'method',
        'секрет', 'трюк', 'хак', 'совет', 'стратег', 'метод',
        
        # Срочность
        'now', 'today', 'quick', 'fast', 'hurry', 'limited',
        'сейчас', 'сегодня', 'быстр', 'спеши', 'ограничен',
        
        # Вопросы-хуки
        'how to', 'what if', 'did you know', 'want to',
        'как', 'что если', 'знаете ли', 'хотите'
    ]
    
    # Считаем вхождения ключевых слов
    keyword_score = sum(1 for keyword in viral_keywords if keyword in text) * 10
    
    # Длина текста (короткие фразы часто более цепляющие)
    length_score = max(0, 50 - len(text.split())) if len(text.split()) < 50 else 0
    
    # Наличие чисел (конкретика привлекает)
    import re
    numbers = re.findall(r'\d+', text)
    number_score = len(numbers) * 15
    
    # Восклицательные и вопросительные знаки
    excitement_score = (text.count('!') + text.count('?')) * 20
    
    return keyword_score + length_score + number_score + excitement_score

def find_viral_moments(video_path, transcript, video_info):
    """Находим самые вирусные моменты в видео"""
    segments = transcript.get('segments', [])
    duration = video_info['duration']
    
    logging.info(f"Analyzing video: duration={duration}s, segments={len(segments)}")
    
    viral_moments = []
    
    # Если есть транскрипция, анализируем по сегментам
    if segments:
        for i, segment in enumerate(segments):
            start_time = segment.get('start', 0)
            end_time = segment.get('end', start_time + 1)
            
            # Базовый скор из анализа текста
            text_score = analyze_transcript_segment(segment)
            
            # Анализ визуальной активности (опционально для производительности)
            visual_score = 0
            if duration < 300:  # Только для видео меньше 5 минут
                visual_score = analyze_visual_activity(video_path, start_time, min(end_time, start_time + 5))
            
            # Анализ аудио энергии
            audio_score = analyze_audio_energy(video_path, start_time, end_time)
            
            # Общий скор
            total_score = text_score + visual_score + audio_score
            
            viral_moments.append({
                'start': start_time,
                'end': end_time,
                'text': segment.get('text', ''),
                'score': total_score,
                'segment_index': i
            })
    
    # Если нет транскрипции или видео очень короткое
    if not viral_moments or duration < 60:
        # Для коротких видео - берем все видео как один момент
        if duration < 60:
            viral_moments = [{
                'start': 0,
                'end': duration,
                'text': 'Full video',
                'score': 100,
                'segment_index': 0
            }]
        else:
            # Для длинных видео без транскрипции - делим на части по 30 секунд
            for i in range(0, int(duration), 30):
                start = i
                end = min(i + 30, duration)
                
                visual_score = analyze_visual_activity(video_path, start, min(end, start + 5))
                audio_score = analyze_audio_energy(video_path, start, end)
                
                viral_moments.append({
                    'start': start,
                    'end': end,
                    'text': f'Segment {i//30 + 1}',
                    'score': visual_score + audio_score,
                    'segment_index': i // 30
                })
    
    # Сортируем по скору
    viral_moments.sort(key=lambda x: x['score'], reverse=True)
    
    return viral_moments

def merge_adjacent_moments(moments, max_gap=2):
    """Объединяем соседние моменты для создания более длинных клипов"""
    if not moments:
        return []
    
    merged = []
    current = moments[0].copy()
    
    for moment in moments[1:]:
        # Если моменты близки по времени, объединяем
        if moment['start'] - current['end'] <= max_gap:
            current['end'] = moment['end']
            current['score'] = max(current['score'], moment['score'])
            current['text'] += ' ' + moment['text']
        else:
            merged.append(current)
            current = moment.copy()
    
    merged.append(current)
    return merged

def create_smart_clips(video_path, transcript):
    """Создаем умные клипы на основе анализа"""
    video_info = get_video_info(video_path)
    duration = video_info['duration']
    
    # Для очень коротких видео (меньше 60 секунд) - особая логика
    if duration <= 60:
        # Находим самый интересный момент
        segments = transcript.get('segments', [])
        
        if segments:
            # Ищем сегмент с самым интересным текстом
            best_segment = None
            best_score = 0
            
            for seg in segments:
                score = analyze_transcript_segment(seg)
                if score > best_score:
                    best_score = score
                    best_segment = seg
            
            if best_segment:
                # Берем время вокруг лучшего сегмента
                start = max(0, best_segment['start'] - 2)
                end = min(duration, best_segment['end'] + 2)
                
                # Минимум 10 секунд, максимум вся длина видео
                if end - start < 10 and duration >= 10:
                    padding = (10 - (end - start)) / 2
                    start = max(0, start - padding)
                    end = min(duration, end + padding)
            else:
                # Если нет сегментов, берем первые 10-15 секунд
                start = 0
                end = min(duration, 15)
        else:
            # Без транскрипции - берем начало
            start = 0
            end = min(duration, 15)
        
        clips = [{
            'index': 1,
            'start': start,
            'end': end,
            'duration': end - start,
            'score': 100,
            'text': 'Best moment',
            'filename': 'clip_01_score100.mp4',
            'path': '/data/clips/clip_01_score100.mp4'
        }]
        
        logging.info(f"Short video: created 1 clip from {start:.1f}s to {end:.1f}s")
        return clips
    
    # Для длинных видео - стандартная логика
    viral_moments = find_viral_moments(video_path, transcript, video_info)
    
    # Объединяем близкие моменты
    viral_moments = merge_adjacent_moments(viral_moments[:10])
    
    clips = []
    
    for i, moment in enumerate(viral_moments[:5]):
        duration = moment['end'] - moment['start']
        
        # Адаптивная длина клипа (от 15 до 60 секунд для оптимального вовлечения)
        if duration < 15:
            # Расширяем короткие моменты
            padding = (15 - duration) / 2
            moment['start'] = max(0, moment['start'] - padding)
            moment['end'] = min(video_info['duration'], moment['end'] + padding)
            duration = moment['end'] - moment['start']
        elif duration > 60:
            # Обрезаем слишком длинные - фокус на самом важном
            # Пытаемся сохранить начало момента
            moment['end'] = moment['start'] + 60
            duration = 60
        
        # Убеждаемся что клип не выходит за границы видео
        if moment['end'] > video_info['duration']:
            moment['end'] = video_info['duration']
            moment['start'] = max(0, moment['end'] - duration)
        
        # Финальная проверка длительности
        actual_duration = moment['end'] - moment['start']
        if actual_duration < 5:  # Слишком короткий клип не имеет смысла
            continue
        
        clip_filename = f"clip_{i+1:02d}_score{int(moment['score'])}.mp4"
        clip_path = os.path.join('/data/clips', clip_filename)
        
        clips.append({
            'index': len(clips) + 1,
            'start': round(moment['start'], 2),
            'end': round(moment['end'], 2),
            'duration': round(actual_duration, 2),
            'score': moment['score'],
            'text': moment['text'][:100] + '...' if len(moment['text']) > 100 else moment['text'],
            'filename': clip_filename,
            'path': clip_path
        })
    
    # Если нет клипов, создаем хотя бы один
    if not clips:
        duration = min(video_info['duration'], 30)
        clips = [{
            'index': 1,
            'start': 0,
            'end': duration,
            'duration': duration,
            'score': 50,
            'text': 'Full video clip',
            'filename': 'clip_01_score50.mp4',
            'path': '/data/clips/clip_01_score50.mp4'
        }]
    
    logging.info(f"Created {len(clips)} smart clips based on viral potential")
    return clips

def extract_clip(video_path, clip_info):
    """Извлекаем клип из видео"""
    start_time = clip_info['start']
    duration = clip_info['duration']
    output_path = clip_info['path']
    
    # Создаем папку если нет
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    cmd = [
        'ffmpeg', '-y',
        '-ss', str(start_time),
        '-t', str(duration),
        '-i', video_path,
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-crf', '22',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-movflags', '+faststart',
        output_path
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Проверяем что файл создан
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            logging.info(f"Successfully extracted clip {clip_info['index']}: {file_size} bytes")
            return True
        else:
            logging.error(f"Clip file not created: {output_path}")
            return False
            
    except subprocess.CalledProcessError as e:
        logging.error(f"FFmpeg error: {e.stderr.decode()}")
        return False

@app.route('/clip-video', methods=['POST'])
def clip_video():
    try:
        data = request.json
        video_path = data.get('video_path')
        transcript = data.get('transcript', {})
        
        if not video_path or not os.path.exists(video_path):
            return jsonify({'error': 'Video file not found'}), 400
        
        logging.info(f"Processing video: {video_path}")
        
        # Анализируем и создаем клипы
        clips = create_smart_clips(video_path, transcript)
        
        # Извлекаем клипы
        successful_clips = []
        for clip in clips:
            logging.info(f"Extracting clip {clip['index']}: {clip['start']}s - {clip['end']}s")
            if extract_clip(video_path, clip):
                successful_clips.append(clip)
        
        return jsonify({
            'status': 'success',
            'clips': successful_clips,
            'total_clips': len(successful_clips)
        })
        
    except Exception as e:
        logging.error(f"Error in clip_video: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    os.makedirs('/data/clips', exist_ok=True)
    app.run(host='0.0.0.0', port=3002)
