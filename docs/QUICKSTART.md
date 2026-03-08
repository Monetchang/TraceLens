# TraceLens 快速开始

## 安装

```bash
pip install -r requirements.txt
```

## 启动服务

### 本地启动

```bash
# 需要先启动 PostgreSQL，创建数据库 tracelens
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/tracelens"
uvicorn tracelens.main:app --reload
```

### Docker 部署

```bash
# 构建并启动（含 PostgreSQL）
docker compose up -d

# 服务地址 http://localhost:8000
# 启动时自动执行 alembic upgrade head 创建/迁移表
```

如需配置 Embedding/LLM，可创建 `.env` 并挂载：

```bash
# docker-compose.yml 中 app 服务添加
env_file: [.env]
```

## 使用场景

TraceLens 支持两种主要使用场景：
1. **单 Run 分析**：分析单个查询的 RAG 表现
2. **批量评测**：系统化测试多个问题并对比版本（推荐）

---

## 场景 1: 单 Run 分析

### SDK 使用

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
# 查询基础指标（单 run，无需版本对比）
curl http://localhost:8000/api/v1/run/<run_id>/metrics

# 查询扩展指标（单 run，需要配置 embedding/LLM）
curl "http://localhost:8000/api/v1/run/<run_id>/metrics?include_extended=true"

# 版本对比（需要 prev_run_id，基础 + 版本对比指标）
curl "http://localhost:8000/api/v1/run/<run_id>/retrieval_diff?prev_run_id=<prev_run_id>"

