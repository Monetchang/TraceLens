import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/tracelens")
API_KEY = os.getenv("API_KEY", "")

# Similarity engine provider (env-based)
EMBEDDING_ENDPOINT = os.getenv("EMBEDDING_ENDPOINT", "")
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "")
EMBEDDING_INPUT_TYPE_QUERY = os.getenv("EMBEDDING_INPUT_TYPE_QUERY", "")
EMBEDDING_INPUT_TYPE_DOC = os.getenv("EMBEDDING_INPUT_TYPE_DOC", "")
LLM_ENDPOINT = os.getenv("LLM_ENDPOINT", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_SAMPLE_RATE = float(os.getenv("LLM_SAMPLE_RATE", "1.0"))

