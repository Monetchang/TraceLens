import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/tracelens")
API_KEY = os.getenv("API_KEY", "")

# Similarity engine provider (env-based)
EMBEDDING_ENDPOINT = os.getenv("EMBEDDING_ENDPOINT", "")
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")
LLM_ENDPOINT = os.getenv("LLM_ENDPOINT", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")

