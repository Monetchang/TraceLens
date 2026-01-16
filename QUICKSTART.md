# TraceLens 快速开始

## 安装

```bash
pip install -r requirements.txt
```

## 启动服务

```bash
# 需要先启动 PostgreSQL，创建数据库 tracelens
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/tracelens"
uvicorn tracelens.main:app --reload
```

## SDK 使用

### 基础示例

```python
from sdk.rag_client import RAGClient
from sdk.client import TraceLensClient

# 初始化客户端
base_client = TraceLensClient("http://localhost:8000")
rag_client = RAGClient("http://localhost:8000")

# 1. 创建 run
run = base_client.start_run(
    name="rag_query",
    metadata={"version_id": "v1.0"}
)

# 2. 上报检索结果
rag_client.retrieval_completed(
    run_id=run.id,
    query="What is RAG?",
    retrieved_chunks=[
        {"chunk_id": "c1", "score": 0.95, "content": "..."},
        {"chunk_id": "c2", "score": 0.87, "content": "..."}
    ]
)

# 3. 上报 prompt chunks
rag_client.prompt_built(run.id, ["c1", "c2"])

# 4. 上报 answer
rag_client.answer_generated(run.id, "RAG is a technique...")

# 5. 结束 run
rag_client.run_finished(run.id, "success")

# 6. 查询指标
metrics = rag_client.get_metrics(run.id, include_extended=True)
print(metrics['metrics'])
print(metrics['extended_metrics'])
```

## API 接口

### 上报接口

```bash
# 1. 创建 run
curl -X POST http://localhost:8000/api/v1/run/start \
  -H "Content-Type: application/json" \
  -d '{"name": "test_run", "metadata": {"version_id": "v1.0"}}'

# 2. 上报检索结果
curl -X POST http://localhost:8000/api/v1/retrieval/completed \
  -H "Content-Type: application/json" \
  -d '{
    "run_id": "<run_id>",
    "query": "What is RAG?",
    "retrieved_chunks": [
      {"chunk_id": "c1", "score": 0.95, "content": "..."}
    ]
  }'

# 3. 上报 prompt chunks
curl -X POST http://localhost:8000/api/v1/prompt/built \
  -H "Content-Type: application/json" \
  -d '{"run_id": "<run_id>", "prompt_chunks": ["c1", "c2"]}'

# 4. 上报 answer
curl -X POST http://localhost:8000/api/v1/answer/generated \
  -H "Content-Type: application/json" \
  -d '{"run_id": "<run_id>", "answer": "RAG is a technique..."}'

# 5. 结束 run
curl -X POST http://localhost:8000/api/v1/run/finished \
  -H "Content-Type: application/json" \
  -d '{"run_id": "<run_id>", "status": "success"}'
```

### 查询接口

```bash
# 查询基础指标
curl http://localhost:8000/api/v1/run/<run_id>/metrics

# 查询扩展指标（需要配置 embedding）
curl "http://localhost:8000/api/v1/run/<run_id>/metrics?include_extended=true"

# 版本对比
curl "http://localhost:8000/api/v1/run/<run_id>/retrieval_diff?prev_run_id=<prev_run_id>"

# 版本对比 + 扩展指标
curl "http://localhost:8000/api/v1/run/<run_id>/retrieval_diff?prev_run_id=<prev_run_id>&include_extended=true"
```

## 核心指标

### 基础指标（版本对比）
- `new_chunks_ratio`: 新增 chunks 比例
- `rank_deltas`: 排名变化

### 扩展指标（需要 embedding）
- `topK_chunk_query_similarity`: Top-K chunks 与 query 的相似度
- `prompt_chunk_answer_similarity`: prompt chunks 与 answer 的相似度
- `semantic_recall_vs_gold`: 相对于 gold chunks 的召回率（可选）
- `new_chunks_query_similarity`: 新增 chunks 与 query 的相似度
- `dropped_chunks_query_similarity`: 丢弃 chunks 与 query 的相似度

## 示例代码

TraceLens 提供三个示例：

1. **API 接口接入** (`examples/rag_api_example.py`)
   - 直接使用 HTTP API 调用
   - 适合任何语言的集成

2. **SDK 接入** (`examples/rag_sdk_example.py`)
   - 使用 Python SDK
   - 更简洁的 API

3. **版本对比** (`examples/rag_version_diff_example.py`)
   - 演示如何对比两个版本的检索结果
   - 展示版本对比指标的使用

## Event 约定

- `retrieval_completed`: 检索完成，上报所有检索到的 chunks
- `prompt_built`: prompt 构建完成，上报使用的 chunks
- `answer_generated`: answer 生成完成，上报 answer 文本
- `gold_chunks`: 上报 gold chunks（可选）
- `run_finished`: run 结束

## 相似度模式

TraceLens 提供三种相似度计算模式：

### 1. Lexical 模式（默认，零配置）
```python
metrics = rag_client.get_metrics(run_id, similarity_mode="lexical")
```
- 特点：基于 TF-IDF 的词法相似度
- 适用：日常开发，快速评估
- 成本：免费

### 2. Embedding 模式（需要配置）
```python
# 配置 embedding function
from tracelens.similarity import get_similarity_engine

engine = get_similarity_engine("embedding", {
    "embedding_function": your_embed_function
})

# 使用
metrics = rag_client.get_metrics(run_id, similarity_mode="embedding")
```
- 特点：基于 embedding 的语义相似度
- 适用：生产环境，精确评估
- 成本：低（~$0.0001/1K tokens）

### 3. LLM 模式（需要配置）
```python
# 配置 LLM client
engine = get_similarity_engine("llm", {
    "llm_client": your_llm_client
})

# 使用
metrics = rag_client.get_metrics(run_id, similarity_mode="llm")
```
- 特点：使用 LLM 判断相似度
- 适用：Benchmark，关键决策
- 成本：高（~$0.01/1K tokens）

详细文档请参考：
- `RAG_METRICS.md` - 指标文档
- `SIMILARITY_ENGINE.md` - 相似度引擎文档
