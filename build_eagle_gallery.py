import os
import json
import sqlite3
from pathlib import Path
from tqdm import tqdm

DB_PATH = "eagle_gallery.db"
LIBRARY_PATH = "/mnt/monitoring/@GP66_D드라이브 백업/my-eagle/Design.library/images"

def init_db():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.execute("PRAGMA journal_mode=WAL;")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS items
                 (id TEXT PRIMARY KEY, name TEXT, ext TEXT, tags TEXT, 
                  annotation TEXT, url TEXT, thumbnail_path TEXT, original_path TEXT)''')
    conn.commit()
    return conn

def build_index():
    conn = init_db()
    c = conn.cursor()
    
    print(f"Scanning {LIBRARY_PATH}...")
    # Find all .info directories
    info_dirs = [d for d in os.listdir(LIBRARY_PATH) if d.endswith('.info')]
    
    count = 0
    batch_data = []
    
    for info_dir in tqdm(info_dirs):
        dir_path = os.path.join(LIBRARY_PATH, info_dir)
        meta_path = os.path.join(dir_path, "metadata.json")
        
        if not os.path.exists(meta_path):
            continue
            
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
                
            item_id = meta.get('id', info_dir.replace('.info', ''))
            name = meta.get('name', '')
            ext = meta.get('ext', '')
            tags = json.dumps(meta.get('tags', []))
            annotation = meta.get('annotation', '')
            url = meta.get('url', '')
            
            # Find thumbnail and original (assuming naming convention)
            files = os.listdir(dir_path)
            thumbnail = next((f for f in files if '_thumbnail.' in f), None)
            original = next((f for f in files if f != 'metadata.json' and not f.endswith('.info') and '_thumbnail' not in f), None)
            
            thumb_path = os.path.join(dir_path, thumbnail) if thumbnail else ""
            orig_path = os.path.join(dir_path, original) if original else ""
            
            batch_data.append((item_id, name, ext, tags, annotation, url, thumb_path, orig_path))
            
            count += 1
            if count % 1000 == 0:
                c.executemany('INSERT OR REPLACE INTO items VALUES (?,?,?,?,?,?,?,?)', batch_data)
                conn.commit()
                batch_data = []
                
        except Exception as e:
            pass # Skip corrupted files
            
    if batch_data:
        c.executemany('INSERT OR REPLACE INTO items VALUES (?,?,?,?,?,?,?,?)', batch_data)
        
    conn.commit()
    conn.close()
    print(f"Indexed {count} items into {DB_PATH}")

if __name__ == "__main__":
    build_index()
