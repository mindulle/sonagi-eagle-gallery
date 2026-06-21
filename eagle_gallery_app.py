import json
import os
import sqlite3

import sentry_sdk
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator

sentry_dsn = os.environ.get("SENTRY_DSN")
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )

app = FastAPI()

Instrumentator().instrument(app).expose(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "eagle_gallery.db"


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/api/items")
def get_items(limit: int = 50, offset: int = 0, search: str = ""):
    conn = get_db()
    c = conn.cursor()

    query = "SELECT * FROM items"
    params = []

    if search:
        query += " WHERE name LIKE ? OR tags LIKE ?"
        search_term = "%" + search + "%"
        params.extend([search_term, search_term])

    query += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    c.execute(query, params)
    rows = c.fetchall()

    items = []
    for r in rows:
        items.append(
            {
                "id": r["id"],
                "name": r["name"],
                "ext": r["ext"],
                "tags": json.loads(r["tags"]) if r["tags"] else [],
                "has_thumbnail": bool(r["thumbnail_path"]),
            }
        )

    conn.close()
    return items


@app.get("/api/image/{item_id}/{type}")
def get_image(item_id: str, type: str):
    if type not in ["thumbnail", "original"]:
        raise HTTPException(status_code=400, detail="Invalid image type")

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT thumbnail_path, original_path FROM items WHERE id = ?", (item_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return HTMLResponse(status_code=404, content="Not found")

    path = row["thumbnail_path"] if type == "thumbnail" else row["original_path"]
    if path and os.path.exists(path):
        return FileResponse(path)
    return HTMLResponse(status_code=404, content="File not found")


@app.get("/")
def index():
    return FileResponse("static/index.html")


app.mount("/static", StaticFiles(directory="static"), name="static")
