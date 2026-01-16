from fastapi import FastAPI
from app.api import router
from app.database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="TraceLens")
app.include_router(router)

