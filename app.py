import os
import sys
import shutil
import tempfile
import urllib.parse

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from typing import List, Optional
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from converter import (
    inspect_file,
    merge_documents_flow,
    sanitize_filename,
    format_size
)
import pymupdf

def get_bundle_dir() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent

def get_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

BUNDLE_DIR = get_bundle_dir()
APP_DIR = get_app_dir()

STATIC_DIR = BUNDLE_DIR / "static"
CACHE_DIR = APP_DIR / ".cache"
OUTPUT_DIR = APP_DIR / "output"

CACHE_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# In-memory storage for active session files
uploaded_files_registry = {}

app = FastAPI(title="PDF Document Joiner")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return HTMLResponse("<h1>Index file not found</h1>", status_code=404)
    return HTMLResponse(content=index_file.read_text(encoding="utf-8"))

@app.post("/api/upload")
async def upload_documents(files: List[UploadFile] = File(...)):
    results = []
    for file in files:
        original_name = file.filename or "unknown"
        ext = Path(original_name).suffix.lower()
        
        allowed_extensions = {".pdf", ".docx", ".doc", ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}
        if ext not in allowed_extensions:
            results.append({
                "original_name": original_name,
                "error": f"Neatbalstīts formāts: {ext}. Atbalstītie: PDF, DOCX, DOC, JPG, PNG, WEBP."
            })
            continue

        temp_name = f"upload_{len(uploaded_files_registry)}_{sanitize_filename(original_name)}"
        temp_file_path = CACHE_DIR / temp_name
        
        with open(temp_file_path, "wb") as f_out:
            shutil.copyfileobj(file.file, f_out)
            
        file_info = inspect_file(str(temp_file_path), original_name, str(CACHE_DIR))
        file_info["file_path"] = str(temp_file_path)
        
        uploaded_files_registry[file_info["id"]] = file_info
        
        results.append({
            "id": file_info["id"],
            "original_name": file_info["original_name"],
            "extension": file_info["extension"],
            "size_formatted": file_info["size_formatted"],
            "size_bytes": file_info["size_bytes"],
            "pages_count": file_info["pages_count"],
            "has_thumbnail": file_info["has_thumbnail"],
            "is_image": file_info["is_image"],
            "is_docx": file_info["is_docx"],
            "is_pdf": file_info["is_pdf"],
            "error": file_info["error"]
        })
        
    return JSONResponse(content={"files": results})

@app.get("/api/thumbnail/{file_id}")
async def get_thumbnail(file_id: str):
    thumb_path = CACHE_DIR / f"thumb_{file_id}.jpg"
    if thumb_path.exists():
        return FileResponse(path=str(thumb_path), media_type="image/jpeg")
    
    # Return placeholder or 404
    return HTTPException(status_code=404, detail="Thumbnail not found")

@app.get("/api/preview/{file_id}/{page_num}")
async def get_page_preview(file_id: str, page_num: int = 0):
    if file_id not in uploaded_files_registry:
        raise HTTPException(status_code=404, detail="File not found")
        
    info = uploaded_files_registry[file_id]
    target_pdf = info.get("working_pdf_path")
    is_image = info.get("is_image")
    file_path = info.get("file_path")
    
    preview_cache = CACHE_DIR / f"prev_{file_id}_{page_num}.jpg"
    if preview_cache.exists():
        return FileResponse(path=str(preview_cache), media_type="image/jpeg")
        
    if is_image and file_path and os.path.exists(file_path):
        return FileResponse(path=file_path)
        
    if target_pdf and os.path.exists(target_pdf):
        try:
            doc = pymupdf.open(target_pdf)
            if 0 <= page_num < len(doc):
                page = doc[page_num]
                # High quality 150 DPI preview
                pix = page.get_pixmap(dpi=150)
                pix.save(str(preview_cache))
                doc.close()
                return FileResponse(path=str(preview_cache), media_type="image/jpeg")
            doc.close()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Preview generation failed: {e}")
            
    raise HTTPException(status_code=404, detail="Preview not available")

class MergeItem(BaseModel):
    id: str
    page_range: Optional[str] = "all"

