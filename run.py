import os
import sys
import time
import webbrowser
import threading
import uvicorn

# Configure safe UTF-8 output on Windows consoles (e.g. CP1257 Baltic, CP1251, CP866)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def open_browser():
    time.sleep(1.2)
    url = "http://127.0.0.1:3335"
    print(f"\n[+] Opening browser: {url}")
    print(f"[+] Atver pārlūku: {url}")
    print(f"[+] Открытие браузера: {url}\n")
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"Warning: could not open browser automatically: {e}")

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    threading.Thread(target=open_browser, daemon=True).start()
    print("=======================================================")
    print("      PDF Document Joiner - Server running on :3335")
    print("=======================================================")
    print("Press Ctrl+C to stop the server.")
    uvicorn.run("app:app", host="127.0.0.1", port=3335, reload=False, log_level="info")
