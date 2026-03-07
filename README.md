<div align="center">

# TraceLens

**RAG Observability, Debugging & Batch Evaluation Backend**

</div>

<p align="center">
  <a href="./README.md"><img alt="English" src="https://img.shields.io/badge/English-DBEDFA"></a>
  <a href="./README_zh.md"><img alt="简体中文" src="https://img.shields.io/badge/简体中文-DFE0E5"></a>
</p>

<p align="center">
  <a href="https://github.com"><img src="https://img.shields.io/badge/License-MIT-ffffff?labelColor=d4eaf7&color=2e6cc4" alt="license"></a>
</p>

<h4 align="center">
  <a href="#-what-is-tracelens">About</a> |
  <a href="#-key-features">Features</a> |
  <a href="#-get-started">Get Started</a> |
  <a href="#-documentation">Documentation</a>
</h4>

<details open>
<summary><b>📕 Table of Contents</b></summary>

- [🔥 Latest Updates](#-latest-updates)
- [💡 What is TraceLens?](#-what-is-tracelens)
- [🌟 Key Features](#-key-features)
- [🎬 Get Started](#-get-started)
- [🔧 Configurations](#-configurations)
- [📚 Documentation](#-documentation)
- [🙌 Contributing](#-contributing)

</details>

## 🔥 Latest Updates

- **2026-03-06** API Key authentication for write endpoints; optional `X-API-Key` header
- **2026-03-06** Alembic migrations; replaced `create_all` with `alembic upgrade head` on startup
- **2026-03-06** Ingest schema validation; Pydantic payload with depth (20) and size (1MB) limits
- **2026-03-06** SDK: long-lived `httpx.Client`, explicit timeout/limits, API key support
- **2026-03-06** Structured logging with `request_id` middleware; replaced `print` with `logger`
- **2026-03-06** Metrics upsert; unique constraint `(run_id, name, similarity_mode)` for idempotent writes
- **2026-03-06** Similarity engine cache: SHA256 keys, LRU maxsize=512
- **2026-03-06** Embedding/LLM provider config via `EMBEDDING_ENDPOINT`, `LLM_ENDPOINT` env vars
- **2026-03-06** Async evaluation: `POST /evaluation/{id}/compute` for background metrics computation

## 💡 What is TraceLens?

[TraceLens](.) is an open-source backend platform for **RAG (Retrieval-Augmented Generation)** and **GraphRAG** systems. It provides:

- **Single-run explainability**: Chunk attribution, retrieval quality metrics, prompt-answer alignment
- **Batch evaluation**: TestSuite/TestCase management, aggregate metrics (avg/p50/p95), version comparison
- **GraphRAG assessment**: Reasoning path quality, connectivity, branch explosion ratio
- **Pluggable similarity engines**: Lexical, Embedding, or LLM Judge

## 🌟 Key Features

### 🍭 Single-Run Analysis

- Chunk attribution: Which chunks were retrieved, used in prompt, and support the answer
- Retrieval quality: Query-chunk similarity, prompt-answer alignment
- Gold-aware metrics: Compare against gold answer/chunks (optional)

### 🍱 Batch Evaluation System

- **TestSuite management**: Create reusable test sets
- **Automated evaluation**: Run multiple test cases in one flow
- **Aggregate metrics**: avg, p50, p95, min, max
- **Version comparison**: Quantify improvements across versions
- **Gold data support**: Optional gold answer / gold chunks / gold docs

### 🌱 GraphRAG Assessment

- Reasoning path quality evaluation
- Graph structure analysis (connectivity, branch explosion ratio)
- Path relevance scoring (with optional LLM Judge)

### 🍔 Flexible Similarity Modes

- **Lexical**: Fast, keyword-based (zero config)
- **Embedding**: Semantic similarity (configurable via `EMBEDDING_ENDPOINT`)
- **LLM Judge**: Subjective scoring (configurable via `LLM_ENDPOINT`)

## 🎬 Get Started

### 📝 Prerequisites

- Python >= 3.10
- PostgreSQL >= 12
- (Optional) External embedding/LLM API for non-lexical similarity modes

### 🚀 Quick Start

1. Clone the repository:

   ```bash
   git clone https://github.com/your-org/tracelens.git
   cd tracelens
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Create the database:

   ```bash
   createdb tracelens
   ```

4. Configure environment (copy `.env.example` to `.env`):

   ```bash
   cp .env.example .env
   # Edit .env: set DATABASE_URL, optionally API_KEY
   ```

5. Start the server:

   ```bash
   uvicorn tracelens.main:app --reload
   ```

6. Verify: `curl http://localhost:8000/health` → `{"status":"ok"}`

### 📌 Usage Example

**Single Run (SDK):**

```python
from sdk.rag_client import RAGClient

client = RAGClient("http://localhost:8000", api_key="your-key")  # api_key optional
run = client.start_run(name="single_query_test")
client.retrieval_completed(run.id, query="What is RAG?", retrieved_chunks=[
    {"chunk_id": "chunk_1", "content": "...", "score": 0.95}
])
client.prompt_built(run.id, ["chunk_1", "chunk_2"])
client.answer_generated(run.id, "RAG is...")
client.run_finished(run.id)
metrics = client.get_metrics(run.id, similarity_mode="lexical")
```

**Batch Evaluation:**

```python
from sdk.evaluation_client import EvaluationClient
from sdk.rag_client import RAGClient

eval_client = EvaluationClient("http://localhost:8000")
rag_client = RAGClient("http://localhost:8000")

test_suite = eval_client.create_test_suite(name="RAG Suite", description="100 test queries")
eval_client.upload_test_cases(test_suite["id"], [
    {"query": "What is RAG?", "gold_answer": "...", "gold_chunk_ids": ["chunk_1"]},
])
evaluation = eval_client.create_evaluation(
    name="v1.0", test_suite_id=test_suite["id"], version_id="v1.0"
)
# Run your RAG over test cases, then:
metrics = eval_client.get_evaluation_metrics(evaluation["id"])
comparison = eval_client.compare_evaluations(eval_v1_id, eval_v2_id)
```

## 🔧 Configurations

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:postgres@localhost:5432/tracelens` |
| `API_KEY` | API key for write endpoints (empty = no auth) | `""` |
| `EMBEDDING_ENDPOINT` | HTTP endpoint for embedding (OpenAI-compatible) | `""` |
| `EMBEDDING_API_KEY` | API key for embedding service | `""` |
| `LLM_ENDPOINT` | HTTP endpoint for LLM (OpenAI chat completions) | `""` |
| `LLM_API_KEY` | API key for LLM service | `""` |

When `API_KEY` is set, all write endpoints require `X-API-Key` header. `/health` is always public.

## 📚 Documentation

- [Quick Start](docs/QUICKSTART.md)
- [RAG Evaluation Guide](docs/RAG_EVALUATION_GUIDE.md)
- [GraphRAG Evaluation Guide](docs/GRAPH_EVALUATION_GUIDE.md)
- [RAG Metrics](docs/RAG_METRICS.md)
- [GraphRAG Metrics](docs/GRAPHRAG_METRICS.md)
- [Similarity Engine](docs/SIMILARITY_ENGINE.md)

### Examples

- [RAG batch evaluation](examples/evaluation_example.py)
- [RAG version comparison](examples/evaluation_comparison_example.py)
- [GraphRAG batch evaluation](examples/graph_evaluation_example.py)
- [Single run (SDK)](examples/rag_sdk_example.py)
- [Similarity modes](examples/similarity_modes_example.py)

## 🙌 Contributing

Contributions are welcome. Please open an Issue or Pull Request.

## License

MIT
