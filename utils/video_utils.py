import os
import time
import cv2
import numpy as np
from PIL import Image
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import QSize, Qt
import functools
import threading
from concurrent.futures import ThreadPoolExecutor

_metadata_cache = {}
_thumbnail_cache = {}
_CACHE_SIZE_LIMIT = 100

_thread_pool = ThreadPoolExecutor(max_workers=4)

SUPPORTED_VIDEO_EXTENSIONS = [
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".mpeg", ".mpg", ".3gp", ".3g2"
]

def is_video_file(file_path):
    _, ext = os.path.splitext(file_path)
    return ext.lower() in SUPPORTED_VIDEO_EXTENSIONS

@functools.lru_cache(maxsize=100)
def get_video_metadata(file_path):
    if not os.path.exists(file_path):
        return None
    
    if file_path in _metadata_cache:
        return _metadata_cache[file_path]
        
    try:
        cap = cv2.VideoCapture(file_path)
        
        if not cap.isOpened():
            cap.release()
            cap = cv2.VideoCapture(file_path, cv2.CAP_FFMPEG)
            
            if not cap.isOpened():
                print(f"Не удалось открыть файл: {file_path}")
                return None
            
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        duration = frame_count / fps if fps > 0 else 0
        
        if width <= 0 or height <= 0 or duration <= 0:
            if os.path.getsize(file_path) > 0:
                width = width if width > 0 else 1280
                height = height if height > 0 else 720
                duration = duration if duration > 0 else 60
        
        file_size = os.path.getsize(file_path)
        
        date_modified = time.ctime(os.path.getmtime(file_path))
        date_created = time.ctime(os.path.getctime(file_path))
        
        cap.release()
        
        result = {
            "width": width,
            "height": height,
            "fps": fps,
            "duration": duration,
            "size": file_size,
            "date_modified": date_modified,
            "date_created": date_created
        }
        
        if len(_metadata_cache) >= _CACHE_SIZE_LIMIT:
            _metadata_cache.clear()
            
        _metadata_cache[file_path] = result
        
        return result
        
    except Exception as e:
        print(f"Ошибка извлечения метаданных из {file_path}: {e}")
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        result = {
            "width": 1280,
            "height": 720,
            "fps": 30,
            "duration": 60,
            "size": file_size,
            "date_modified": time.ctime(os.path.getmtime(file_path)),
            "date_created": time.ctime(os.path.getctime(file_path))
        }
        return result

def extract_thumbnail(file_path, position=0.1, size=QSize(320, 180)):
    if not os.path.exists(file_path):
        return None
    
    cache_key = f"{file_path}_{position}_{size.width()}x{size.height()}"
    
    if cache_key in _thumbnail_cache:
        return _thumbnail_cache[cache_key]
        
    try:
        cap = cv2.VideoCapture(file_path, cv2.CAP_FFMPEG)
        
        if not cap.isOpened():
            print(f"Не удалось открыть файл для миниатюры: {file_path}")
            pixmap = QPixmap(size)
            pixmap.fill(Qt.darkGray)
            return pixmap
            
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if total_frames <= 0:
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0:
                fps = 25
                
            file_size = os.path.getsize(file_path)
            if file_size > 10000000:
                seek_pos = 5.0
            else:
                seek_pos = 1.0
                
            cap.set(cv2.CAP_PROP_POS_MSEC, seek_pos * 1000)
        else:
            target_frame = int(total_frames * position)
            if target_frame <= 0:
                target_frame = 1
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        
        ret, frame = cap.read()
        cap.release()
        
        if not ret or frame is None:
            print(f"Не удалось прочитать кадр из {file_path}")
            pixmap = QPixmap(size)
            pixmap.fill(Qt.darkGray)
            return pixmap
            
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        height, width, _ = frame.shape
        aspect_ratio = width / height
        
        if width > height:
            new_width = size.width()
            new_height = int(new_width / aspect_ratio)
        else:
            new_height = size.height()
            new_width = int(new_height * aspect_ratio)
            
        frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
        
        height, width, channel = frame.shape
        bytes_per_line = 3 * width
        q_img = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
        
        pixmap = QPixmap.fromImage(q_img)
        
        if pixmap.width() != size.width() or pixmap.height() != size.height():
            pixmap = pixmap.scaled(size, aspectRatioMode=Qt.KeepAspectRatio, transformMode=Qt.SmoothTransformation)
        
        if len(_thumbnail_cache) >= _CACHE_SIZE_LIMIT:
            _thumbnail_cache.clear()
            
        _thumbnail_cache[cache_key] = pixmap
        
        return pixmap
        
    except Exception as e:
        print(f"Ошибка извлечения миниатюры из {file_path}: {e}")
        pixmap = QPixmap(size)
        pixmap.fill(Qt.darkGray)
        return pixmap

def extract_thumbnail_async(file_path, callback, position=0.1, size=QSize(320, 180)):
    def _extract_and_callback():
        try:
            thumbnail = extract_thumbnail(file_path, position, size)
            callback(file_path, thumbnail)
        except Exception as e:
            print(f"Error in async thumbnail extraction: {e}")
    
    _thread_pool.submit(_extract_and_callback)

def format_file_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes/(1024*1024):.1f} MB"
    else:
        return f"{size_bytes/(1024*1024*1024):.1f} GB"

def format_duration(seconds):
    if seconds is None:
        return "Unknown"
        
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"

def create_preview_clip(file_path, output_path, start_time=0, duration=3):
    try:
        os.system(f'ffmpeg -i "{file_path}" -ss {start_time} -t {duration} -c:v libx264 -c:a aac -strict experimental -b:a 128k "{output_path}" -y -loglevel error')
        return True
    except Exception as e:
        print(f"Error creating preview clip: {e}")
        return False

def clear_caches():
    _metadata_cache.clear()
    _thumbnail_cache.clear()