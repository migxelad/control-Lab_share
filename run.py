#!/usr/bin/env python3
"""Arranque rápido: prepara venv + dependencias, compila el frontend (si hace falta) y lanza el servidor.
Uso:  python run.py [--port 8000] [--dev] [--rebuild]"""
import argparse, os, subprocess, sys, venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
PY = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def sh(cmd, **kw):
    print("→", " ".join(map(str, cmd)))
    subprocess.run(cmd, check=True, **kw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--dev", action="store_true", help="Vite dev server (5173) + API con recarga")
    ap.add_argument("--rebuild", action="store_true", help="recompilar el frontend")
    a = ap.parse_args()

    if not PY.exists():
        venv.EnvBuilder(with_pip=True).create(VENV)
    stamp = VENV / ".deps-ok"
    req = ROOT / "backend" / "requirements.txt"
    if not stamp.exists() or stamp.stat().st_mtime < req.stat().st_mtime:
        sh([PY, "-m", "pip", "install", "-q", "-r", req])
        stamp.touch()

    fe = ROOT / "frontend"
    npm = "npm.cmd" if os.name == "nt" else "npm"
    if not (fe / "node_modules").exists():
        sh([npm, "install", "--no-audit", "--no-fund"], cwd=fe)
    api = [PY, "-m", "uvicorn", "app.main:app", "--port", str(a.port), "--host", "0.0.0.0"]
    if a.dev:
        p = subprocess.Popen([*api, "--reload"], cwd=ROOT / "backend")
        try:
            sh([npm, "run", "dev", "--", "--host"], cwd=fe)
        finally:
            p.terminate()
        return
    if a.rebuild or not (fe / "dist").exists():
        sh([npm, "run", "build"], cwd=fe)
    print(f"\n  Control Lab en http://localhost:{a.port}\n")
    sh(api, cwd=ROOT / "backend")


if __name__ == "__main__":
    sys.exit(main())
