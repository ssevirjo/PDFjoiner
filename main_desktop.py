import os
import sys
import time
import socket
import threading
import webbrowser
from pathlib import Path
import uvicorn

# Configure safe UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def find_available_port(preferred_port: int = 3335) -> int:
    """Check preferred port, or find an open ephemeral port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(('127.0.0.1', preferred_port)) != 0:
            return preferred_port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

def run_server(port: int):
    # Import app here so multiprocessing/fork in PyInstaller behaves cleanly
    from app import app
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")

def main():
    if getattr(sys, "frozen", False):
        os.chdir(Path(sys.executable).resolve().parent)
    else:
        os.chdir(Path(__file__).resolve().parent)

    port = find_available_port(3335)
    url = f"http://127.0.0.1:{port}"

    # Start FastAPI in background daemon thread
    server_thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    server_thread.start()

    # Allow server a brief moment to bind
    time.sleep(1.0)

    # Try native Windows desktop window using pywebview (Edge WebView2)
    has_gui = False
    try:
        import webview
        # Create native desktop window
        window = webview.create_window(
            title="PDF Dokumentu Apvienotājs",
            url=url,
            width=1180,
            height=850,
            min_size=(840, 600),
            confirm_close=False
        )
        has_gui = True
        webview.start()
    except Exception as e:
        print(f"Native GUI initialization skipped ({e}), opening in default browser...")
        has_gui = False

    if not has_gui:
        print(f"\n[+] Serveris darbojas: {url}")
        print("[+] Nospiediet Ctrl+C logā, lai apturētu programmu.\n")
        try:
            webbrowser.open(url)
        except Exception:
            pass
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nApturēts.")

if __name__ == "__main__":
    main()
