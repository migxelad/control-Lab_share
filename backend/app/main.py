"""API FastAPI + servidor estático del frontend compilado."""
from __future__ import annotations
import traceback
from pathlib import Path
from fastapi import APIRouter, FastAPI, Request
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .symbolic import AnalysisError
from .analysis import analyze
from . import report

app = FastAPI(title="Control Lab API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(AnalysisError)
async def _ae(_: Request, exc: AnalysisError):
    return JSONResponse(status_code=422, content={"ok": False, "detail": str(exc)})


@app.exception_handler(StarletteHTTPException)
async def _http(request: Request, exc: StarletteHTTPException):
    body = {"detail": exc.detail}
    if exc.status_code == 404:
        body["path"] = request.url.path  # diagnóstico: ruta que ha recibido la app
    return JSONResponse(status_code=exc.status_code, content=body)


router = APIRouter()


@router.get("/health")
def health():
    return {"ok": True}


@router.post("/analyze")
def api_analyze(req: dict):
    try:
        return analyze(req)
    except AnalysisError:
        raise
    except Exception as ex:  # noqa: BLE001
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"ok": False, "detail": f"Error interno: {type(ex).__name__}: {ex}"})


@router.post("/report")
def api_report(req: dict, format: str = "pdf"):
    r = analyze(req)
    if format == "pdf":
        return Response(report.pdf(r), media_type="application/pdf",
                        headers={"Content-Disposition": "attachment; filename=informe.pdf"})
    if format in ("md", "tex"):
        return Response(report.zip_report(r, format), media_type="application/zip",
                        headers={"Content-Disposition": f"attachment; filename=informe_{format}.zip"})
    return JSONResponse(status_code=400, content={"detail": "Formato no soportado"})


app.include_router(router, prefix="/api")
# Algunos entornos (p. ej. Vercel) pueden entregar la ruta sin el prefijo /api:
app.include_router(router, include_in_schema=False)


DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="static")