# 版本对比 + 扩展指标（new_chunks_query_similarity / dropped_chunks_query_similarity 需要此模式）
curl "http://localhost:8000/api/v1/run/<run_id>/retrieval_diff?prev_run_id=<prev_run_id>&include_extended=true"
```

## 核心指标

> **名词说明**
>
> - **retrieved_chunks**：检索阶段返回的所有候选 chunks，通过 `retrieval_completed` 上报。
> - **prompt_chunks**：从 retrieved_chunks 中筛选后、实际放入 LLM prompt 的 chunks，通过 `prompt_built` 上报。两者数量不同：retrieved_chunks 是候选集，prompt_chunks 是最终使用集。
> - **topK chunks**：prompt_chunks 中排名前 K 个（默认 K=5），用于评估最关键 chunks 的质量。

### 基础指标（需要传入 `prev_run_id` 做版本对比时计算）
- `new_chunks_ratio`: 相比上一版本，新增 retrieved chunks 的占比
- `rank_deltas`: 相同 chunk 在两个版本中的排名变化

### 扩展指标（需要 embedding 或 LLM）

**单 run 指标**（无需版本对比，每次 run 独立计算）：
- `topK_chunk_query_similarity`: prompt_chunks 前 K 个与 query 的关联度，衡量检索头部质量
- `prompt_chunk_answer_similarity`: 所有 prompt_chunks 对 answer 的支撑度，衡量 chunks 对最终回答的贡献
- `exact_recall_vs_gold_chunks`: retrieved_chunks 对 gold chunks 的 chunk_id 精确命中率（需要上报 gold_chunks，可选）

**版本对比指标**（需要传入 `prev_run_id`，对比两个版本的 retrieved_chunks 差异）：
- `new_chunks_query_similarity`: 本版本相比上一版本**新增**的 retrieved chunks 与 query 的关联度，值高说明新引入的 chunks 是有效的
- `dropped_chunks_query_similarity`: 本版本相比上一版本**丢失**的 retrieved chunks 与 query 的关联度，值高说明丢掉的是好 chunks（需关注）

## 示例代码

TraceLens 提供三个示例：

1. **API 接口接入** ([`examples/rag_api_example.py`](../examples/rag_api_example.py))
   - 直接使用 HTTP API 调用
   - 适合任何语言的集成

2. **SDK 接入** ([`examples/rag_sdk_example.py`](../examples/rag_sdk_example.py))
   - 使用 Python SDK
   - 更简洁的 API

3. **批量评测** ([`examples/evaluation_example.py`](../examples/evaluation_example.py))
   - 演示如何对比两个版本的检索结果
   - 展示版本对比指标的使用

## Event 约定

> 上报顺序应与 RAG pipeline 执行顺序保持一致，TraceLens 按时序关联各阶段数据。

- `retrieval_completed`: 检索完成，上报所有检索到的 chunks（retrieved_chunks）及 query
- `prompt_built`: prompt 构建完成，上报实际进入 LLM prompt 的 chunks（prompt_chunks，是 retrieved_chunks 的子集）
- `answer_generated`: LLM 生成完成，上报 answer 文本
- `gold_chunks`: 上报标注的正确 chunks（可选，用于 `exact_recall_vs_gold_chunks` 指标）
- `run_finished`: run 结束，上报状态（success/failure）

## 关联度计算模式

> **完整说明**：Lexical / Embedding / LLM 三种模式的计算原理、配置方式、Asymmetric Embedding 支持模型等详见 **[相似度引擎文档](SIMILARITY_ENGINE.md)**。

TraceLens 提供三种模式计算 chunk 与 query 的**关联度**、chunk 对 answer 的**支撑度**（lexical/embedding 用相似度近似）：

### 1. Lexical 模式（默认，零配置）
```python
metrics = rag_client.get_metrics(run_id, similarity_mode="lexical")
```
- 特点：基于 TF-IDF 的词法相似度近似关联度
- 适用：日常开发，快速评估
- 成本：免费

### 2. Embedding 模式

**配置方式：设置环境变量，无需编写任何代码**

```python
metrics = rag_client.get_metrics(run_id, similarity_mode="embedding")
```

TraceLens 会自动识别主流 embedding 接口的响应格式，包括 OpenAI 格式、Ollama 格式和腾讯混元原生格式。

#### 各平台接入配置

**OpenAI**
```bash
export EMBEDDING_ENDPOINT="https://api.openai.com/v1/embeddings"
export EMBEDDING_API_KEY="sk-..."
export EMBEDDING_MODEL="text-embedding-3-small"
```

**阿里云百炼（Qwen Embedding，兼容 OpenAI 格式）**
```bash
export EMBEDDING_ENDPOINT="https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"
export EMBEDDING_API_KEY="sk-..."
export EMBEDDING_MODEL="text-embedding-v3"
```

**腾讯混元（OpenAI 兼容接口）**
```bash
export EMBEDDING_ENDPOINT="https://api.hunyuan.cloud.tencent.com/v1/embeddings"
export EMBEDDING_API_KEY="..."
export EMBEDDING_MODEL="hunyuan-embedding"
```

> 腾讯混元也提供原生 API（响应格式为 `Response.Data[].Embedding`），TraceLens 同样支持。

**Ollama（本地部署）**
```bash
export EMBEDDING_ENDPOINT="http://localhost:11434/api/embed"
export EMBEDDING_MODEL="nomic-embed-text"
# Ollama 本地部署无需 API Key，留空即可
```

> Ollama 使用 `/api/embed` 接口，响应格式为 `{"embeddings": [[...]]}` 而非 OpenAI 的 `data[].embedding`，TraceLens 已做兼容处理。

**vLLM / 其他 OpenAI 兼容服务**
```bash
export EMBEDDING_ENDPOINT="http://your-vllm-host/v1/embeddings"
export EMBEDDING_MODEL="your-model-name"
```

**高级用法：自定义 embedding function（接入任意本地 SDK）**

```python
import numpy as np
from tracelens.similarity import get_similarity_engine
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("BAAI/bge-m3")

def my_embed(text: str) -> np.ndarray:
    return model.encode(text)

