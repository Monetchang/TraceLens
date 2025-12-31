import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/tracelens")
OVERLAP_EPSILON = float(os.getenv("OVERLAP_EPSILON", "0.01"))

