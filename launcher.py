"""
launcher.py — Entry point for the Daycare Manager v2 desktop app.

Starts the FastAPI/Uvicorn server in a background thread, opens the
default browser, and shows a menu-bar / taskbar control window.
"""
import sys
import os
import time
import secrets
import threading
import webbrowser
import platform
import signal
import logging


# ── Base path (works both frozen by PyInstaller and in dev) ───────────────────
if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS  # PyInstaller temp extraction dir
    EXE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    EXE_DIR = BASE_DIR

# Add BASE_DIR to sys.path so `app` package is importable after freeze
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


# ── User data directory (persists DB, log, secret key) ───────────────────────
def _user_data_dir() -> str:
    if platform.system() == "Darwin":
        base = os.path.expanduser("~/Library/Application Support")
    elif platform.system() == "Windows":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.path.expanduser("~/.local/share")
    path = os.path.join(base, "DaycareManagerV2")
    os.makedirs(path, exist_ok=True)
    return path


APP_DATA_DIR = _user_data_dir()
DB_PATH = os.path.join(APP_DATA_DIR, "daycare.db")


def _load_or_create_secret() -> str:
    secret_file = os.path.join(APP_DATA_DIR, ".secret_key")
    if os.path.exists(secret_file):
        with open(secret_file) as f:
            return f.read().strip()
    key = secrets.token_urlsafe(32)
    with open(secret_file, "w") as f:
        f.write(key)
    return key


# ── Set env vars BEFORE importing any app code ────────────────────────────────
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{DB_PATH}")
os.environ.setdefault("SECRET_KEY", _load_or_create_secret())
os.environ.setdefault("ENVIRONMENT", "production")
os.environ.setdefault("RATE_LIMIT_MAX_REQUESTS", "200")
os.environ.setdefault("LOG_LEVEL", "WARNING")


# ── Logging ───────────────────────────────────────────────────────────────────
log_file = os.path.join(APP_DATA_DIR, "daycare_manager.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("launcher")


HOST = "127.0.0.1"
PORT = 8765
URL = f"http://{HOST}:{PORT}"


# ── Server ────────────────────────────────────────────────────────────────────
def start_server():
    import uvicorn
    from app.main import app as fastapi_app
    uvicorn.run(fastapi_app, host=HOST, port=PORT, log_level="warning")


def wait_and_open_browser():
    import urllib.request
    for _ in range(40):
        try:
            urllib.request.urlopen(f"{URL}/health", timeout=1)
            break
        except Exception:
            time.sleep(0.5)
    webbrowser.open(URL)
    logger.info(f"Browser opened at {URL}")


# ── macOS menu-bar (rumps) ────────────────────────────────────────────────────
def run_tray_mac():
    try:
        import rumps
        icon_path = os.path.join(BASE_DIR, "installer", "icon.icns")
        if not os.path.exists(icon_path):
            icon_path = None

        class DaycareApp(rumps.App):
            def __init__(self):
                super().__init__("Daycare Mgr v2", icon=icon_path, quit_button=None)
                self.menu = [
                    rumps.MenuItem("Open App", callback=self.open_browser),
                    None,
                    rumps.MenuItem("Quit", callback=self.quit_app),
                ]

            def open_browser(self, _):
                webbrowser.open(URL)

            def quit_app(self, _):
                rumps.quit_application()

        DaycareApp().run()
    except Exception as e:
        logger.warning(f"Menu bar unavailable ({e}); holding process open")
        signal.pause()


# ── Windows / generic control window (tkinter) ────────────────────────────────
def run_tray_windows():
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.title("Daycare Manager v2")
    root.resizable(False, False)
    root.geometry("300x130")

    icon_path = os.path.join(BASE_DIR, "installer", "icon.ico")
    if os.path.exists(icon_path):
        try:
            root.iconbitmap(icon_path)
        except Exception:
            pass

    tk.Label(root, text="✅  Daycare Manager v2 is running.", pady=12, font=("Segoe UI", 10)).pack()
    tk.Button(root, text="Open in Browser", width=22,
              command=lambda: webbrowser.open(URL)).pack(pady=4)

    def on_quit():
        if messagebox.askyesno("Quit", "Stop Daycare Manager and exit?"):
            root.destroy()
            os.kill(os.getpid(), signal.SIGTERM)

    tk.Button(root, text="Quit", width=22, command=on_quit).pack(pady=2)
    root.protocol("WM_DELETE_WINDOW", on_quit)
    root.mainloop()


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info(f"Daycare Manager v2 starting — data: {APP_DATA_DIR}")

    threading.Thread(target=start_server, daemon=True).start()
    threading.Thread(target=wait_and_open_browser, daemon=True).start()

    if platform.system() == "Darwin":
        run_tray_mac()
    else:
        run_tray_windows()
