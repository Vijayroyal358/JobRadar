"""One-click launcher for JobRadar.

1. Creates a private Python environment (.venv) and installs dependencies on first run or when requirements change.
2. Starts the local server on http://127.0.0.1:8765.
3. Opens the dashboard in your browser.
"""
import hashlib
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
REQ = ROOT / "requirements.txt"
HOST = os.environ.get("JOBRADAR_HOST", "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1")
PORT = int(os.environ.get("PORT", os.environ.get("JOBRADAR_PORT", "8765")))
URL = f"http://{HOST}:{PORT}"


def venv_python():
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def in_venv():
    return Path(sys.prefix).resolve() == VENV.resolve()


def venv_works(py):
    """A .venv copied from another computer points at that computer's Python and no longer runs."""
    if not py.exists():
        return False
    try:
        return subprocess.run([str(py), "-c", "import sys"], capture_output=True, timeout=30).returncode == 0
    except Exception:
        return False


def make_shortcut():
    """On Windows, put a JobRadar shortcut on the desktop (once per computer)."""
    if os.name != "nt":
        return
    ps = (
        "$d=[Environment]::GetFolderPath('Desktop'); $l=Join-Path $d 'JobRadar.lnk';"
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($l);"
        f"$s.TargetPath='{ROOT / 'start.bat'}'; $s.WorkingDirectory='{ROOT}';"
        "$s.Description='JobRadar - jobs matched to your resume'; $s.Save()"
    )
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, timeout=30)
        print("Added a JobRadar shortcut to your desktop.")
    except Exception:
        pass


def ensure_env():
    if sys.version_info < (3, 10):
        sys.exit(f"JobRadar needs Python 3.10 or newer. This is Python {sys.version.split()[0]}. "
                 "Install a newer one from https://www.python.org/downloads/")
    py = venv_python()
    if not venv_works(py):
        if VENV.exists():
            print("Rebuilding the Python environment for this computer...")
            shutil.rmtree(VENV, ignore_errors=True)
        else:
            print("Setting up JobRadar for the first time (about a minute)...")
        subprocess.check_call([sys.executable, "-m", "venv", str(VENV)])
        make_shortcut()
    want = hashlib.sha1(REQ.read_bytes()).hexdigest()
    marker = VENV / ".requirements.sha1"
    if not marker.exists() or marker.read_text().strip() != want:
        print("Installing dependencies...")
        subprocess.check_call([str(py), "-m", "pip", "install", "--disable-pip-version-check", "-q", "--upgrade", "pip"])
        subprocess.check_call([str(py), "-m", "pip", "install", "--disable-pip-version-check", "-q", "-r", str(REQ)])
        marker.write_text(want)
    return py


def server_alive():
    try:
        with urllib.request.urlopen(URL + "/api/meta", timeout=1.5) as r:
            return r.status == 200
    except Exception:
        return False


def open_when_ready():
    for _ in range(60):
        if server_alive():
            webbrowser.open(URL)
            return
        time.sleep(0.5)


def main():
    if not in_venv():
        py = ensure_env()
        sys.exit(subprocess.call([str(py), str(ROOT / "run.py")] + sys.argv[1:]))

    if server_alive():
        print(f"JobRadar is already running. Opening {URL}")
        webbrowser.open(URL)
        return

    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    import uvicorn

    if "--no-browser" not in sys.argv:
        threading.Thread(target=open_when_ready, daemon=True).start()
    print(f"\n  JobRadar is running at {URL}\n  Keep this window open while you use it. Close it to stop.\n")
    uvicorn.run("app.main:app", host=HOST, port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
