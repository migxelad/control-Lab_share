"""Punto de entrada para Vercel (funciones Python): expone la app FastAPI."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.main import app  # noqa: E402,F401
