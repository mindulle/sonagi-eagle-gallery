import json
import os
import shutil
import sqlite3


def export_project():
    OUTPUT_DIR = "submission_ready"
    IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")

    # Create directories
    os.makedirs(IMAGES_DIR, exist_ok=True)

    # 1. Connect to DB and fetch top 60 items for the assignment
    conn = sqlite3.connect("eagle_gallery.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM items ORDER BY id DESC LIMIT 60")
    rows = c.fetchall()

    items_data = []

    print("Exporting data and copying images...")
    for r in rows:
        item_id = r["id"]
        ext = r["ext"]
        thumb_src = r["thumbnail_path"]
        orig_src = r["original_path"]

        # Determine local paths for export
        local_thumb = f"{item_id}_thumb.png"
        local_orig = f"{item_id}.{ext}" if ext else f"{item_id}_orig"

        # Copy files if they exist
        has_thumbnail = False
        if thumb_src and os.path.exists(thumb_src):
            shutil.copy2(thumb_src, os.path.join(IMAGES_DIR, local_thumb))
            has_thumbnail = True

        if orig_src and os.path.exists(orig_src):
            shutil.copy2(orig_src, os.path.join(IMAGES_DIR, local_orig))

        items_data.append(
            {
                "id": item_id,
                "name": r["name"],
                "ext": ext,
                "tags": json.loads(r["tags"]) if r["tags"] else [],
                "annotation": r["annotation"],
                "url": r["url"],
                "has_thumbnail": has_thumbnail,
                "thumb_url": f"images/{local_thumb}",
                "orig_url": f"images/{local_orig}",
            }
        )

    # Get top tags for these items
    c.execute("""
        SELECT value as tag, count(*) as count
        FROM items, json_each(items.tags)
        WHERE items.id IN (SELECT id FROM items ORDER BY id DESC LIMIT 60)
        GROUP BY value
        ORDER BY count DESC LIMIT 10
    """)
    tags_data = [{"tag": row["tag"], "count": row["count"]} for row in c.fetchall()]

    c.execute("""
        SELECT ext, count(*) as count
        FROM items
        WHERE ext != '' AND ext IS NOT NULL
        AND id IN (SELECT id FROM items ORDER BY id DESC LIMIT 60)
        GROUP BY ext
        ORDER BY count DESC LIMIT 10
    """)
    exts_data = [{"ext": row["ext"], "count": row["count"]} for row in c.fetchall()]

    conn.close()

    # Dump JSON
    export_data = {"items": items_data, "tags": tags_data, "exts": exts_data}
    with open(os.path.join(OUTPUT_DIR, "data.json"), "w", encoding="utf-8") as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)

    print("Generating HTML/CSS/JS files...")
    # Generate HTML files (Semantic Markup)
    # 1. index.html
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
                <!-- jQuery will inject cards here -->
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

    # 2. content.html
    html_content = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Eagle Gallery - Content</title>
    <link rel="stylesheet" href="style.css">
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
    <main>
        <article class="page-content">
            <h2>Detailed View</h2>
            <p>This page is a placeholder for detailed content visualization required by the assignment specs.</p>
            <p>In a real application, this would render a specific item's full detail view directly via server-side rendering or query parameters.</p>
        </article>
    </main>
    <footer>
        <p>&copy; 2026 Web Programming Assignment - Sonagi</p>
    </footer>