engine = get_similarity_engine("embedding", {"embedding_function": my_embed})
```

- 适用：生产环境，精确评估
- 成本：低（~$0.0001/1K tokens）

### 3. LLM 模式

**配置方式：设置环境变量，无需编写任何代码**

```python
metrics = rag_client.get_metrics(run_id, similarity_mode="llm")
```

所有兼容 OpenAI Chat Completions API 的服务均可直接接入。

#### 各平台接入配置

**OpenAI**
```bash
export LLM_ENDPOINT="https://api.openai.com/v1/chat/completions"
export LLM_API_KEY="sk-..."
export LLM_MODEL="gpt-4o-mini"
```

**DeepSeek**
```bash
export LLM_ENDPOINT="https://api.deepseek.com/v1/chat/completions"
export LLM_API_KEY="sk-..."
export LLM_MODEL="deepseek-chat"
```

**Kimi（Moonshot AI）**
```bash
export LLM_ENDPOINT="https://api.moonshot.cn/v1/chat/completions"
export LLM_API_KEY="sk-..."
export LLM_MODEL="moonshot-v1-8k"
```

**MiniMax**
```bash
export LLM_ENDPOINT="https://api.minimax.chat/v1/text/chatcompletion_v2"
export LLM_API_KEY="..."
export LLM_MODEL="MiniMax-Text-01"
```

**阿里云百炼（Qwen）**
```bash
export LLM_ENDPOINT="https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
export LLM_API_KEY="sk-..."
export LLM_MODEL="qwen-turbo"
```

**腾讯混元**
```bash
export LLM_ENDPOINT="https://api.hunyuan.cloud.tencent.com/v1/chat/completions"
export LLM_API_KEY="..."
export LLM_MODEL="hunyuan-turbos-latest"
```

**Ollama（本地部署 LLM）**
```bash
export LLM_ENDPOINT="http://localhost:11434/v1/chat/completions"
export LLM_MODEL="qwen2.5:7b"
# Ollama 本地部署无需 API Key
```

> Ollama 的 `/v1/chat/completions` 接口兼容 OpenAI 格式，直接可用。

**高级用法：自定义 LLM function**

```python
from openai import OpenAI
from tracelens.similarity import get_similarity_engine

client = OpenAI(api_key="sk-...", base_url="https://api.deepseek.com/v1")

def my_llm(prompt: str) -> str:
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}]
    )
    return resp.choices[0].message.content

engine = get_similarity_engine("llm", {"llm_client": my_llm})
```

- 特点：使用 LLM 直接判断 query-chunk 关联度、chunk-answer 支撑度
- 适用：Benchmark，关键决策
- 成本：高（~$0.01/1K tokens）

---

## 场景 2: 批量评测（推荐）

批量评测让你能够系统化地评估 RAG 系统在多个测试问题上的表现，并对比不同版本的改进效果。

### 完整工作流

```python
from sdk.evaluation_client import EvaluationClient
from sdk.rag_client import RAGClient

eval_client = EvaluationClient("http://localhost:8000")
rag_client = RAGClient("http://localhost:8000")

# Step 1: 创建测试集
test_suite = eval_client.create_test_suite(
    name="RAG Test Suite",
    description="标准测试集，包含100个问题"
)
test_suite_id = test_suite["id"]

# Step 2: 上传测试用例
test_cases = [
    {
        "query": "What is RAG?",
        "gold_answer": "RAG stands for Retrieval-Augmented Generation...",
        "gold_chunk_ids": ["chunk_1", "chunk_2"],
        "metadata": {"category": "concept"}
    },
    # ... 更多测试用例
]
eval_client.upload_test_cases(test_suite_id, test_cases)

# Step 3: 创建评测任务（v1.0）
evaluation_v1 = eval_client.create_evaluation(
    name="RAG System v1.0 Evaluation",
    test_suite_id=test_suite_id,
    version_id="v1.0",
    metadata={"embedding_model": "text-embedding-ada-002", "chunk_size": 512}
)
eval_v1_id = evaluation_v1["id"]

# Step 4: 运行评测
test_cases_to_run = eval_client.get_evaluation_test_cases(eval_v1_id)
for tc in test_cases_to_run:
    # 创建 run，自动关联 test_case（自动加载 gold 数据）
    run = rag_client.start_run(
        name=f"v1.0_{tc['id']}",
        evaluation_id=eval_v1_id,
        test_case_id=tc["id"]
    )
    
    # 运行你的 RAG 系统
    retrieved_chunks = your_rag_system.retrieve(tc["query"])
    # retrieved_chunks: 检索返回的全部候选 chunks
    rag_client.retrieval_completed(run.id, retrieved_chunks, tc["query"])
    
    # prompt_chunks: 从 retrieved_chunks 中筛选后实际放入 prompt 的 chunks（子集）
    prompt_chunks = your_rag_system.build_prompt(retrieved_chunks)
    rag_client.prompt_built(run.id, prompt_chunks)
    
    answer = your_rag_system.generate(tc["query"], prompt_chunks)
    rag_client.answer_generated(run.id, answer)
    
    rag_client.run_finished(run.id, status="success")

# Step 5: 获取聚合指标
metrics_v1 = eval_client.get_evaluation_metrics(eval_v1_id, similarity_mode="lexical")
print(f"v1.0 指标:")
for metric_name, stats in metrics_v1["aggregate_metrics"].items():
    print(f"  {metric_name}:")
    print(f"    avg: {stats['avg']:.4f}, p50: {stats['p50']:.4f}, p95: {stats['p95']:.4f}")

