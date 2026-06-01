import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.routes import agents, config, runs, skills

DEBUG = os.environ.get("DEBUG", "").lower() in ("1", "true", "yes")

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)

if DEBUG:
    # Show every HTTP call — both genai and google-cloud-aiplatform SDKs
    for _verbose in (
        "httpx", "httpcore",
        "google.genai", "google_genai",
        "google.cloud", "google.api_core",
        "vertexai",
    ):
        logging.getLogger(_verbose).setLevel(logging.DEBUG)
    logging.getLogger("watchfiles.main").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
else:
    for _noisy in (
        "httpx", "httpcore",
        "google.genai", "google_genai",
        "google.cloud", "google.api_core",
        "vertexai",
        "watchfiles.main", "uvicorn.access",
    ):
        logging.getLogger(_noisy).setLevel(logging.WARNING)

log = logging.getLogger("digest")

_USE_VERTEX = os.environ.get("USE_VERTEX", "").lower() in ("1", "true", "yes")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if _USE_VERTEX:
        if not os.environ.get("GOOGLE_CLOUD_PROJECT"):
            raise RuntimeError("GOOGLE_CLOUD_PROJECT must be set when USE_VERTEX=true")
        log.info("Surface: Vertex AI Agent Platform (project=%s)", os.environ["GOOGLE_CLOUD_PROJECT"])
    else:
        if not os.environ.get("GEMINI_API_KEY"):
            raise RuntimeError("GEMINI_API_KEY must be set (or set USE_VERTEX=true for Vertex AI)")
        log.info("Surface: Gemini API")
    log.info("Daily Digest API started  debug=%s", DEBUG)
    yield
    log.info("Daily Digest API stopped")


app = FastAPI(title="Daily Digest API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/info")
def info():
    return {
        "surface": "vertex" if _USE_VERTEX else "gemini",
        "project": os.environ.get("GOOGLE_CLOUD_PROJECT") if _USE_VERTEX else None,
    }


@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)
    if "text/event-stream" not in response.headers.get("content-type", ""):
        log.info("%s %s  →  %s", request.method, request.url.path, response.status_code)
    return response


app.include_router(config.router)
app.include_router(agents.router)
app.include_router(runs.router)
app.include_router(skills.router)
