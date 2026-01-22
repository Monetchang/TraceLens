# TraceLens

**RAG 可解释性、调试与批量评测系统**

TraceLens 是一个专为 RAG（Retrieval-Augmented Generation）系统设计的后端平台，提供：
- 单 run 可解释性分析（chunk 归因、检索质量评估）
- 批量评测与版本对比（系统化测试多个问题）
- GraphRAG 推理路径评估
- 多种相似度计算模式（Lexical / Embedding / LLM Judge）

## 核心功能

### 1. 单 Run 分析
- Chunk 归因分析：哪些 chunk 被检索、用于 prompt、支撑答案
- 检索质量评估：query-chunk 相似度、prompt-answer 对齐度
- Gold-aware 指标：与标准答案/chunk 对比（可选）

### 2. 批量评测系统 ⭐ NEW
- **TestSuite 管理**：创建可复用的测试集
- **自动化评测**：一键运行多个测试用例
- **聚合指标**：avg / p50 / p95 统计维度
- **版本对比**：量化不同版本的改进效果
- **Gold 数据支持**：可选的 gold answer / gold chunks / gold docs

### 3. GraphRAG 评估
- 推理路径质量评估
- 图结构分析（连通性、分支爆炸比）
- 路径相关性评分

### 4. 灵活的相似度计算
- Lexical（快速，基于关键词）
- Embedding（准确，基于语义）
- LLM Judge（主观，基于 LLM 判断）

## 快速开始

### 安装

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动 PostgreSQL 并创建数据库
createdb tracelens

# 3. 设置环境变量（可选）
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/tracelens"

# 4. 启动服务
uvicorn tracelens.main:app --reload
```

### 使用方式

#### 方式 A: 单 Run 分析

```python
from sdk.rag_client import RAGClient

client = RAGClient("http://localhost:8000")

# 创建 run
run = client.start_run(name="single_query_test")

# 上报检索结果
client.retrieval_completed(run.id, retrieved_chunks=[
    {"chunk_id": "chunk_1", "content": "...", "score": 0.95}
])

# 上报 prompt chunks
client.prompt_built(run.id, ["chunk_1", "chunk_2"])

# 上报生成的答案
client.answer_generated(run.id, "RAG is...")

# 结束 run
client.run_finished(run.id)

# 获取指标
metrics = client.get_metrics(run.id, similarity_mode="lexical")
```

#### 方式 B: 批量评测（推荐）

```python
from sdk.evaluation_client import EvaluationClient
from sdk.rag_client import RAGClient

eval_client = EvaluationClient("http://localhost:8000")
rag_client = RAGClient("http://localhost:8000")

# 1. 创建测试集
test_suite = eval_client.create_test_suite(
    name="RAG Test Suite",
    description="100个标准测试问题"
)

# 2. 上传测试用例
eval_client.upload_test_cases(test_suite["id"], [
    {
        "query": "What is RAG?",
        "gold_answer": "...",
        "gold_chunk_ids": ["chunk_1", "chunk_2"]
    },
    # ... 更多测试用例
])

# 3. 创建评测任务
evaluation = eval_client.create_evaluation(
    name="v1.0 Evaluation",
    test_suite_id=test_suite["id"],
    version_id="v1.0"
)

# 4. 运行评测
test_cases = eval_client.get_evaluation_test_cases(evaluation["id"])
for tc in test_cases:
    run = rag_client.start_run(
        name=f"eval_{tc['id']}",
        evaluation_id=evaluation["id"],
        test_case_id=tc["id"]
    )
    # 运行你的 RAG 系统...
    # rag_client.retrieval_completed(...)
    # rag_client.prompt_built(...)
    # rag_client.answer_generated(...)
    rag_client.run_finished(run.id)

# 5. 获取聚合指标
metrics = eval_client.get_evaluation_metrics(evaluation["id"])
print(f"avg: {metrics['aggregate_metrics']['topK_chunk_query_similarity']['avg']}")

# 6. 版本对比（在运行 v2.0 后）
comparison = eval_client.compare_evaluations(eval_v1_id, eval_v2_id)
```

## 批量评测工作流

```mermaid
graph LR
    A[创建 TestSuite] --> B[上传 TestCase]
    B --> C[创建 Evaluation v1.0]
    C --> D[运行 RAG 系统]
    D --> E[获取聚合指标]
    E --> F[修改系统]
    F --> G[创建 Evaluation v2.0]
    G --> H[运行 RAG 系统]
    H --> I[对比 v1.0 vs v2.0]
