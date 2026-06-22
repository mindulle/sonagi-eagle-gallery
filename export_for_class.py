# ruff: noqa: E501, E701
import json
import os
import shutil
import sqlite3

def export_project():
    OUTPUT_DIR = "submission_ready"
    IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")
    
    os.makedirs(IMAGES_DIR, exist_ok=True)
    
    conn = sqlite3.connect("eagle_gallery.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Fetch 40 items with tags
    c.execute("SELECT * FROM items WHERE tags != '[]' AND tags != '' AND tags IS NOT NULL ORDER BY id DESC LIMIT 40")
    tagged_rows = c.fetchall()
    
    # Fetch 20 items without tags (or random others)
    c.execute("SELECT * FROM items WHERE tags = '[]' OR tags = '' OR tags IS NULL ORDER BY id DESC LIMIT 20")
    untagged_rows = c.fetchall()
    
    rows = tagged_rows + untagged_rows
    
    items_data = []
    for r in rows:
        item_id = r["id"]
        ext = r["ext"]
        thumb_src = r["thumbnail_path"]
        orig_src = r["original_path"]
        
        local_thumb = f"{item_id}_thumb.png"
        local_orig = f"{item_id}.{ext}" if ext else f"{item_id}_orig"
        
        has_thumbnail = False
        if thumb_src and os.path.exists(thumb_src):
            try:
                shutil.copy2(thumb_src, os.path.join(IMAGES_DIR, local_thumb))
                has_thumbnail = True
            except Exception: pass
            
        if orig_src and os.path.exists(orig_src):
            try:
                shutil.copy2(orig_src, os.path.join(IMAGES_DIR, local_orig))
            except Exception: pass
            
        items_data.append({
            "id": item_id,
            "name": r["name"],
            "ext": ext,
            "tags": json.loads(r["tags"]) if r["tags"] else [],
            "annotation": r["annotation"],
            "url": r["url"],
            "has_thumbnail": has_thumbnail,
            "thumb_url": f"images/{local_thumb}",
            "orig_url": f"images/{local_orig}"
        })
        
    curated_ids = [r["id"] for r in rows]
    placeholders = ",".join("?" for _ in curated_ids)
    
    c.execute(f"""
        SELECT value as tag, count(*) as count 
        FROM items, json_each(items.tags) 
        WHERE items.id IN ({placeholders})
        GROUP BY value 
        ORDER BY count DESC LIMIT 10
    """, curated_ids)
    tags_data = [{"tag": row["tag"], "count": row["count"]} for row in c.fetchall()]
    
    c.execute(f"""
        SELECT ext, count(*) as count 
        FROM items 
        WHERE ext != '' AND ext IS NOT NULL
        AND items.id IN ({placeholders})
        GROUP BY ext 
        ORDER BY count DESC LIMIT 10
    """, curated_ids)
    exts_data = [{"ext": row["ext"], "count": row["count"]} for row in c.fetchall()]
    
    conn.close()

    export_data = {
        "items": items_data,
        "tags": tags_data,
        "exts": exts_data
    }
    
    # Save as data.json instead of data.js
    with open(os.path.join(OUTPUT_DIR, "data.json"), "w", encoding="utf-8") as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)

    html_index = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Eagle Gallery - Home</title>
    <link rel="stylesheet" href="style.css">
    <script src="https://code.jquery.com/jquery-4.0.0-beta.min.js"></script>
    <script src="main.js" defer></script>
</head>
<body>
    <header>
        <h1>Sonagi Eagle Gallery</h1>
        <nav>
            <ul>
                <li><a href="index.html" class="active">Home</a></li>
                <li><a href="content.html">Content</a></li>
                <li><a href="about.html">About</a></li>
            </ul>
        </nav>
    </header>
    
    <main class="layout">
        <aside class="sidebar">
            <section class="sidebar-section">
                <h3>Extensions</h3>
                <ul id="ext-list" class="filter-list"></ul>
            </section>
            <section class="sidebar-section">
                <h3>Tags</h3>
                <ul id="tag-list" class="filter-list"></ul>
            </section>
        </aside>
        
        <article class="main-content">
            <div class="search-bar">
                <input type="text" id="search" placeholder="Search by name or tag...">
            </div>
            <div class="gallery" id="gallery">
                <div class="loading-msg">Loading data.json...<br><small>(로컬 환경 실행 시 Live Server 등 웹 서버가 필요합니다)</small></div>
            </div>
        </article>
    </main>

    <!-- Modal -->
    <div id="lightbox" class="lightbox">
        <div class="lightbox-overlay"></div>
        <div class="lightbox-content">
            <button class="close-btn">&times;</button>
            <div class="lightbox-image-container" id="modal-img-wrapper"></div>
            <div class="lightbox-info" id="modal-info"></div>
        </div>
    </div>

    <footer>
        <p>&copy; 2026 Web Programming Assignment - Sonagi</p>
    </footer>
