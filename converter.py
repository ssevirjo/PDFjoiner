import os
import sys
import uuid
import shutil
import tempfile
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import pymupdf
from PIL import Image
import pythoncom
import win32com.client

# COM lock to serialize Word automation across threads safely
word_lock = threading.Lock()

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal and invalid chars."""
    keepchars = (' ', '.', '_', '-', '(', ')')
    clean = "".join(c for c in filename if c.isalnum() or c in keepchars).strip()
    return clean or "document.pdf"

def convert_docx_to_pdf(docx_path: str, output_pdf_path: str) -> bool:
    """
    Converts DOCX/DOC to PDF using Microsoft Word COM on Windows,
    or headless LibreOffice on Linux / Cloud (e.g. Render.com).
    Ensures 100% preservation of fonts, Latvian characters, layouts, and styles.
    """
    abs_docx = os.path.abspath(docx_path)
    abs_pdf = os.path.abspath(output_pdf_path)

    # 1. On Windows, use Microsoft Word COM automation
    if sys.platform == "win32":
        try:
            with word_lock:
                pythoncom.CoInitialize()
                word = None
                doc = None
                try:
                    word = win32com.client.DispatchEx("Word.Application")
                    word.Visible = False
                    word.DisplayAlerts = 0  # wdAlertsNone
                    
                    doc = word.Documents.Open(abs_docx, ReadOnly=True, ConfirmConversions=False)
                    doc.ExportAsFixedFormat(
                        OutputFileName=abs_pdf,
                        ExportFormat=17,  # wdExportFormatPDF
                        OpenAfterExport=False,
                        OptimizeFor=0,     # wdExportOptimizeForPrint
                        CreateBookmarks=1  # wdExportCreateHeadingBookmarks
                    )
                    return True
                finally:
                    if doc:
                        try:
                            doc.Close(SaveChanges=0)
                        except Exception:
                            pass
                    if word:
                        try:
                            word.Quit()
                        except Exception:
                            pass
                    pythoncom.CoUninitialize()
        except Exception as e:
            print(f"Word COM konvertācija neizdevās: {e}. Mēģina LibreOffice...")

    # 2. On Linux or if Word is unavailable, use LibreOffice
    import subprocess
    for cmd in ["soffice", "libreoffice"]:
        if shutil.which(cmd):
            try:
                out_dir = os.path.dirname(abs_pdf)
                subprocess.run(
                    [cmd, "--headless", "--convert-to", "pdf", "--outdir", out_dir, abs_docx],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=60,
                    check=True
                )
                expected_pdf = os.path.join(out_dir, Path(abs_docx).stem + ".pdf")
                if os.path.exists(expected_pdf):
                    if expected_pdf != abs_pdf:
                        shutil.move(expected_pdf, abs_pdf)
                    return True
            except Exception as ex:
                print(f"LibreOffice kļūda: {ex}")

    raise RuntimeError(f"Neizdevās konvertēt '{os.path.basename(docx_path)}' uz PDF. Lūdzu, pārliecinieties, ka datorā ir instalēts MS Word vai LibreOffice.")

def image_to_pdf_page(doc: pymupdf.Document, img_path: str, fit_mode: str = "a4_auto"):
    """
    Inserts an image file as a new PDF page.
    fit_mode:
      - 'a4_auto': scales image into standard A4 portrait or landscape page with clean margins
      - 'original': page size exactly matches the pixel dimensions of the image
    """
    with Image.open(img_path) as pil_img:
        img_w, img_h = pil_img.size
        # Correct orientation based on EXIF if present
        try:
            from PIL import ImageOps
            pil_img = ImageOps.exif_transpose(pil_img)
            img_w, img_h = pil_img.size
        except Exception:
            pass

    # A4 dimensions in points (72 points per inch)
    A4_W, A4_H = 595.28, 841.89

    if fit_mode == "original":
        page = doc.new_page(width=img_w, height=img_h)
        rect = pymupdf.Rect(0, 0, img_w, img_h)
        page.insert_image(rect, filename=img_path)
    else:
        # A4 auto: pick portrait or landscape
        if img_w > img_h:
            page_w, page_h = A4_H, A4_W  # Landscape
        else:
            page_w, page_h = A4_W, A4_H  # Portrait

        margin = 20.0
        avail_w = page_w - (2 * margin)
        avail_h = page_h - (2 * margin)

        # Scale preserving aspect ratio
        scale = min(avail_w / img_w, avail_h / img_h)
        dest_w = img_w * scale
        dest_h = img_h * scale

        # Center in page
        x0 = margin + (avail_w - dest_w) / 2.0
        y0 = margin + (avail_h - dest_h) / 2.0
        rect = pymupdf.Rect(x0, y0, x0 + dest_w, y0 + dest_h)

        page = doc.new_page(width=page_w, height=page_h)
        page.insert_image(rect, filename=img_path)

def parse_page_range(range_str: str, total_pages: int) -> List[int]:
    """
    Parses a page range string like '1-3, 5, 7-10' into 0-indexed page numbers.
    If 'all' or empty, returns list(range(total_pages)).
    """
    if not range_str or range_str.strip().lower() in ("all", "visi", "*"):
        return list(range(total_pages))
    
    pages = set()
    parts = range_str.replace(" ", "").split(",")
    for part in parts:
        if not part:
            continue
        if "-" in part:
            bounds = part.split("-")
            if len(bounds) == 2 and bounds[0].isdigit() and bounds[1].isdigit():
                start = max(1, int(bounds[0]))
                end = min(total_pages, int(bounds[1]))
                if start <= end:
                    for p in range(start, end + 1):
                        pages.add(p - 1)
        elif part.isdigit():
            p = int(part)
            if 1 <= p <= total_pages:
                pages.add(p - 1)
    
    res = sorted(list(pages))
    return res if res else list(range(total_pages))

def generate_thumbnail(source_path: str, out_thumb_path: str, max_size: int = 240) -> bool:
    """
    Generates a crisp thumbnail of the first page of a document.
    Works for PDF and images directly.
    """
    ext = Path(source_path).suffix.lower()
    try:
        if ext in (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"):
            with Image.open(source_path) as img:
                try:
                    from PIL import ImageOps
                    img = ImageOps.exif_transpose(img)
                except Exception:
                    pass
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                # Convert to RGB if RGBA/P for JPEG
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.save(out_thumb_path, "JPEG", quality=85)
            return True
        elif ext == ".pdf":
            doc = pymupdf.open(source_path)
            if len(doc) > 0:
                page = doc[0]
                # Render page at 100 DPI
                pix = page.get_pixmap(dpi=100)
                pix.save(out_thumb_path)
                doc.close()
                return True
            doc.close()
    except Exception as e:
        print(f"Thumbnail generation error for {source_path}: {e}")
    return False

def inspect_file(file_path: str, original_name: str, cache_dir: str) -> Dict[str, Any]:
    """
    Inspects an uploaded file: converts DOCX to PDF for preview if needed,
    determines page count, and prepares thumbnail.
    """
    ext = Path(original_name).suffix.lower()
    file_id = str(uuid.uuid4())
    size_bytes = os.path.getsize(file_path)
    
    file_info = {
        "id": file_id,
        "original_name": original_name,
        "extension": ext,
        "size_bytes": size_bytes,
        "size_formatted": format_size(size_bytes),
        "pages_count": 1,
        "has_thumbnail": False,
        "working_pdf_path": None,
        "is_image": ext in (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"),
        "is_docx": ext in (".docx", ".doc"),
        "is_pdf": ext == ".pdf",
        "error": None
    }
    
    thumb_path = os.path.join(cache_dir, f"thumb_{file_id}.jpg")
    
    try:
        if file_info["is_pdf"]:
            doc = pymupdf.open(file_path)
            file_info["pages_count"] = len(doc)
            doc.close()
            file_info["working_pdf_path"] = file_path
            if generate_thumbnail(file_path, thumb_path):
                file_info["has_thumbnail"] = True
                
        elif file_info["is_docx"]:
            # Convert DOCX to PDF now so we know exact page count and have thumbnails
            converted_pdf = os.path.join(cache_dir, f"conv_{file_id}.pdf")
            convert_docx_to_pdf(file_path, converted_pdf)
            file_info["working_pdf_path"] = converted_pdf
            
            doc = pymupdf.open(converted_pdf)
            file_info["pages_count"] = len(doc)
            doc.close()
            
            if generate_thumbnail(converted_pdf, thumb_path):
                file_info["has_thumbnail"] = True
                
        elif file_info["is_image"]:
            file_info["pages_count"] = 1
            if generate_thumbnail(file_path, thumb_path):
                file_info["has_thumbnail"] = True
        else:
            file_info["error"] = f"Neatbalstīts faila formāts: {ext}"
    except Exception as e:
        file_info["error"] = str(e)
        
    return file_info

def format_size(bytes_val: int) -> str:
    """Format bytes into readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}" if unit != 'B' else f"{bytes_val} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} TB"