</body>
</html>"""

    # 3. about.html
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
    <main>
        <article class="page-content">
            <h2>About the Project</h2>
            <p>This is a static web application built for the 3rd year 1st semester Web Programming assignment.</p>
            <p><strong>Tech Stack:</strong> HTML5 (Semantic), CSS3 (Flexbox/Grid/Masonry), jQuery 4.0.0-beta</p>
            <p>It exports data from a live FastAPI application into a static JSON format to ensure zero backend dependencies for grading.</p>
        </article>
    </main>
    <footer>
        <p>&copy; 2026 Web Programming Assignment - Sonagi</p>
    </footer>
</body>
</html>"""

    # 4. style.css (Semantic & Grid/Flexbox)
    css_content = """* { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, sans-serif; }
body { background: #faf9f7; color: #333; display: flex; flex-direction: column; min-height: 100vh; }

/* Header & Nav */
header { background: #1991B9; color: white; padding: 20px; display: flex; justify-content: space-between; align-items: center; }
nav ul { list-style: none; display: flex; gap: 20px; }
nav a { color: white; text-decoration: none; opacity: 0.8; font-weight: bold; }
nav a:hover, nav a.active { opacity: 1; text-decoration: underline; }

/* Layout */
.layout { display: flex; flex: 1; }
.sidebar { width: 250px; background: #fff; border-right: 1px solid #eee; padding: 20px; }
.sidebar-section { margin-bottom: 20px; }
.filter-list { list-style: none; }
.filter-list li { padding: 8px; cursor: pointer; display: flex; justify-content: space-between; border-radius: 4px; }
.filter-list li:hover { background: #f0f8fb; color: #1991B9; }
.count { color: #aaa; background: #eee; padding: 2px 6px; border-radius: 12px; font-size: 0.8em; }

/* Main Content */
.main-content { flex: 1; padding: 20px; }
.search-bar { margin-bottom: 20px; }
.search-bar input { width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 4px; }

/* Masonry Gallery */
.gallery { column-count: 4; column-gap: 20px; }
.card { background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; break-inside: avoid; display: inline-block; width: 100%; cursor: pointer; }
.card img { width: 100%; display: block; }
.card-info { padding: 15px; }
.card-title { font-size: 1em; margin-bottom: 10px; }
.tag { display: inline-block; background: #eee; padding: 4px 8px; border-radius: 4px; font-size: 0.8em; margin: 2px; }

/* Footer */
footer { background: #333; color: white; text-align: center; padding: 20px; margin-top: auto; }

/* Modal */
.lightbox { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 1000; }
.lightbox-overlay { position: absolute; width: 100%; height: 100%; background: rgba(0,0,0,0.8); }
.lightbox-content { position: relative; width: 80%; height: 80%; background: white; margin: 5% auto; display: flex; border-radius: 8px; overflow: hidden; }
.lightbox-image-container { flex: 2; background: #f4f4f4; display: flex; align-items: center; justify-content: center; padding: 20px; }
.lightbox-image-container img { max-width: 100%; max-height: 100%; object-fit: contain; }
.lightbox-info { flex: 1; padding: 30px; overflow-y: auto; }
.close-btn { position: absolute; top: 10px; right: 20px; background: none; border: none; font-size: 2em; cursor: pointer; }

/* Pages */
.page-content { padding: 40px; max-width: 800px; margin: 0 auto; flex: 1; }
.page-content h2 { margin-bottom: 20px; }
.page-content p { margin-bottom: 15px; line-height: 1.6; }

/* Responsive */
@media (max-width: 1024px) { .gallery { column-count: 3; } }
@media (max-width: 768px) { .layout { flex-direction: column; } .gallery { column-count: 2; } .lightbox-content { flex-direction: column; } }
"""

    # 5. main.js (jQuery 4.0.0)
    js_content = """let globalData = null;

$(function() {
    // Initialize
    $.getJSON('data.json', function(data) {
        globalData = data;
        renderSidebar(data);
        renderGallery(data.items);
    });

    // Search functionality
    $('#search').on('keyup', function() {
        const term = $(this).val().toLowerCase();
        filterGallery(term);
    });

    // Modal close events
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
        const $li = $('<li>').html(`<span># ${t.tag}</span> <span class="count">${t.count}</span>`);
        $li.on('click', () => { $('#search').val(t.tag); filterGallery(t.tag); });
        $tagList.append($li);
    });

    $.each(data.exts, function(i, e) {
        const $li = $('<li>').html(`<span>. ${e.ext.toUpperCase()}</span> <span class="count">${e.count}</span>`);
        $li.on('click', () => { $('#search').val(e.ext); filterGallery(e.ext); });
        $extList.append($li);
    });
}

function renderGallery(items) {
    const $gallery = $('#gallery');
    $gallery.empty();

    if (items.length === 0) {
        $gallery.html('<p>No results found.</p>');
        return;
    }

    $.each(items, function(i, item) {
        const imgSrc = item.has_thumbnail ? item.thumb_url : item.orig_url;

        const $card = $('<div>', { class: 'card' }).on('click', () => openModal(item));
        const $img = $('<img>', { src: imgSrc, loading: 'lazy' });

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
    const filtered = globalData.items.filter(item => {
        const matchName = (item.name || '').toLowerCase().includes(term);
        const matchTags = item.tags.some(t => t.toLowerCase().includes(term));
        const matchExt = (item.ext || '').toLowerCase().includes(term);
        return matchName || matchTags || matchExt;
    });
    renderGallery(filtered);
}

function openModal(item) {
    $('#modal-img-wrapper').html($('<img>', { src: item.orig_url }));

    const $info = $('#modal-info').empty();
    $info.append($('<h2>', { text: item.name || 'Untitled' }));
    $info.append($('<p>').html(`<strong>Ext:</strong> ${item.ext || 'Unknown'}`));

    if (item.url) {
        $info.append($('<p>').html(`<strong>Source:</strong> <a href="${item.url}" target="_blank">Link</a>`));
    }

    if (item.annotation) {
        $info.append($('<p>').html(`<strong>Note:</strong> ${item.annotation}`));
    }

    $('#lightbox').css('display', 'flex').hide().fadeIn(200);
}
"""

    with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(html_index)
    with open(os.path.join(OUTPUT_DIR, "content.html"), "w", encoding="utf-8") as f:
        f.write(html_content)
    with open(os.path.join(OUTPUT_DIR, "about.html"), "w", encoding="utf-8") as f:
        f.write(html_about)
    with open(os.path.join(OUTPUT_DIR, "style.css"), "w", encoding="utf-8") as f:
        f.write(css_content)
    with open(os.path.join(OUTPUT_DIR, "main.js"), "w", encoding="utf-8") as f:
        f.write(js_content)

    print(f"Export complete. Check the '{OUTPUT_DIR}' directory.")


if __name__ == "__main__":
    export_project()