</body>
</html>"""

    html_content = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Eagle Gallery - Content Detail</title>
    <link rel="stylesheet" href="style.css">
    <script src="https://code.jquery.com/jquery-4.0.0-beta.min.js"></script>
    <script>
    $(async function() {
        try {
            const response = await fetch('data.json');
            if (!response.ok) throw new Error('Network response was not ok');
            const data = await response.json();
            
            const params = new URLSearchParams(location.search);
            const id = params.get('id');
            if (!id) return showError("아이템 ID가 지정되지 않았습니다. 갤러리에서 항목을 선택해주세요.");
            
            const item = data.items.find(i => i.id === id);
            if (!item) return showError("해당 아이템을 찾을 수 없습니다.");
            
            renderDetail(item);
        } catch (error) {
            console.error(error);
            showError("data.json 데이터를 불러오는데 실패했습니다. (CORS 정책 제한 또는 파일 누락)");
        }
    });

    function showError(msg) {
        $('#detail-container').html(`<div class="not-found"><h2>${msg}</h2><br><a href="index.html" class="btn-secondary">갤러리로 돌아가기</a></div>`);
    }

    function renderDetail(item) {
        const imgSrc = item.orig_url;
        $('#d-image').attr('src', imgSrc).on('error', function() { $(this).hide(); });
        
        $('#d-name').text(item.name || 'Untitled');
        $('#d-ext').text(item.ext ? item.ext.toUpperCase() : 'Unknown');
        
        const $tags = $('#d-tags');
        if (item.tags && item.tags.length > 0) {
            $.each(item.tags, function(i, t) {
                $tags.append($('<a>', { href: `index.html?tag=${encodeURIComponent(t)}`, class: 'tag tag-link', text: t }));
            });
        } else {
            $tags.text('None');
        }
        
        if (item.url) {
            $('#d-url').append($('<a>', { href: item.url, target: '_blank', rel: 'noopener noreferrer', text: item.url }));
        } else {
            $('#d-url').text('N/A');
        }
        
        const $note = $('#d-note');
        if (item.annotation) {
            $note.addClass('note-box').text(item.annotation);
        } else {
            $note.text('N/A');
        }
    }
    </script>
</head>
<body>
    <header>
        <h1>Sonagi Eagle Gallery</h1>
        <nav>
            <ul>
                <li><a href="index.html">Home</a></li>
                <li><a href="content.html" class="active">Content</a></li>
                <li><a href="about.html">About</a></li>
            </ul>
        </nav>
    </header>
    <main class="page-layout">
        <div class="top-bar">
            <a href="index.html" class="btn-secondary">&larr; 갤러리로 돌아가기</a>
        </div>
        <div id="detail-container" class="detail-layout">
            <div class="detail-image">
                <img id="d-image" src="" alt="Detail Image">
            </div>
            <div class="detail-meta">
                <h2 id="d-name"></h2>
                <dl class="meta-list">
                    <dt>Extension</dt>
                    <dd id="d-ext"></dd>
                    
                    <dt>Tags</dt>
                    <dd id="d-tags"></dd>
                    
                    <dt>Source URL</dt>
                    <dd id="d-url"></dd>
                    
                    <dt>Annotation</dt>
                    <dd id="d-note"></dd>
                </dl>
            </div>
        </div>
    </main>
    <footer>
        <p>&copy; 2026 Web Programming Assignment - Sonagi</p>
    </footer>
</body>
</html>"""

    html_about = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Eagle Gallery - About</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <header>
        <h1>Sonagi Eagle Gallery</h1>
        <nav>
            <ul>
                <li><a href="index.html">Home</a></li>
                <li><a href="content.html">Content</a></li>
                <li><a href="about.html" class="active">About</a></li>
            </ul>
        </nav>
    </header>
    <main class="page-layout about-layout">
        <section class="tech-section">
            <h3>1. 프로젝트 개요 (Project Overview)</h3>
            <p>본 프로젝트는 3학년 1학기 '인터넷과 웹 기초' 수업의 기말 과제 제출용으로 제작된 <b>정적 웹 갤러리</b>입니다. 실제 서버(FastAPI)에서 구동 중인 Eagle Gallery 데이터베이스의 항목들을 순수 HTML/CSS/JS 환경에서 탐색할 수 있도록 정적 덤프(Static Export)하여 구현했습니다.</p>
        </section>
        
        <section class="tech-section">
            <h3>2. 비동기 데이터 로딩 (Fetch API & JSON)</h3>
            <p>수업 시간에 배운 <code>Fetch API</code>와 <code>async/await</code> 키워드를 활용하여 서버 역할을 하는 <code>data.json</code> 파일에서 비동기적으로 갤러리 데이터를 불러옵니다. 과제 제출 규정에 따라 데이터를 분리된 JSON 형식으로 관리하며, 네트워크 지연을 고려해 데이터를 모두 받을 때까지 대기(await)한 후 화면 렌더링을 시작합니다.</p>
            <div class="code-block"><pre><code>// main.js - Fetch API 데이터 호출 발췌
