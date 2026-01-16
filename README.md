# TraceLens

RAG 可解释性与调试后端系统。追踪 chunk 对 RAG 答案的贡献。

## 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动 PostgreSQL 并创建数据库
createdb tracelens

# 3. 设置环境变量（可选）
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/tracelens"
export OVERLAP_EPSILON=0.01

# 4. 启动服务
uvicorn app.main:app --reload
```

## API

### 1. 创建 Run
```bash
curl -X POST http://localhost:8000/api/v1/run \
  -H "Content-Type: application/json" \
  -d '{"app_id": "my-app", "query": "什么是RAG?", "index_version": "v1"}'
```

### 2. 记录检索结果
```bash
curl -X POST http://localhost:8000/api/v1/retrieval \
  -H "Content-Type: application/json" \
  -d '{
    "run_id": "<run_id>",
    "retriever_name": "dense",
    "top_k": 5,
    "chunks": [
      {"chunk_id": "<uuid>", "doc_id": "doc1", "content": "RAG是检索增强生成...", "score": 0.95, "rank": 1}
    ]
  }'
```

### 3. 记录 Prompt Chunks
```bash
curl -X POST http://localhost:8000/api/v1/prompt/chunks \
  -H "Content-Type: application/json" \
  -d '{
    "run_id": "<run_id>",
    "chunks": [{"chunk_id": "<uuid>", "order_index": 0}]
  }'
```

### 4. 记录答案
```bash
curl -X POST http://localhost:8000/api/v1/answer \
  -H "Content-Type: application/json" \
  -d '{"run_id": "<run_id>", "answer_text": "RAG是检索增强生成技术..."}'
```

### 5. 获取指标
```bash
curl http://localhost:8000/api/v1/run/<run_id>/rag-metrics
```

返回：
```json
{
  "run_id": "<uuid>",
  "total_answer_tokens": 50,
  "retrieved_chunks": 5,
  "prompt_chunks": 3,
  "used_chunks": 2,
  "retrieval_utilization": 0.4,
  "pollution_rate": 0.33,
  "attributions": [
    {"chunk_id": "<uuid>", "overlap_tokens": 15, "overlap_ratio": 0.3, "used": true}
  ]
}
```

### 6. 对比不同版本
```bash
curl "http://localhost:8000/api/v1/diff?run_a=<run_id_a>&run_b=<run_id_b>"
```

## 指标说明

| 指标 | 公式 |
|------|------|
| `overlap_ratio` | `overlap_tokens / total_answer_tokens` |
| `chunk_used` | `overlap_ratio > epsilon` |
| `retrieval_utilization` | `used_chunks / retrieved_chunks` |
| `pollution_rate` | `unused_prompt_chunks / total_prompt_chunks` |

