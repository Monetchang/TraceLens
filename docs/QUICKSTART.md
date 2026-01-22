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
    rag_client.retrieval_completed(run.id, retrieved_chunks, tc["query"])
    
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

## 相似度模式

TraceLens 提供三种相似度计算模式：

### 1. Lexical 模式（默认，零配置）
```python
metrics = eval_client.get_evaluation_metrics(eval_id, similarity_mode="lexical")
```
- 特点：基于 TF-IDF 的词法相似度
- 适用：日常开发，快速评估
- 成本：免费

### 2. Embedding 模式（需要配置）
```python
metrics = eval_client.get_evaluation_metrics(eval_id, similarity_mode="embedding")
```
- 特点：基于 embedding 的语义相似度
- 适用：生产环境，精确评估
- 成本：低（~$0.0001/1K tokens）

### 3. LLM 模式（需要配置）
```python
metrics = eval_client.get_evaluation_metrics(eval_id, similarity_mode="llm")
```
- 特点：使用 LLM 判断相似度
- 适用：Benchmark，关键决策
- 成本：高（~$0.01/1K tokens）

---

## 文档索引

- **[批量评测指南](EVALUATION_GUIDE.md)** - 完整的批量评测使用指南
- **[RAG 指标文档](RAG_METRICS.md)** - 单 run 指标详解
- **[GraphRAG 指标文档](GRAPHRAG_METRICS.md)** - GraphRAG 评估详解
- **[相似度引擎文档](SIMILARITY_ENGINE.md)** - 三种相似度计算模式
- **[README](README.md)** - 项目概览