let galleryData = { items: [], tags: [], exts: [] };

$(async function() {
    try {
        const response = await fetch('data.json');
        if (!response.ok) throw new Error('Network error');
        
        galleryData = await response.json(); // JSON 파싱 완료 대기
        
        renderSidebar(galleryData); // 사이드바 렌더링
        renderGallery(galleryData.items); // 갤러리 렌더링
    } catch (error) {
        console.error("데이터 로드 실패:", error);
    }
});</code></pre></div>
        </section>

        <section class="tech-section">
            <h3>3. jQuery DOM 동적 렌더링 (Dynamic DOM Rendering)</h3>
            <p>불러온 JSON 배열을 순회하며 동적으로 HTML 요소를 생성하고 화면에 부착(Append)합니다. 수업에서 다룬 배열 순회 방식과 더불어, 허용된 <code>jQuery 4.0.0-beta</code>의 <code>$.each()</code> 유틸리티 및 <code>$('&lt;tag&gt;')</code> 팩토리 함수를 조합하여 직관적이고 캡슐화된 DOM 조작을 구현했습니다.</p>
            <div class="code-block"><pre><code>// main.js - 갤러리 렌더링 발췌
function renderGallery(items) {
    const $gallery = $('#gallery').empty();

    $.each(items, function(i, item) {
        const $card = $('&lt;div&gt;', { class: 'card' }).on('click', () => openModal(item));
        const $img = $('&lt;img&gt;', { src: item.thumb_url, loading: 'lazy' });
        
        const $info = $('&lt;div&gt;', { class: 'card-info' });
        $info.append($('&lt;h3&gt;', { class: 'card-title', text: item.name }));
        
        $card.append($img).append($info);
        $gallery.append($card);
    });
}</code></pre></div>
        </section>

        <section class="tech-section">
            <h3>4. 배열 메서드를 활용한 검색/필터링 (Array Filtering)</h3>
            <p>사이드바의 태그를 클릭하거나 상단 검색바에 텍스트를 입력하면, 자바스크립트의 내장 배열 메서드인 <code>Array.prototype.filter()</code>와 <code>some()</code>을 사용하여 조건에 맞는 아이템만 새 배열로 추출한 후 갤러리 영역을 즉시 재렌더링합니다.</p>
            <div class="code-block"><pre><code>// main.js - 검색 필터링 발췌
