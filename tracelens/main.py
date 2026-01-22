from fastapi import FastAPI
from tracelens.api.routes import router
from tracelens.api.ingest_routes import router as ingest_router
from tracelens.api.rag_routes import router as rag_router
from tracelens.api.graph_routes import router as graph_router
from tracelens.api.evaluation_routes import router as eval_router
from tracelens.storage.database import engine, Base

app = FastAPI(title="TraceLens", version="0.1.0")

Base.metadata.create_all(bind=engine)

app.include_router(router)
app.include_router(ingest_router)
app.include_router(rag_router)
app.include_router(graph_router)
app.include_router(eval_router)


@app.get("/health")
def health():
    return {"status": "ok"}