# Step 6: 运行 v2.0 评测（假设修改了系统）
evaluation_v2 = eval_client.create_evaluation(
    name="RAG System v2.0 Evaluation",
    test_suite_id=test_suite_id,  # 复用同一测试集
    version_id="v2.0",
    metadata={"embedding_model": "text-embedding-3-large", "chunk_size": 256}
)
# ... 重复运行流程 ...

# Step 7: 版本对比
comparison = eval_client.compare_evaluations(
    eval_a_id=eval_v1_id,
    eval_b_id=eval_v2_id,
    similarity_mode="lexical"
)

print(f"\n版本对比: {comparison['evaluation_a']['version_id']} → {comparison['evaluation_b']['version_id']}")
for metric_name, delta_stats in comparison["metrics_delta"].items():
    delta = delta_stats["delta"]
    percent_change = delta_stats["percent_change"]
    print(f"  {metric_name}: {delta:+.4f} ({percent_change:+.2f}%)")
```

### 批量评测 API

```bash
# 1. 创建测试集
curl -X POST http://localhost:8000/api/v1/test_suite \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Suite", "description": "..."}'

# 2. 上传测试用例
curl -X POST http://localhost:8000/api/v1/test_suite/{suite_id}/test_cases \
  -H "Content-Type: application/json" \
  -d '{
    "test_cases": [
      {
        "query": "What is RAG?",
        "gold_answer": "...",
        "gold_chunk_ids": ["chunk_1", "chunk_2"]
      }
    ]
  }'

# 3. 创建评测任务
curl -X POST http://localhost:8000/api/v1/evaluation \
  -H "Content-Type: application/json" \
  -d '{
    "name": "v1.0 Evaluation",
    "test_suite_id": "...",
    "version_id": "v1.0"
  }'

# 4. 获取测试用例（供 RAG 系统遍历）
curl http://localhost:8000/api/v1/evaluation/{evaluation_id}/test_cases

# 5. 创建 run（自动关联 test_case）
curl -X POST http://localhost:8000/api/v1/run/start \
  -H "Content-Type: application/json" \
  -d '{
    "name": "eval_run",
    "evaluation_id": "...",
    "test_case_id": "..."
  }'

# 6. 获取聚合指标
curl "http://localhost:8000/api/v1/evaluation/{evaluation_id}/metrics?similarity_mode=lexical"

# 7. 版本对比
curl "http://localhost:8000/api/v1/evaluation/compare?eval_a={id_a}&eval_b={id_b}"
```

### 聚合指标说明

批量评测提供以下统计维度：
- **avg (均值)**: 所有 run 的平均值
- **p50 (中位数)**: 抗异常值干扰，反映"典型"表现
- **p95 (95分位数)**: 识别边缘情况和异常值
- **min / max**: 最佳/最差表现

---

## 关联度计算模式（批量评测）

配置方式与单 Run 分析相同，调用时传入 `similarity_mode` 即可。各平台环境变量配置、Asymmetric Embedding 等详见 **[相似度引擎文档](SIMILARITY_ENGINE.md)**。

```python
# Lexical（默认，零配置）
metrics = eval_client.get_evaluation_metrics(eval_id, similarity_mode="lexical")

# Embedding（需配置 EMBEDDING_ENDPOINT / EMBEDDING_API_KEY / EMBEDDING_MODEL）
metrics = eval_client.get_evaluation_metrics(eval_id, similarity_mode="embedding")

# LLM（需配置 LLM_ENDPOINT / LLM_API_KEY / LLM_MODEL）
metrics = eval_client.get_evaluation_metrics(eval_id, similarity_mode="llm")
```

---

## 文档索引

- **[RAG 批量评测指南](RAG_EVALUATION_GUIDE.md)** - RAG 批量评测与版本对比
- **[RAG 指标文档](RAG_METRICS.md)** - 单 run 指标详解
- **[GraphRAG 批量评测指南](GRAPH_EVALUATION_GUIDE.md)** - GraphRAG 批量评测
- **[GraphRAG 指标文档](GRAPHRAG_METRICS.md)** - GraphRAG 推理路径指标
- **[相似度引擎](SIMILARITY_ENGINE.md)** - 关联度计算模式详解（Lexical / Embedding / LLM、各平台配置、Asymmetric Embedding）