def merge_documents_flow(
    files_spec: List[Dict[str, Any]], 
    output_path: str,
    image_fit: str = "a4_auto"
) -> Dict[str, Any]:
    """
    Merges documents in the exact order requested.
    Uses lossless PyMuPDF page stream copying to preserve 100% of fonts,
    Latvian Unicode text, vectors, and attachments.
    """
    merged_doc = pymupdf.open()
    total_pages_merged = 0
    items_processed = 0

    for item in files_spec:
        f_type = item.get("extension", "").lower()
        working_path = item.get("working_pdf_path")
        orig_path = item.get("file_path")
        page_range = item.get("page_range", "all")

        if f_type == ".pdf" or f_type in (".docx", ".doc"):
            target_pdf = working_path if working_path and os.path.exists(working_path) else orig_path
            src_doc = pymupdf.open(target_pdf)
            total_src_pages = len(src_doc)
            pages_to_include = parse_page_range(page_range, total_src_pages)
            
            for p_num in pages_to_include:
                # insert_pdf preserves original streams, fonts, diacritics verbatim!
                merged_doc.insert_pdf(src_doc, from_page=p_num, to_page=p_num)
                total_pages_merged += 1
                
            src_doc.close()
            items_processed += 1

        elif f_type in (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"):
            image_to_pdf_page(merged_doc, orig_path, fit_mode=image_fit)
            total_pages_merged += 1
            items_processed += 1

    # Save with garbage collection and deflation for optimal clean PDF
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    merged_doc.save(
        output_path,
        garbage=4,
        deflate=True,
        clean=True
    )
    merged_doc.close()

    final_size = os.path.getsize(output_path)
    return {
        "output_path": output_path,
        "output_filename": os.path.basename(output_path),
        "total_pages": total_pages_merged,
        "items_count": items_processed,
        "size_bytes": final_size,
        "size_formatted": format_size(final_size)
    }
