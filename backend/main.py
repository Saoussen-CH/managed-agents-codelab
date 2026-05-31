import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()  # loads .env from repo root if present

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.routes import agents, config, runs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)

# Silence noisy third-party loggers
for _noisy in ("httpx", "httpcore", "google.genai", "watchfiles.main", "uvicorn.access"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

log = logging.getLogger("digest")


@asynccontextmanager
async def lifespan(app: FastAPI):
    use_vertex = os.environ.get("USE_VERTEX", "").lower() in ("1", "true", "yes")
    if use_vertex:
        if not os.environ.get("GOOGLE_CLOUD_PROJECT"):
            raise RuntimeError("GOOGLE_CLOUD_PROJECT must be set when USE_VERTEX=true")
        log.info("Surface: Vertex AI Agent Platform (project=%s)", os.environ["GOOGLE_CLOUD_PROJECT"])
    else:
        if not os.environ.get("GEMINI_API_KEY"):
            raise RuntimeError("GEMINI_API_KEY must be set (or set USE_VERTEX=true for Vertex AI)")
        log.info("Surface: Gemini API")
    log.info("Daily Digest API started")
    yield
    log.info("Daily Digest API stopped")


app = FastAPI(title="Daily Digest API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)
    # Skip SSE streams — they stay open and log on every chunk otherwise
    if "text/event-stream" not in response.headers.get("content-type", ""):
        log.info("%s %s  →  %s", request.method, request.url.path, response.status_code)
    return response


app.include_router(config.router)
app.include_router(agents.router)
app.include_router(runs.router)