function filterGallery(term) {
    term = term.toLowerCase();
    const filtered = galleryData.items.filter(item => {
        const matchName = (item.name || '').toLowerCase().includes(term);
        const matchTags = item.tags.some(t => t.toLowerCase().includes(term));
        const matchExt = (item.ext || '').toLowerCase().includes(term);
        
        return matchName || matchTags || matchExt;
    });
    renderGallery(filtered);
}</code></pre></div>
        </section>

        <section class="tech-section">
            <h3>5. 반응형 CSS Masonry 레이아웃 (Responsive Layout)</h3>
            <p>높이가 제각각인 이미지들을 빈틈없이 정렬하기 위해 무거운 서드파티 JS 라이브러리를 배제하고, CSS3의 다단 편집 기능인 <code>column-count</code>와 <code>break-inside: avoid</code> 속성을 조합하여 가볍고 반응형에 최적화된 벽돌형(Masonry) 그리드를 순수 CSS로 구현했습니다.</p>
            <div class="code-block"><pre><code>/* style.css */
.gallery { 
    column-count: 4; 
    column-gap: 20px; 
}
.card { 
    display: inline-block; 
    width: 100%; 
    break-inside: avoid; /* 카드가 단 사이에서 쪼개지는 것 방지 */
    margin-bottom: 20px;
}
/* 화면 크기에 따른 미디어 쿼리 */
@media (max-width: 1024px) { .gallery { column-count: 3; } }
@media (max-width: 768px) { .gallery { column-count: 2; } }</code></pre></div>
        </section>
    </main>
    <footer>
        <p>&copy; 2026 Web Programming Assignment - Sonagi</p>
    </footer>
</body>
</html>"""

    css_content = """* { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, sans-serif; }
