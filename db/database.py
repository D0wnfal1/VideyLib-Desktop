import os
import sqlite3
import json
from PyQt5.QtCore import QDir

class Database:
    def __init__(self):
        self.app_data_dir = os.path.join(QDir.homePath(), ".videolibrary")
        self.db_path = os.path.join(self.app_data_dir, "videolibrary.db")
        
        os.makedirs(self.app_data_dir, exist_ok=True)
        
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE,
                file_name TEXT,
                folder_path TEXT,
                size INTEGER,
                duration INTEGER,
                watched INTEGER DEFAULT 0,
                last_watched TEXT,
                last_position INTEGER DEFAULT 0,
                date_added TEXT,
                date_modified TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS video_tags (
                video_id INTEGER,
                tag_id INTEGER,
                PRIMARY KEY (video_id, tag_id),
                FOREIGN KEY (video_id) REFERENCES videos (id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                video_id INTEGER PRIMARY KEY,
                content TEXT,
                FOREIGN KEY (video_id) REFERENCES videos (id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id INTEGER,
                rating INTEGER,
                review_text TEXT,
                date_added TEXT,
                FOREIGN KEY (video_id) REFERENCES videos (id) ON DELETE CASCADE
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_video(self, file_path, file_name, folder_path, size, duration, date_added, date_modified):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO videos 
            (file_path, file_name, folder_path, size, duration, date_added, date_modified)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (file_path, file_name, folder_path, size, duration, date_added, date_modified))
        
        video_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return video_id
    
    def get_video_by_path(self, file_path):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM videos WHERE file_path = ?", (file_path,))
        video = cursor.fetchone()
        
        conn.close()
        
        return dict(video) if video else None
    
    def update_watched_status(self, video_id, watched, last_position=0, last_watched=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE videos 
            SET watched = ?, last_position = ?, last_watched = ?
            WHERE id = ?
        ''', (1 if watched else 0, last_position, last_watched, video_id))
        
        conn.commit()
        conn.close()
    
    def add_tag(self, name):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (name,))
        cursor.execute("SELECT id FROM tags WHERE name = ?", (name,))
        tag_id = cursor.fetchone()[0]
        
        conn.commit()
        conn.close()
        
        return tag_id
    
    def add_video_tag(self, video_id, tag_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("INSERT OR IGNORE INTO video_tags (video_id, tag_id) VALUES (?, ?)", 
                      (video_id, tag_id))
        
        conn.commit()
        conn.close()
    
    def remove_video_tag(self, video_id, tag_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM video_tags WHERE video_id = ? AND tag_id = ?", 
                      (video_id, tag_id))
        
        conn.commit()
        conn.close()
    
    def get_video_tags(self, video_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT t.id, t.name
            FROM tags t
            JOIN video_tags vt ON t.id = vt.tag_id
            WHERE vt.video_id = ?
        ''', (video_id,))
        
        tags = [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]
        
        conn.close()
        
        return tags
    
    def save_note(self, video_id, content):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO notes (video_id, content)
            VALUES (?, ?)
        ''', (video_id, content))
        
        conn.commit()
        conn.close()
    
    def get_note(self, video_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT content FROM notes WHERE video_id = ?", (video_id,))
        result = cursor.fetchone()
        
        conn.close()
        
        return result[0] if result else ""
    
    def search_videos(self, query="", folder=None, tags=None, watched=None):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        params = []
        conditions = []
        
        if query:
            conditions.append("v.file_name LIKE ?")
            params.append(f"%{query}%")
        
        if folder:
            conditions.append("v.folder_path = ?")
            params.append(folder)
        
        if watched is not None:
            conditions.append("v.watched = ?")
            params.append(1 if watched else 0)
        
        sql = "SELECT DISTINCT v.* FROM videos v"
        
        if tags:
            sql += " JOIN video_tags vt ON v.id = vt.video_id JOIN tags t ON vt.tag_id = t.id"
            tag_conditions = []
            for tag in tags:
                tag_conditions.append("t.name = ?")
                params.append(tag)
            conditions.append("(" + " OR ".join(tag_conditions) + ")")
        
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        
        cursor.execute(sql, params)
        
        videos = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return videos
    
    def get_all_tags(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, name FROM tags ORDER BY name")
        
        tags = [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]
        
        conn.close()
        
        return tags
    
    def add_review(self, video_id, rating, review_text, date_added):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO reviews (video_id, rating, review_text, date_added)
            VALUES (?, ?, ?, ?)
        ''', (video_id, rating, review_text, date_added))
        
        review_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return review_id

    def update_review(self, review_id, rating, review_text):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE reviews
            SET rating = ?, review_text = ?
            WHERE id = ?
        ''', (rating, review_text, review_id))
        
        conn.commit()
        conn.close()

    def get_review(self, video_id):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, rating, review_text, date_added
            FROM reviews
            WHERE video_id = ?
            ORDER BY date_added DESC
            LIMIT 1
        ''', (video_id,))
        
        review = cursor.fetchone()
        
        conn.close()
        
        return dict(review) if review else None

    def get_all_reviews(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT r.id, r.video_id, v.file_name, r.rating, r.review_text, r.date_added
            FROM reviews r
            JOIN videos v ON r.video_id = v.id
            ORDER BY r.date_added DESC
        ''')
        
        reviews = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return reviews