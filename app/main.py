"""FastAPI entrypoint: mounts the /api/v1 routers, then serves the built
frontend (frontend/dist) with an SPA fallback for every non-API route.

Single web service, single port ($PORT), per Section 2 of the spec.
"""
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.routers import auth as auth_router
from app.routers import settings as settings_router

app = FastAPI(title="HeadcountHQ API", docs_url="/api/docs", openapi_url="/api/openapi.json")

session_secret = os.environ.get("SESSION_SECRET")
if not session_secret:
    raise RuntimeError("SESSION_SECRET is required (set it via Replit's secrets tool).")
app.add_middleware(SessionMiddleware, secret_key=session_secret, same_site="lax")

# Routers are included directly on the main app (not mounted as a separate
# sub-application) so that /api/docs's OpenAPI schema actually documents
# every /api/v1 route.
app.include_router(auth_router.router, prefix="/api/v1")
app.include_router(settings_router.router, prefix="/api/v1")


@app.exception_handler(404)
async def spa_or_404(request, exc):
    # /api/* 404s stay JSON; everything else falls back to the SPA shell so
    # client-side routing (React Router) can handle the path.
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    return _serve_index()


FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


def _serve_index() -> FileResponse | JSONResponse:
    index_path = FRONTEND_DIST / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return JSONResponse(
        status_code=503,
        content={
            "detail": (
                "Frontend build not found. Run `npm run build` inside frontend/ "
                "(the .replit run command does this automatically)."
            )
        },
    )


if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")


@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")
    return _serve_index()