body { background: #faf9f7; color: #333; display: flex; flex-direction: column; min-height: 100vh; }
header { background: #1991B9; color: white; padding: 20px; display: flex; justify-content: space-between; align-items: center; }
nav ul { list-style: none; display: flex; gap: 20px; }
nav a { color: white; text-decoration: none; opacity: 0.8; font-weight: bold; }
nav a:hover, nav a.active { opacity: 1; text-decoration: underline; }
.layout { display: flex; flex: 1; }
.sidebar { width: 250px; background: #fff; border-right: 1px solid #eee; padding: 20px; }
.sidebar-section { margin-bottom: 20px; }
.filter-list { list-style: none; }
.filter-list li { padding: 8px; cursor: pointer; display: flex; justify-content: space-between; border-radius: 4px; }
.filter-list li:hover { background: #f0f8fb; color: #1991B9; }
.count { color: #aaa; background: #eee; padding: 2px 6px; border-radius: 12px; font-size: 0.8em; }
.main-content { flex: 1; padding: 20px; }
.search-bar { margin-bottom: 20px; }
.search-bar input { width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 4px; }
.loading-msg { padding: 40px; text-align: center; color: #666; font-size: 1.2em; width: 100%; grid-column: 1 / -1; }
.gallery { column-count: 4; column-gap: 20px; }
.card { background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; break-inside: avoid; display: inline-block; width: 100%; cursor: pointer; }
.card img { width: 100%; display: block; background: #f4f4f4; min-height: 100px; }
.card-info { padding: 15px; }
.card-title { font-size: 1em; margin-bottom: 10px; line-height: 1.4; word-break: break-all; }
.tag { display: inline-block; background: #eee; padding: 4px 8px; border-radius: 4px; font-size: 0.8em; margin: 2px; }
footer { background: #333; color: white; text-align: center; padding: 20px; margin-top: auto; }
.lightbox { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 1000; }
.lightbox-overlay { position: absolute; width: 100%; height: 100%; background: rgba(0,0,0,0.8); }
.lightbox-content { position: relative; width: 80%; height: 80%; background: white; margin: 5% auto; display: flex; border-radius: 8px; overflow: hidden; }
.lightbox-image-container { flex: 2; background: #f4f4f4; display: flex; align-items: center; justify-content: center; padding: 20px; }
.lightbox-image-container img { max-width: 100%; max-height: 100%; object-fit: contain; }
.lightbox-info { flex: 1; padding: 30px; overflow-y: auto; }
.lightbox-info h2 { font-size: 1.5em; margin-bottom: 15px; line-height: 1.4; word-break: break-all; }
.close-btn { position: absolute; top: 10px; right: 20px; background: none; border: none; font-size: 2em; cursor: pointer; }

/* Content Details Page */
.page-layout { padding: 40px; max-width: 1200px; margin: 0 auto; flex: 1; width: 100%; }
.about-layout { max-width: 900px; }
.top-bar { margin-bottom: 20px; }
.btn-secondary { display: inline-block; padding: 8px 16px; background: #eee; color: #333; text-decoration: none; border-radius: 4px; font-size: 0.9em; transition: background 0.2s; font-weight: bold; }
.btn-secondary:hover { background: #ddd; }
.detail-layout { display: flex; gap: 40px; background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
.detail-image { flex: 2; display: flex; align-items: center; justify-content: center; background: #f4f4f4; border-radius: 8px; padding: 20px; min-height: 400px; }
.detail-image img { max-width: 100%; max-height: 70vh; object-fit: contain; }
.detail-meta { flex: 1; }
.detail-meta h2 { margin-bottom: 20px; font-size: 1.5em; border-bottom: 2px solid #1991B9; padding-bottom: 10px; line-height: 1.4; word-break: break-all; }
.meta-list dt { font-weight: bold; color: #666; font-size: 0.9em; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }
.meta-list dd { margin-bottom: 20px; word-break: break-all; line-height: 1.5; }
.tag-link { cursor: pointer; text-decoration: none; color: #333; }
.tag-link:hover { background: #1991B9; color: white; }
.note-box { background: #f9f9f9; padding: 12px; border-left: 3px solid #ccc; font-style: italic; color: #555; }
.not-found { text-align: center; padding: 100px 20px; }
.not-found h2 { margin-bottom: 20px; color: #999; }
.detail-link { display: inline-block; margin-top: 15px; color: #1991B9; text-decoration: none; font-weight: bold; }
.detail-link:hover { text-decoration: underline; }

/* About Page */
.tech-section { background: #fff; border-radius: 8px; padding: 30px; margin-bottom: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
.tech-section h3 { border-left: 4px solid #1991B9; padding-left: 12px; margin-bottom: 16px; color: #333; font-size: 1.2em; }
.tech-section p { margin-bottom: 15px; line-height: 1.6; color: #444; }
.tech-section b { color: #1991B9; }
.code-block { background: #1e1e1e; color: #d4d4d4; padding: 20px; border-radius: 6px; overflow-x: auto; font-family: 'Consolas', monospace; font-size: 0.9em; line-height: 1.5; margin-top: 15px; }

@media (max-width: 1024px) { .gallery { column-count: 3; } }
@media (max-width: 768px) { 
    .layout { flex-direction: column; } 
    .gallery { column-count: 2; } 
    .lightbox-content { flex-direction: column; } 
    .detail-layout { flex-direction: column; }
}
"""

    js_content = """let galleryData = { items: [], tags: [], exts: [] };

$(async function() {
    // 1. Fetch data.json asynchronously
    try {
        const response = await fetch('data.json');
        if (!response.ok) throw new Error('Network response was not ok');
        
        galleryData = await response.json();
        
        // 2. Render UI
        renderSidebar(galleryData);
        renderGallery(galleryData.items);

        // 3. Check for tag URL parameter
        const initTag = new URLSearchParams(location.search).get('tag');
        if (initTag) {
            $('#search').val(initTag);
            filterGallery(initTag);
        }
    } catch (error) {
        console.error("Data fetch error:", error);
        $('#gallery').html('<div class="loading-msg" style="color: #c0392b;"><b>데이터 로드 실패</b><br>data.json 파일을 불러오지 못했습니다.<br><small>로컬에서 실행 시 CORS 보안 정책으로 차단되었을 수 있습니다. VSCode Live Server 등을 통해 실행해주세요.</small></div>');
    }

    // Event Listeners
    $('#search').on('keyup', function() {
        const term = $(this).val().toLowerCase();
        filterGallery(term);
    });

    $('.close-btn, .lightbox-overlay').on('click', function() {
        $('#lightbox').fadeOut(200);
    });
    
    $(document).on('keydown', function(e) {
        if (e.key === 'Escape') $('#lightbox').fadeOut(200);
    });
});

function renderSidebar(data) {
    const $tagList = $('#tag-list');
    const $extList = $('#ext-list');

    $.each(data.tags, function(i, t) {
        const $li = $('<li>');
        const $label = $('<span>').text('# ' + t.tag);
        const $count = $('<span>', { class: 'count', text: t.count });
        $li.append($label).append(' ').append($count);
        $li.on('click', () => { $('#search').val(t.tag); filterGallery(t.tag); });
        $tagList.append($li);
    });

    $.each(data.exts, function(i, e) {
        const $li = $('<li>');
        const $label = $('<span>').text('. ' + e.ext.toUpperCase());
        const $count = $('<span>', { class: 'count', text: e.count });
        $li.append($label).append(' ').append($count);
        $li.on('click', () => { $('#search').val(e.ext); filterGallery(e.ext); });
        $extList.append($li);
    });
}

function renderGallery(items) {
    const $gallery = $('#gallery');
    $gallery.empty();

    if (items.length === 0) {
        $gallery.append($('<p>', { text: 'No results found.' }));
        return;
    }

    $.each(items, function(i, item) {
        const imgSrc = item.has_thumbnail ? item.thumb_url : item.orig_url;
        
        const $card = $('<div>', { class: 'card' }).on('click', () => openModal(item));
        const $img = $('<img>', { src: imgSrc, loading: 'lazy' });
        
        $img.on('error', function() {
            $(this).css('display', 'none');
            $(this).parent().css({ 'min-height': '150px', 'background': '#f4f4f4' });
        });
        
        const $info = $('<div>', { class: 'card-info' });
        $info.append($('<h3>', { class: 'card-title', text: item.name || 'Untitled' }));
        
        const $tags = $('<div>');
        if (item.ext) {
            $tags.append($('<span>', { class: 'tag', style: 'background:#1991B9; color:white;', text: item.ext.toUpperCase() }));
        }
        $.each(item.tags.slice(0, 3), function(_, t) {
            $tags.append($('<span>', { class: 'tag', text: t }));
        });
        
        $info.append($tags);
        $card.append($img).append($info);
        $gallery.append($card);
    });
}

function filterGallery(term) {
    term = term.toLowerCase();
    const filtered = galleryData.items.filter(item => {
        const matchName = (item.name || '').toLowerCase().includes(term);
        const matchTags = item.tags.some(t => t.toLowerCase().includes(term));
        const matchExt = (item.ext || '').toLowerCase().includes(term);
        return matchName || matchTags || matchExt;
    });
    renderGallery(filtered);
}

function openModal(item) {
    const $img = $('<img>', { src: item.orig_url });
    $img.on('error', function() { $(this).hide(); });
    $('#modal-img-wrapper').empty().append($img);
    
    const $info = $('#modal-info').empty();
    $info.append($('<h2>', { text: item.name || 'Untitled' }));
    
    const $extP = $('<p>').html('<strong>Ext:</strong> ');
    $extP.append(document.createTextNode(item.ext || 'Unknown'));
    $info.append($extP);
    
    if (item.url) {
        const $sourceP = $('<p>').html('<strong>Source:</strong> ');
        $sourceP.append($('<a>', { href: item.url, target: '_blank', rel: 'noopener noreferrer', text: 'Link' }));
        $info.append($sourceP);
    }
    
    if (item.annotation) {
        const $noteP = $('<p>').html('<strong>Note:</strong> ');
        $noteP.append(document.createTextNode(item.annotation));
        $info.append($noteP);
    }
    
    $info.append($('<hr>', { style: 'margin: 20px 0; border: 0; border-top: 1px solid #eee;' }));
    $info.append($('<a>', {
        href: 'content.html?id=' + item.id,
        class: 'detail-link',
        text: '상세 페이지에서 보기 →'
    }));
    
    $('#lightbox').css('display', 'flex').hide().fadeIn(200);
}
"""

    # If data.js exists from previous versions, remove it to avoid confusion
    if os.path.exists(os.path.join(OUTPUT_DIR, "data.js")):
        os.remove(os.path.join(OUTPUT_DIR, "data.js"))

    with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f: f.write(html_index)
    with open(os.path.join(OUTPUT_DIR, "content.html"), "w", encoding="utf-8") as f: f.write(html_content)
    with open(os.path.join(OUTPUT_DIR, "about.html"), "w", encoding="utf-8") as f: f.write(html_about)
    with open(os.path.join(OUTPUT_DIR, "style.css"), "w", encoding="utf-8") as f: f.write(css_content)
    with open(os.path.join(OUTPUT_DIR, "main.js"), "w", encoding="utf-8") as f: f.write(js_content)

if __name__ == "__main__":
    export_project()
