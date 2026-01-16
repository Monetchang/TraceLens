from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from tracelens.config import DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

