import logging
import uuid
from contextvars import ContextVar

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from tracelens.api.routes import router
from tracelens.api.ingest_routes import router as ingest_router
from tracelens.api.rag_routes import router as rag_router
from tracelens.api.graph_routes import router as graph_router
from tracelens.api.evaluation_routes import router as eval_router

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


class RequestIdFilter(logging.Filter):
    def filter(self, record):
        try:
            record.request_id = request_id_ctx.get()
        except LookupError:
            record.request_id = ""
        return True

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","request_id":"%(request_id)s","msg":"%(message)s"}',
    datefmt="%Y-%m-%dT%H:%M:%S",
)
for h in logging.root.handlers:
    h.addFilter(RequestIdFilter())


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request_id_ctx.set(rid)
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response


app = FastAPI(title="TraceLens", version="0.1.0")
app.add_middleware(RequestIdMiddleware)


@app.on_event("startup")
def startup():
    from tracelens.config import DATABASE_URL
    if "postgres:postgres@" in DATABASE_URL or "@localhost" in DATABASE_URL:
        import logging
        logging.getLogger(__name__).warning(
            "Using default DATABASE_URL with weak credentials. "
            "Set DATABASE_URL explicitly for production."
        )
    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")

app.include_router(router)
app.include_router(ingest_router)
app.include_router(rag_router)
app.include_router(graph_router)
app.include_router(eval_router)


@app.get("/health")
def health():
    return {"status": "ok"}