```

## 核心 API

### 批量评测 API

```bash
# 创建测试集
POST /api/v1/test_suite

# 上传测试用例
POST /api/v1/test_suite/{id}/test_cases

# 创建评测任务
POST /api/v1/evaluation

# 获取测试用例（供 RAG 系统遍历）
GET /api/v1/evaluation/{id}/test_cases

# 获取聚合指标
GET /api/v1/evaluation/{id}/metrics?similarity_mode=lexical

# 版本对比
GET /api/v1/evaluation/compare?eval_a={id}&eval_b={id}
```

### 单 Run API

```bash
# 创建 run（支持评测参数）
POST /api/v1/run/start

# 上报检索结果
POST /api/v1/retrieval/completed

# 上报 prompt chunks
POST /api/v1/prompt/built

# 上报答案
POST /api/v1/answer/generated

# 上报 gold chunks（可选）
POST /api/v1/gold/chunks

# 结束 run
POST /api/v1/run/finished

# 获取单 run 指标
GET /api/v1/run/{id}/metrics

# 对比两个 run
GET /api/v1/run/{id}/retrieval_diff?prev_run_id={prev_id}
```

## 聚合指标

批量评测支持以下统计维度：
- **avg (均值)**: 所有 run 的平均值
- **p50 (中位数)**: 抗异常值干扰
- **p95 (95分位数)**: 识别边缘情况
- **min / max**: 最佳/最差表现

支持的指标包括：
- `topK_chunk_query_similarity`: 检索质量
- `prompt_chunk_answer_similarity`: 答案支撑程度
- `semantic_recall_vs_gold`: 召回率（需要 gold data）
- `new_chunks_ratio`: 版本间新增 chunk 比例
- `dropped_chunks_ratio`: 版本间丢失 chunk 比例

## 示例代码

### RAG 批量评测
- [`examples/evaluation_example.py`](examples/evaluation_example.py) - RAG 批量评测完整工作流
- [`examples/evaluation_comparison_example.py`](examples/evaluation_comparison_example.py) - RAG 版本对比分析

### GraphRAG 批量评测
- [`examples/graph_evaluation_example.py`](examples/graph_evaluation_example.py) - GraphRAG 批量评测完整工作流
- [`examples/graph_evaluation_comparison_example.py`](examples/graph_evaluation_comparison_example.py) - GraphRAG 版本对比分析

### 单次运行示例
- [`examples/rag_api_example.py`](examples/rag_api_example.py) - RAG 单次运行（API 方式）
- [`examples/rag_sdk_example.py`](examples/rag_sdk_example.py) - RAG 单次运行（SDK 方式）

### 其他示例
- [`examples/similarity_modes_example.py`](examples/similarity_modes_example.py) - 相似度计算模式示例

## 文档

### 快速入门
- [快速开始](docs/QUICKSTART.md) - 详细的入门教程

### 批量评测
- [RAG 批量评测指南](docs/RAG_EVALUATION_GUIDE.md) - RAG 批量评测完整指南
- [GraphRAG 批量评测指南](docs/GRAPH_EVALUATION_GUIDE.md) - GraphRAG 批量评测完整指南

### 指标说明
- [RAG 指标说明](docs/RAG_METRICS.md) - RAG 单次运行指标详解
- [GraphRAG 指标说明](docs/GRAPHRAG_METRICS.md) - GraphRAG 推理路径指标详解

### 高级功能
- [相似度引擎](docs/SIMILARITY_ENGINE.md) - 三种相似度计算模式（Lexical / Embedding / LLM Judge）

## 使用场景

### 1. RAG 系统迭代优化
- 切换 embedding 模型（ada-002 → text-embedding-3-large）
- 调整 chunk size（512 → 256）
- 优化 retrieval 策略（top-k、reranking）
- 通过批量评测量化改进效果

### 2. A/B 测试
- 在生产环境前，用标准测试集验证新版本
- 对比不同配置的表现
- 识别回归问题

### 3. 持续监控
- 每次发布后运行评测
- 监控关键指标趋势
- 及时发现性能下降

### 4. 调试与分析
- 单 run 分析找出问题 query
- per-query 对比定位版本间差异
- chunk 归因分析理解系统行为

## 架构特点

- **Gold-Optional**: 支持有/无 gold 数据的评测
- **可扩展**: 插件式相似度引擎
- **高效**: Lexical 模式快速计算
- **灵活**: 支持单 run 和批量两种模式
- **可追溯**: 所有数据和指标可追溯到源

## 许可证

MIT

## 贡献

欢迎提交 Issue 和 Pull Request！
