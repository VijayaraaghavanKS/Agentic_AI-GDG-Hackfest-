# -*- coding: utf-8 -*-
"""
start.py - Unified launcher for the Regime-Aware Trading Command Center.

Usage:
    python start.py              # Production mode: build frontend, start FastAPI
    python start.py --dev        # Dev mode: start FastAPI + Vite dev server
    python start.py --build-only # Just build the frontend
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT / "frontend"
SERVER_MODULE = "server.app:app"


def run(cmd: list[str], cwd: str | Path = ROOT, **kwargs):
    """Run a command and stream output."""
    print(f"  → {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=str(cwd), **kwargs)


def install_frontend_deps():
    """Install frontend npm dependencies if needed."""
    node_modules = FRONTEND_DIR / "node_modules"
    if not node_modules.is_dir():
        print("\n[*] Installing frontend dependencies...")
        result = run(["npm", "install"], cwd=FRONTEND_DIR)
        if result.returncode != 0:
            print("[FAIL] npm install failed")
            sys.exit(1)
    else:
        print("[OK] Frontend dependencies already installed")


def build_frontend():
    """Build the React frontend for production."""
    print("\n[*] Building frontend...")
    result = run(["npm", "run", "build"], cwd=FRONTEND_DIR)
    if result.returncode != 0:
        print("[FAIL] Frontend build failed")
        sys.exit(1)
    dist = FRONTEND_DIR / "dist"
    if dist.is_dir():
        print(f"[OK] Frontend built -> {dist}")
    else:
        print("[FAIL] Build output not found")
        sys.exit(1)


def start_production(host: str, port: int):
    """Build frontend then start FastAPI serving everything."""
    install_frontend_deps()
    build_frontend()

    print(f"\n[*] Starting production server on http://{host}:{port}")
    print("    Press Ctrl+C to stop\n")
    run(
        [sys.executable, "-m", "uvicorn", SERVER_MODULE,
         "--host", host, "--port", str(port)],
    )


def start_dev(host: str, port: int):
    """Start FastAPI backend + Vite dev server concurrently."""
    install_frontend_deps()

    print(f"\n[*] Starting dev mode...")
    print(f"    Backend  -> http://{host}:{port}")
    print(f"    Frontend -> http://localhost:5173 (Vite dev server)")
    print("    Press Ctrl+C to stop both\n")

    procs = []
    try:
        # Start FastAPI backend
        backend = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", SERVER_MODULE,
             "--host", host, "--port", str(port), "--reload"],
            cwd=str(ROOT),
        )
        procs.append(backend)

        # Start Vite dev server
        frontend = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=str(FRONTEND_DIR),
        )
        procs.append(frontend)

        # Poll until any process exits
        while True:
            for p in procs:
                ret = p.poll()
                if ret is not None:
                    print(f"\n[WARN] Process (pid={p.pid}) exited with code {ret}")
                    raise SystemExit(ret)
            time.sleep(0.5)

    except (KeyboardInterrupt, SystemExit):
        print("\n\n[*] Shutting down...")
    finally:
        for p in procs:
            try:
                p.terminate()
                p.wait(timeout=5)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass
        print("[OK] All processes stopped")


def main():
    parser = argparse.ArgumentParser(
        description="Regime-Aware Trading Command Center Launcher"
    )
    parser.add_argument(
        "--dev", action="store_true",
        help="Run in development mode (hot-reload for both frontend and backend)"
    )
    parser.add_argument(
        "--build-only", action="store_true",
        help="Only build the frontend, don't start any server"
    )
    parser.add_argument("--host", default="0.0.0.0", help="Server host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Server port (default: 8000)")

    args = parser.parse_args()

    if args.build_only:
        install_frontend_deps()
        build_frontend()
    elif args.dev:
        start_dev(args.host, args.port)
    else:
        start_production(args.host, args.port)


if __name__ == "__main__":
    main()