class MergeRequest(BaseModel):
    items: List[MergeItem]
    output_filename: Optional[str] = "Apvienotais_dokuments.pdf"
    output_folder: Optional[str] = None
    image_fit: Optional[str] = "a4_auto"
    open_after_create: Optional[bool] = False
    open_explorer: Optional[bool] = False

@app.post("/api/choose-folder")
async def choose_folder():
    """Opens native Windows folder selection dialog."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        selected_dir = filedialog.askdirectory(title="Izvēlieties mapi PDF saglabāšanai")
        root.destroy()
        if selected_dir:
            norm_dir = os.path.normpath(selected_dir)
            return JSONResponse(content={"folder": norm_dir})
        return JSONResponse(content={"folder": None})
    except Exception as e:
        return JSONResponse(content={"folder": None, "error": str(e)})

@app.post("/api/merge")
async def merge_files(request: MergeRequest):
    if not request.items:
        raise HTTPException(status_code=400, detail="Nav atlasīts neviens dokuments apvienošanai.")
        
    files_spec = []
    for item in request.items:
        if item.id in uploaded_files_registry:
            file_meta = uploaded_files_registry[item.id].copy()
            file_meta["page_range"] = item.page_range
            files_spec.append(file_meta)
        else:
            raise HTTPException(status_code=400, detail=f"Fails ar ID {item.id} netika atrasts sesijā.")
            
    raw_name = request.output_filename.strip() if request.output_filename else "Apvienotais_dokuments.pdf"
    if not raw_name.lower().endswith(".pdf"):
        raw_name += ".pdf"
    clean_name = sanitize_filename(raw_name)
    if not clean_name.lower().endswith(".pdf"):
        clean_name += ".pdf"

    # Default internal output path
    default_output_file_path = OUTPUT_DIR / clean_name
    
    # Custom user-selected destination folder
    dest_file_path = default_output_file_path
    if request.output_folder and os.path.isdir(request.output_folder):
        dest_file_path = Path(request.output_folder) / clean_name
    
    try:
        stats = merge_documents_flow(
            files_spec=files_spec,
            output_path=str(dest_file_path),
            image_fit=request.image_fit or "a4_auto"
        )

        # If saved to custom directory, also make a copy in OUTPUT_DIR for browser download link
        if dest_file_path != default_output_file_path:
            try:
                shutil.copyfile(str(dest_file_path), str(default_output_file_path))
            except Exception:
                pass
        
        # Optionally open directly in Windows PDF viewer
        if request.open_after_create and hasattr(os, "startfile"):
            try:
                os.startfile(str(dest_file_path))
            except Exception as e:
                print(f"Neizdevās atvērt failu automātiski: {e}")
                
        # Optionally open in explorer
        if request.open_explorer and sys.platform == "win32":
            try:
                import subprocess
                subprocess.Popen(f'explorer /select,"{dest_file_path}"')
            except Exception as e:
                print(f"Neizdevās atvērt mapi: {e}")
                
        download_url = f"/api/download/{urllib.parse.quote(clean_name)}"
        
        return JSONResponse(content={
            "success": True,
            "filename": clean_name,
            "saved_path": str(dest_file_path),
            "saved_folder": str(dest_file_path.parent),
            "download_url": download_url,
            "stats": stats
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Kļūda dokumentu apvienošanā: {str(e)}")

@app.get("/api/download/{filename}")
async def download_file(filename: str):
    clean_name = sanitize_filename(filename)
    target_path = OUTPUT_DIR / clean_name
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="Fails netika atrasts.")
        
    # Quote filename for UTF-8 RFC 5987 content-disposition
    encoded_name = urllib.parse.quote(clean_name)
    return FileResponse(
        path=str(target_path),
        media_type="application/pdf",
        filename=clean_name,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}"
        }
    )

@app.post("/api/open-output-folder")
async def open_output_folder():
    try:
        if hasattr(os, "startfile"):
            os.startfile(str(OUTPUT_DIR))
        return JSONResponse(content={"success": True})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)})

@app.post("/api/clear")
async def clear_uploaded_files():
    uploaded_files_registry.clear()
    for item in CACHE_DIR.glob("*"):
        try:
            if item.is_file():
                item.unlink(missing_ok=True)
            elif item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
        except Exception:
            pass
    return JSONResponse(content={"success": True, "message": "Saraksts un pagaidu faili notīrīti."})

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=3335, reload=False)
