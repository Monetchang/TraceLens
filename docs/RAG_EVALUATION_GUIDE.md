# RAG 批量评测指南

## 目录

1. [概述](#概述)
2. [核心概念](#核心概念)
3. [前置条件](#前置条件)
4. [完整工作流](#完整工作流)
5. [API 参考](#api-参考)
6. [SDK 使用](#sdk-使用)
7. [聚合指标解读](#聚合指标解读)
8. [版本对比最佳实践](#版本对比最佳实践)
9. [常见问题](#常见问题)

---

## 概述

**RAG 批量评测**是 TraceLens 提供的系统化评估 RAG 系统的能力，专注于**检索质量**和**召回率**的评估。

### 为什么需要 RAG 批量评测？

在 RAG 系统开发中，你可能需要：
- 评估检索策略的效果
- 对比不同 embedding 模型的表现
- 调优 `top_k`、`chunk_size` 等参数
- 评估版本迭代效果

**RAG 批量评测让这些从"凭感觉"变成"有数据支撑"的决策。**

### RAG 评测 vs GraphRAG 评测

| 维度 | RAG 批量评测 | GraphRAG 批量评测 |
|------|-------------|------------------|
| **关注点** | **检索质量**、召回率 | 推理效率、路径质量、连通性 |
| **Gold 数据** | **gold_answer**, **gold_chunk_ids**, **gold_doc_ids** | gold_path, gold_nodes |
| **关键指标** | **topK_chunk_query_similarity**, **semantic_recall_vs_gold** | branch_explosion_ratio, reasoning_hops |
| **版本对比重点** | **检索结果变化** | 推理跳数变化、分支爆炸比改善 |

---

## 核心概念

### 1. TestSuite（测试集）

一组测试问题的集合，可以被多个评测任务复用。

**示例**：
```python
test_suite = {
    "name": "RAG System Test Suite",
    "description": "标准测试集，包含100个典型问题"
}
```

### 2. TestCase（测试用例）

单个测试问题，包含：

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `query` | string | ✅ | 测试问题 |
| `gold_answer` | string | ❌ | 正确答案 |
| `gold_chunk_ids` | list[str] | ❌ | 正确检索片段 ID 列表 |
| `gold_doc_ids` | list[str] | ❌ | 正确文档 ID 列表 |
| `metadata` | object | ❌ | 其他元数据（如分类、难度） |

**Gold 数据设计**：

- **gold_answer**：标准答案，用于计算答案相似度
- **gold_chunk_ids**：应该检索到的 chunk ID 列表，用于计算召回率
- **gold_doc_ids**：应该检索到的文档 ID 列表

**示例**：
```python
test_case = {
    "query": "What is RAG?",
    "gold_answer": "RAG stands for Retrieval-Augmented Generation...",
    "gold_chunk_ids": ["chunk_001", "chunk_002"],
    "gold_doc_ids": ["doc_001"],
    "metadata": {"category": "concept", "difficulty": "easy"}
}
```

### 3. Evaluation（评测任务）

针对一个 TestSuite 的**特定版本** RAG 系统的评测任务。

**关键字段**：
- `version_id`: 版本标识（如 `"v1.0"`, `"v2.0"`）
- `test_suite_id`: 关联的测试集
- `metadata`: 可选的配置信息（如 `{"embedding_model": "text-embedding-ada-002", "chunk_size": 512}`）

### 4. Run

评测任务中的单次执行，对应一个 TestCase。

**自动关联**：
- 当 `start_run` 时提供 `test_case_id`，会自动加载 `query` 和 `gold_chunk_ids`

---

## 前置条件

在进行批量评测之前，你的 RAG 系统必须已经集成了 TraceLens 的数据上报接口。

### 必需的上报接口

根据 [`RAG_METRICS.md`](RAG_METRICS.md)，RAG 系统需要上报：

1. **检索结果**: `POST /api/v1/retrieval/completed`
2. **Prompt 构建**: `POST /api/v1/prompt/built`
3. **答案生成**: `POST /api/v1/answer/generated`
4. **Run 结束**: `POST /api/v1/run/finished`

### 集成方式

#### 方式一：使用 SDK（推荐）

```python
from sdk.rag_client import RAGClient

rag_client = RAGClient("http://localhost:8000")

def your_rag_system_retrieve(query: str, run_id: UUID):
    # 你的检索逻辑
    retrieved_chunks = your_retrieval_logic(query)
    
    # 上报检索结果到 TraceLens
    rag_client.retrieval_completed(
        run_id=run_id,
        query=query,
        retrieved_chunks=retrieved_chunks
    )
    return retrieved_chunks

def your_rag_system_generate(query: str, chunks: list, run_id: UUID):
    # 构建 prompt
    prompt_chunks = your_prompt_builder(chunks)
    rag_client.prompt_built(run_id, prompt_chunks)
    
    # 生成答案
    answer = your_llm_call(query, prompt_chunks)
    rag_client.answer_generated(run_id, answer)
    
    return answer
```

#### 方式二：直接调用 API

```python
import httpx

def your_rag_system_retrieve(query: str, run_id: str):
    retrieved_chunks = your_retrieval_logic(query)
    
    # 上报到 TraceLens
    httpx.post("http://localhost:8000/api/v1/retrieval/completed", json={
        "run_id": run_id,
        "query": query,
        "retrieved_chunks": retrieved_chunks
    })
    return retrieved_chunks
```

**重要提示**：如果你的 RAG 系统尚未集成上报接口，批量评测将无法计算指标。请先完成集成，再进行批量评测。

详细的集成指南和示例代码，请参考：
- [`RAG_METRICS.md`](RAG_METRICS.md) 中的 "数据上报" 章节
- [`QUICKSTART.md`](QUICKSTART.md) 中的 "SDK 使用"

---

## 完整工作流

### Step 1: 创建测试集

```python
from sdk.evaluation_client import EvaluationClient

eval_client = EvaluationClient(base_url="http://localhost:8000")

test_suite = eval_client.create_test_suite(
    name="RAG System Test Suite",
    description="标准测试集，包含100个典型问题"
)
```

### Step 2: 上传测试用例

```python
from uuid import UUID

test_cases = [
    {
        "query": "What is RAG?",
        "gold_answer": "RAG stands for Retrieval-Augmented Generation...",
        "gold_chunk_ids": ["chunk_001", "chunk_002"],
        "gold_doc_ids": ["doc_001"],
        "metadata": {"category": "concept", "difficulty": "easy"}
    },
    {
        "query": "How does vector database work?",
        "gold_answer": "Vector databases store embeddings...",
        "gold_chunk_ids": ["chunk_010", "chunk_011"],
        "metadata": {"category": "technical"}
    },
    # ... 更多测试用例
]

result = eval_client.upload_test_cases(UUID(test_suite["id"]), test_cases)
print(f"已上传 {result['created_count']} 个测试用例")
```

**支持的 Gold 数据**：
- 全部提供：`gold_answer`, `gold_chunk_ids`, `gold_doc_ids`
- 部分提供：如只提供 `gold_chunk_ids`
- 都不提供：纯 gold-optional 评测

### Step 3: 创建评测任务 v1.0

```python
evaluation_v1 = eval_client.create_evaluation(
    name="RAG System v1.0 Evaluation",
    test_suite_id=UUID(test_suite["id"]),
    version_id="v1.0",
    metadata={
        "embedding_model": "text-embedding-ada-002",
        "chunk_size": 512,
        "top_k": 5
    }
)
```

### Step 4: 运行评测

**核心步骤**：
1. 获取测试用例列表
2. 对每个测试用例，启动 run（关联 `evaluation_id` 和 `test_case_id`）
3. 调用你的 RAG 系统（已集成上报接口）
4. 结束 run

```python
from sdk.rag_client import RAGClient

rag_client = RAGClient(base_url="http://localhost:8000")

# 获取测试用例
test_cases_to_run = eval_client.get_evaluation_test_cases(UUID(evaluation_v1["id"]))

for tc in test_cases_to_run:
    # 启动 run，自动关联 test_case 的 gold_chunk_ids
    run = rag_client.start_run(
        name=f"v1.0_{tc['id']}",
        evaluation_id=evaluation_v1["id"],
        test_case_id=tc["id"]
    )
    
    try:
        # 运行你的 RAG 系统（已集成上报接口）
        query = tc["query"]
        
        # 1. 检索（内部会调用 rag_client.retrieval_completed）
        retrieved_chunks = your_rag_system.retrieve(query, run.id)
        
        # 2. 构建 Prompt（内部会调用 rag_client.prompt_built）
        prompt_chunks = your_rag_system.build_prompt(retrieved_chunks)
        
        # 3. 生成答案（内部会调用 rag_client.answer_generated）
        answer = your_rag_system.generate(query, prompt_chunks, run.id)
        
        # 4. 结束 run
        rag_client.run_finished(run.id, status="success")
    except Exception as e:
        print(f"Run {run.id} failed: {e}")
        rag_client.run_finished(run.id, status="error")
```

**自动加载 Gold 数据**：
当你创建 run 时提供 `test_case_id`，系统会自动：
- 从 TestCase 加载 `query`
- 如果有 `gold_chunk_ids`，自动创建 `GoldChunk` 记录
- 评测指标计算时会自动使用这些 gold 数据

### Step 5: 获取聚合指标

```python
# 获取评测进度
status = eval_client.get_evaluation_status(UUID(evaluation_v1["id"]))
print(f"进度: {status['completed_runs']}/{status['total_test_cases']} ({status['progress']*100:.1f}%)")

# 获取聚合指标
metrics_v1 = eval_client.get_evaluation_metrics(
    UUID(evaluation_v1["id"]),
    similarity_mode="lexical",  # 或 "embedding", "llm"
    include_per_query=False
)

print(f"版本: {metrics_v1['version_id']}")
print(f"完成: {metrics_v1['completed_runs']}/{metrics_v1['total_runs']}")

for metric_name, stats in metrics_v1["aggregate_metrics"].items():
    print(f"{metric_name}:")
    print(f"  avg: {stats['avg']:.4f}")
    print(f"  p50: {stats['p50']:.4f}")
    print(f"  p95: {stats['p95']:.4f}")
```

### Step 6: 运行 v2.0 评测

```python
# 创建 v2.0 评测任务
evaluation_v2 = eval_client.create_evaluation(
    name="RAG System v2.0 Evaluation",
    test_suite_id=UUID(test_suite["id"]),
    version_id="v2.0",
    metadata={
        "embedding_model": "text-embedding-3-large",
        "chunk_size": 512,
        "top_k": 5
    }
)

# 运行评测（代码与 v1.0 类似）
# ...
```

### Step 7: 版本对比

```python
comparison = eval_client.compare_evaluations(
    eval_a_id=UUID(evaluation_v1["id"]),
    eval_b_id=UUID(evaluation_v2["id"]),
    similarity_mode="lexical"
)

# 分析检索质量
retrieval_delta = comparison["metrics_delta"]["topK_chunk_query_similarity"]
print(f"检索质量: {retrieval_delta['avg_a']:.4f} → {retrieval_delta['avg_b']:.4f}")
print(f"改善: {retrieval_delta['percent_change']:.1f}%")

# 分析召回率
if "semantic_recall_vs_gold" in comparison["metrics_delta"]:
    recall_delta = comparison["metrics_delta"]["semantic_recall_vs_gold"]
    print(f"召回率: {recall_delta['avg_a']:.4f} → {recall_delta['avg_b']:.4f}")
```

---

## API 参考

### 1. 创建测试集

```http
POST /api/v1/test_suite
Content-Type: application/json

{
  "name": "RAG System Test Suite",
  "description": "标准测试集，包含100个典型问题"
}
```

### 2. 批量上传测试用例

```http
POST /api/v1/test_suite/{suite_id}/test_cases
Content-Type: application/json

{
  "test_cases": [
    {
      "query": "What is RAG?",
      "gold_answer": "...",
      "gold_chunk_ids": ["chunk_1", "chunk_2"],
      "gold_doc_ids": ["doc_1"],
      "metadata": {"category": "concept"}
    }
  ]
}
```

### 3. 创建评测任务

```http
POST /api/v1/evaluation
Content-Type: application/json

{
  "name": "RAG System v1.0 Evaluation",
  "test_suite_id": "uuid",
  "version_id": "v1.0",
  "metadata": {"embedding_model": "text-embedding-ada-002"}
}
```

### 4. 获取聚合指标

```http
GET /api/v1/evaluation/{evaluation_id}/metrics?similarity_mode=lexical&include_per_query=false
```

**响应示例**：

```json
{
  "evaluation_id": "uuid",
  "version_id": "v1.0",
  "total_runs": 100,
  "completed_runs": 98,
  "aggregate_metrics": {
    "topK_chunk_query_similarity": {
      "avg": 0.78,
      "p50": 0.80,
      "p95": 0.92,
      "min": 0.45,
      "max": 0.98
    },
    "prompt_chunk_answer_similarity": {
      "avg": 0.82,
      "p50": 0.85,
      "p95": 0.94,
      "min": 0.50,
      "max": 0.99
    },
    "semantic_recall_vs_gold": {
      "avg": 0.85,
      "p50": 0.90,
      "p95": 1.0,
      "min": 0.33,
      "max": 1.0
    }
  },
  "per_query_metrics": null
}
```

### 5. 对比两个评测

```http
GET /api/v1/evaluation/compare?eval_a={uuid}&eval_b={uuid}&similarity_mode=lexical&include_per_query=false
```

**响应示例**：

```json
{
  "evaluation_a": {
    "id": "uuid",
    "version_id": "v1.0",
    "name": "RAG System v1.0 Evaluation"
  },
  "evaluation_b": {
    "id": "uuid",
    "version_id": "v2.0",
    "name": "RAG System v2.0 Evaluation"
  },
  "metrics_delta": {
    "topK_chunk_query_similarity": {
      "avg_a": 0.78,
      "avg_b": 0.85,
      "delta": 0.07,
      "percent_change": 8.97,
      "p50_a": 0.80,
      "p50_b": 0.87,
      "p95_a": 0.92,
      "p95_b": 0.96
    },
    "semantic_recall_vs_gold": {
      "avg_a": 0.85,
      "avg_b": 0.90,
      "delta": 0.05,
      "percent_change": 5.88
    }
  },
  "per_query_comparison": null
}
```

---

## SDK 使用

### 完整示例

详细示例代码请参考：
- [`examples/evaluation_example.py`](../examples/evaluation_example.py) - 完整工作流
- [`examples/evaluation_comparison_example.py`](../examples/evaluation_comparison_example.py) - 版本对比分析

### 快速开始

```python
from uuid import UUID
from sdk.evaluation_client import EvaluationClient

eval_client = EvaluationClient(base_url="http://localhost:8000")

# 1. 创建测试集
test_suite = eval_client.create_test_suite(
    name="RAG Test",
    description="100个测试问题"
)

# 2. 上传测试用例
test_cases = [...]
eval_client.upload_test_cases(UUID(test_suite["id"]), test_cases)

# 3. 创建评测任务
evaluation = eval_client.create_evaluation(
    name="v1.0 Evaluation",
    test_suite_id=UUID(test_suite["id"]),
    version_id="v1.0"
)

# 4. 运行评测
# ... (调用你的 RAG 系统)

# 5. 获取指标
metrics = eval_client.get_evaluation_metrics(UUID(evaluation["id"]))

# 6. 版本对比
comparison = eval_client.compare_evaluations(eval_a_id, eval_b_id)
```

---

## 聚合指标解读

### 聚合统计量

每个指标提供 5 个统计量：

- **avg**：平均值，反映整体水平
- **p50**（中位数）：更鲁棒的中心趋势，抗异常值干扰
- **p95**：95% 的 runs 都在此值以下，反映尾部性能
- **min / max**：极值，用于发现异常

**建议关注顺序**：avg > p50 > p95 > max

### 支持的指标

所有单 run 指标都会被聚合：

| 指标 | 含义 | 范围 | 理想值 |
|------|------|------|--------|
| `topK_chunk_query_similarity` | 检索质量 | [0, 1] | ≥ 0.7 |
| `prompt_chunk_answer_similarity` | 答案支撑程度 | [0, 1] | ≥ 0.8 |
| `semantic_recall_vs_gold` | 召回率（需 gold data） | [0, 1] | ≥ 0.8 |
| `new_chunks_ratio` | 新增 chunk 比例（版本对比） | [0, 1] | - |
| `dropped_chunks_ratio` | 丢失 chunk 比例（版本对比） | [0, 1] | < 0.1 |

---

## 版本对比最佳实践

### 场景 1：评估 Embedding 模型切换

**问题**：想从 `text-embedding-ada-002` 切换到 `text-embedding-3-large`，不确定效果。

**方案**：

1. 创建测试集（100个典型问题）
2. v1.0：使用 `text-embedding-ada-002` 运行评测
3. v2.0：使用 `text-embedding-3-large` 运行评测
4. 对比 `topK_chunk_query_similarity` 和 `semantic_recall_vs_gold`

**期望结果**：v2.0 的检索质量和召回率都有提升

**示例**：

```python
comparison = eval_client.compare_evaluations(eval_a_id, eval_b_id)

retrieval_delta = comparison["metrics_delta"]["topK_chunk_query_similarity"]
if retrieval_delta["delta"] > 0.05:
    print("✅ 显著改善：检索质量提升明显")
```

### 场景 2：调优检索参数（top_k, chunk_size）

**问题**：不确定 `top_k=5` 还是 `top_k=10` 更好。

**方案**：

1. 使用同一测试集
2. eval_A：使用 `top_k=5`
3. eval_B：使用 `top_k=10`
4. 对比检索质量和答案支撑度

**分析维度**：

- **检索质量**：`topK_chunk_query_similarity` 是否提升？
- **答案支撑度**：`prompt_chunk_answer_similarity` 是否提升？
- **效率成本**：更多 chunks 是否带来实质提升？

**示例**：

```python
comparison = eval_client.compare_evaluations(
    eval_a_id,  # top_k=5
    eval_b_id,  # top_k=10
    include_per_query=True
)

# 检索质量分析
retrieval = comparison["metrics_delta"]["topK_chunk_query_similarity"]
print(f"检索质量: {retrieval['avg_a']:.2f} → {retrieval['avg_b']:.2f} ({retrieval['percent_change']:.1f}%)")

# 答案支撑分析
answer_support = comparison["metrics_delta"]["prompt_chunk_answer_similarity"]
print(f"答案支撑: {answer_support['avg_a']:.2f} → {answer_support['avg_b']:.2f}")

# 决策
if retrieval["delta"] > 0.03 and answer_support["delta"] > 0.02:
    print("✅ 推荐 top_k=10：检索质量和答案支撑都提升")
elif retrieval["delta"] < 0.01:
    print("⚠️ 保持 top_k=5：增加 chunks 没有明显提升")
```

### 场景 3：Chunk Size 优化

**问题**：不确定 `chunk_size=512` 还是 `chunk_size=1024` 更好。

**方案**：

1. 创建多个评测任务，分别使用不同 chunk_size
2. 对比检索质量和答案支撑度

**示例**：

```python
# chunk_size=512
eval_512 = eval_client.create_evaluation(
    name="chunk_size=512",
    test_suite_id=suite_id,
    version_id="v1_cs512",
    metadata={"chunk_size": 512}
)

# chunk_size=1024
eval_1024 = eval_client.create_evaluation(
    name="chunk_size=1024",
    test_suite_id=suite_id,
    version_id="v1_cs1024",
    metadata={"chunk_size": 1024}
)

# 对比
comparison = eval_client.compare_evaluations(eval_512["id"], eval_1024["id"])
```

### 最佳实践总结

1. **单变量实验**：每次只改一个配置（如只改 embedding 模型），便于归因
2. **A/B 测试**：在生产环境前，用评测系统验证改进效果
3. **持续监控**：每次发布新版本后运行评测，防止回归
4. **关注 p95**：识别长尾问题和边缘情况
5. **per-query 分析**：对于关键指标下降，查看 per-query 详情找出原因

---

## 常见问题

### 1. 我还没有集成 TraceLens 上报接口，可以直接使用批量评测吗？

**不可以**。批量评测依赖于 RAG 系统在运行时上报事件数据（检索结果、prompt、答案等）。你需要：

1. 先在 RAG 系统中集成 TraceLens SDK 或 API（参见"前置条件"章节）
2. 确保 RAG 系统能够上报 `retrieval_completed`, `prompt_built`, `answer_generated` 等事件
3. 在单个 run 上验证数据上报正常
4. 然后再进行批量评测

详细集成步骤请参考：
- [RAG_METRICS.md - 数据上报](RAG_METRICS.md#二数据上报)
- [QUICKSTART.md - SDK 使用](QUICKSTART.md#场景-1-单-run-分析)

### 2. 如何处理没有 gold 数据的场景？

**可以**。TraceLens 支持 gold-optional 评测。

**不需要 gold 数据的指标**（gold-optional）：
- `topK_chunk_query_similarity`（基于 query-chunk 相似度）
- `prompt_chunk_answer_similarity`（基于 prompt-answer 相似度）
- 版本对比指标（`new_chunks_ratio`, `dropped_chunks_ratio`）

**需要 gold 数据的指标**（gold-aware）：
- `semantic_recall_vs_gold`（需要 `gold_chunk_ids`）

**建议**：
- 初期没有 gold 数据时，关注 `topK_chunk_query_similarity`
- 后期有能力标注 gold 数据时，再关注 `semantic_recall_vs_gold`

### 3. 评测运行很慢怎么办？

**建议**：
- 使用 `similarity_mode="lexical"`（最快，基于关键词匹配）
- 不要每次都计算 per-query 详情（`include_per_query=False`）
- 考虑并行运行多个 run（TraceLens 支持并发）
- 如果使用 `similarity_mode="embedding"` 或 `"llm"`，会更慢但更准确

### 4. 如何对比不同测试集的评测？

**不建议**。不同测试集的评测无法直接对比（问题不同）。

**建议**：
- 使用同一个 TestSuite，在不同版本间对比
- 如果需要扩展测试集，创建新的 TestSuite 和新的基线评测
- 或者创建一个"核心测试集"用于持续对比，另一个"扩展测试集"用于全面覆盖

### 5. 评测指标与实际用户体验不符？

**自动化指标无法完全替代人工评估**。

**建议**：
- 结合用户反馈和人工标注
- 调整相似度计算模式：
  - `lexical`：快速，基于关键词
  - `embedding`：中等，基于语义向量
  - `llm`：慢但准确，基于 LLM 判断
- 设计更贴近业务的 gold 数据
- 在关键问题上进行人工复核

### 6. 批量评测会自动加载 gold_chunk_ids 吗？

**会**。

当你调用 `start_run` 并提供 `test_case_id` 时：
1. TraceLens 会自动从 `TestCase` 中读取 `gold_chunk_ids`
2. 创建 `GoldChunk` 记录
3. 计算指标时会自动使用

**无需手动传递 gold_chunk_ids**。

### 7. 可以在同一个 TestSuite 上运行多次评测吗？

**可以**。

一个 TestSuite 可以关联多个 Evaluation，每个 Evaluation 对应一个版本或配置。

**示例**：
```python
# 同一个 test_suite，多次评测
eval_v1 = eval_client.create_evaluation(suite_id, version_id="v1.0")
eval_v2 = eval_client.create_evaluation(suite_id, version_id="v2.0")
eval_v3 = eval_client.create_evaluation(suite_id, version_id="v3.0")
```

### 8. per_query_metrics 包含什么？

当 `include_per_query=True` 时，返回每个测试用例的详细指标。

**用途**：
- 识别哪些问题改进显著
- 识别哪些问题仍需优化
- 深入分析特定问题的检索结果

**示例**：
```python
metrics = eval_client.get_evaluation_metrics(
    evaluation_id,
    include_per_query=True
)

for item in metrics["per_query_metrics"]:
    print(f"Query: {item['query']}")
    print(f"  topK_chunk_query_similarity: {item['metrics']['topK_chunk_query_similarity']:.2f}")
```

### 9. 评测任务可以暂停和恢复吗？

**可以**。

评测任务只是一个逻辑分组，实际的执行是逐个 run 完成的。

你可以：
- 先运行部分 test_cases
- 随时停止
- 稍后继续运行剩余的 test_cases
- 调用 `get_evaluation_status` 查看进度

---

## 总结

RAG 批量评测系统的核心价值：

> **让 RAG 的检索质量和召回率从"凭感觉"变成"有数据支撑"的系统化评估。**

**三个关键能力**：
1. 🎯 **聚合指标**：系统化评估检索质量（topK_chunk_query_similarity）和召回率（semantic_recall_vs_gold）
2. 📊 **版本对比**：量化 embedding 模型、检索参数优化的效果
3. 🔍 **Per-Query 分析**：识别哪些问题改进显著、哪些仍需优化

**适用场景**：
- Embedding 模型切换评估
- 检索参数调优（top_k, chunk_size）
- 版本回归测试
- A/B 测试验证

---

**相关文档**：
- [`RAG_METRICS.md`](RAG_METRICS.md) - RAG 单次指标计算详解
- [`GRAPH_EVALUATION_GUIDE.md`](GRAPH_EVALUATION_GUIDE.md) - GraphRAG 批量评测指南
- [`SIMILARITY_ENGINE.md`](SIMILARITY_ENGINE.md) - 相似度计算模式详解
- [`examples/evaluation_example.py`](../examples/evaluation_example.py) - 完整示例代码
