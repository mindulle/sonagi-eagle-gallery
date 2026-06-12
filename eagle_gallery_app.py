import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

DB_PATH = 'eagle_gallery.db'

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn

@app.get('/api/items')
def get_items(limit: int = 50, offset: int = 0, search: str = ''):
    conn = get_db()
    c = conn.cursor()
    
    query = 'SELECT * FROM items'
    params = []
    
    if search:
        query += ' WHERE name LIKE ? OR tags LIKE ?'
        search_term = '%' + search + '%'
        params.extend([search_term, search_term])
        
    query += ' ORDER BY id DESC LIMIT ? OFFSET ?'
    params.extend([limit, offset])
    
    c.execute(query, params)
    rows = c.fetchall()
    
    items = []
    for r in rows:
        items.append({
            'id': r['id'],
            'name': r['name'],
            'ext': r['ext'],
            'tags': json.loads(r['tags']) if r['tags'] else [],
            'has_thumbnail': bool(r['thumbnail_path'])
        })
    
    conn.close()
    return items

@app.get('/api/image/{item_id}/{type}')
def get_image(item_id: str, type: str):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT thumbnail_path, original_path FROM items WHERE id = ?', (item_id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        return HTMLResponse(status_code=404, content='Not found')
        
    path = row['thumbnail_path'] if type == 'thumbnail' else row['original_path']
    if path and os.path.exists(path):
        return FileResponse(path)
    return HTMLResponse(status_code=404, content='File not found')

@app.get('/')
def index():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sonagi Eagle Gallery</title>
        <style>
            body { font-family: sans-serif; background: #f0f2f5; margin: 0; padding: 20px; }
            .header { text-align: center; margin-bottom: 20px; display: flex; justify-content: center; align-items: center; gap: 10px;}
            #search { padding: 10px; width: 300px; border-radius: 5px; border: 1px solid #ccc; font-size: 16px; }
            button { padding: 10px 20px; border-radius: 5px; border: none; background: #007bff; color: white; font-size: 16px; cursor: pointer; transition: background 0.2s; }
            button:hover { background: #0056b3; }
            .gallery { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px; }
            .card { background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.1); cursor: pointer; transition: transform 0.2s; }
            .card:hover { transform: translateY(-5px); }
            .card img { width: 100%; height: 200px; object-fit: cover; display: block; background: #ddd; }
            .card-info { padding: 10px; }
            .card-title { font-size: 14px; margin: 0 0 5px 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
            .tag { display: inline-block; background: #e1e4e8; font-size: 11px; padding: 2px 6px; border-radius: 3px; margin: 2px 2px 0 0; color: #555; }
            #loading { text-align: center; padding: 20px; display: none; }
        </style>
    </head>
    <body>
        <div class="header">
            <input type="text" id="search" placeholder="Search tags or names..." onkeyup="if(event.key==='Enter') searchItems()">
            <button onclick="searchItems()">Search</button>
        </div>
        <div class="gallery" id="gallery"></div>
        <div id="loading">Loading more...</div>

        <script>
            let offset = 0;
            let currentSearch = '';
            let isLoading = false;
            
            window.onload = () => {
                const urlParams = new URLSearchParams(window.location.search);
                const querySearch = urlParams.get('search');
                if (querySearch) {
                    currentSearch = querySearch;
                    document.getElementById('search').value = currentSearch;
                }
                loadItems();
            };
            
            async function loadItems() {
                if(isLoading) return;
                isLoading = true;
                document.getElementById('loading').style.display = 'block';
                
                try {
                    const res = await fetch(`/api/items?limit=50&offset=${offset}&search=${encodeURIComponent(currentSearch)}`);
                    const items = await res.json();
                    
                    const gallery = document.getElementById('gallery');
                    if(offset === 0) gallery.innerHTML = '';
                    
                    items.forEach(item => {
                        const card = document.createElement('div');
                        card.className = 'card';
                        card.onclick = () => window.open(`/api/image/${item.id}/original`, '_blank');
                        
                        const imgSrc = item.has_thumbnail ? `/api/image/${item.id}/thumbnail` : `/api/image/${item.id}/original`;
                        const tagsHtml = item.tags.slice(0,3).map(t => `<span class=tag>${t}</span>`).join('');
                        const itemName = item.name || 'Untitled';
                        
                        card.innerHTML = `
                            <img src=${imgSrc} loading=lazy onerror=this.style.display=none>
                            <div class=card-info>
                                <h3 class=card-title>${itemName}</h3>
                                <div>${tagsHtml}</div>
                            </div>
                        `;
                        gallery.appendChild(card);
                    });
                    
                    offset += 50;
                } catch(e) {
                    console.error(e);
                } finally {
                    isLoading = false;
                    document.getElementById('loading').style.display = 'none';
                }
            }
            
            function searchItems() {
                currentSearch = document.getElementById('search').value;
                offset = 0;
                
                const newUrl = new URL(window.location.href);
                if (currentSearch) {
                    newUrl.searchParams.set('search', currentSearch);
                } else {
                    newUrl.searchParams.delete('search');
                }
                window.history.pushState({}, '', newUrl.toString());
                
                loadItems();
            }
            
            window.onscroll = () => {
                if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight - 500) {
                    loadItems();
                }
            };
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
