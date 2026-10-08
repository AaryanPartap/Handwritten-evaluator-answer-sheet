import os
import sys
import time
import subprocess
import signal
from pathlib import Path

def main():
    root = Path(__file__).resolve().parent
    venv_python = root / "venv" / "bin" / "python3"
    python_exe = str(venv_python) if venv_python.exists() else sys.executable

    print("=" * 65)
    print("      HANDWRITTEN ANSWER EVALUATOR (MVP) SYSTEM LAUNCHER")
    print("=" * 65)
    print(f"Using Python interpreter: {python_exe}\n")

    # 1. Launch FastAPI Backend
    print("[1/2] Launching FastAPI Backend on http://127.0.0.1:8000 ...")
    backend_proc = subprocess.Popen(
        [python_exe, str(root / "run_backend.py")],
        cwd=str(root)
    )

    # Allow backend 1.5 seconds to initialize
    time.sleep(1.5)

    # 2. Launch Flask Frontend
    print("[2/2] Launching Flask Frontend on http://127.0.0.1:5000 ...")
    frontend_proc = subprocess.Popen(
        [python_exe, str(root / "run_frontend.py")],
        cwd=str(root)
    )

    print("\n" + "=" * 65)
    print("ALL SERVICES RUNNING SUCCESSFULLY:")
    print(" -> Faculty Web Dashboard:    http://127.0.0.1:5000")
    print(" -> FastAPI Backend API:      http://127.0.0.1:8000")
    print(" -> Interactive Swagger Docs: http://127.0.0.1:8000/docs")
    print("=" * 65)
    print("Press Ctrl+C to terminate both servers.\n")

    def handle_sigint(sig, frame):
        print("\nShutting down servers...")
        try:
            backend_proc.terminate()
            frontend_proc.terminate()
        except Exception:
            pass
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sigint)

    try:
        backend_proc.wait()
        frontend_proc.wait()
    except KeyboardInterrupt:
        handle_sigint(None, None)

if __name__ == "__main__":
    main()
