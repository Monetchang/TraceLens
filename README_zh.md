<div align="center">

# TraceLens

**RAG 可解释性、调试与批量评测后端**

</div>

<p align="center">
  <a href="./README.md"><img alt="English" src="https://img.shields.io/badge/English-DBEDFA"></a>
  <a href="./README_zh.md"><img alt="简体中文" src="https://img.shields.io/badge/简体中文-DFE0E5"></a>
</p>

<p align="center">
  <a href="https://github.com"><img src="https://img.shields.io/badge/License-MIT-ffffff?labelColor=d4eaf7&color=2e6cc4" alt="license"></a>
</p>

<h4 align="center">
  <a href="#-tracelens-是什么">简介</a> |
  <a href="#-核心功能">功能</a> |
  <a href="#-快速开始">快速开始</a> |
  <a href="#-文档">文档</a>
</h4>

<details open>
<summary><b>📕 目录</b></summary>

- [🔥 最近更新](#-最近更新)
- [💡 TraceLens 是什么？](#-tracelens-是什么)
- [🌟 核心功能](#-核心功能)
- [🎬 快速开始](#-快速开始)
- [🔧 配置说明](#-配置说明)
- [📚 文档](#-文档)
- [🙌 贡献](#-贡献)

</details>

## 🔥 最近更新

- **2026-03-07** 指标优化：`exact_recall_vs_gold_chunks`（原 semantic_recall，chunk_id 精确命中）；evaluation 聚合按 `similarity_mode` 过滤；`rank_deltas` 落库 `value_json`；chunks 批量 upsert；embedding/LLM provider 长连接复用
- **2026-03-06** 写接口 API Key 鉴权；可选 `X-API-Key` 请求头
- **2026-03-06** Alembic 迁移；启动时执行 `alembic upgrade head` 替代 `create_all`
- **2026-03-06** Ingest 接口 Schema 校验；Pydantic 负载，深度 20、大小 1MB 限制
- **2026-03-06** SDK：长连接 `httpx.Client`、显式 timeout/limits、API Key 支持
- **2026-03-06** 结构化日志与 `request_id` 中间件；`print` 替换为 `logger`
- **2026-03-06** Metrics 幂等写入；`(run_id, name, similarity_mode)` 唯一约束
- **2026-03-06** 相似度引擎缓存：SHA256 key、LRU maxsize=512
- **2026-03-06** Embedding/LLM provider 通过 `EMBEDDING_ENDPOINT`、`LLM_ENDPOINT` 环境变量配置
- **2026-03-06** 异步评测：`POST /evaluation/{id}/compute` 后台计算指标

## 💡 TraceLens 是什么？

[TraceLens](.) 是面向 **RAG（检索增强生成）** 和 **GraphRAG** 系统的开源后端平台，提供：

- **单 run 可解释性**：chunk 归因、检索质量指标、prompt-answer 对齐
- **批量评测**：TestSuite/TestCase 管理、聚合指标（avg/p50/p95）、版本对比
- **GraphRAG 评估**：推理路径质量、连通性、分支爆炸比
- **可插拔相似度引擎**：Lexical、Embedding 或 LLM Judge

## 🌟 核心功能

### 🍭 单 Run 分析

- Chunk 归因：哪些 chunk 被检索、用于 prompt、支撑答案
- 检索质量：query-chunk 相似度、prompt-answer 对齐度
- Gold-aware 指标：与标准答案/chunk 对比（可选）

### 🍱 批量评测系统

- **TestSuite 管理**：创建可复用测试集
- **自动化评测**：一键运行多个测试用例
- **聚合指标**：avg、p50、p95、min、max
- **版本对比**：量化不同版本的改进效果
- **Gold 数据支持**：可选的 gold answer / gold chunks / gold docs

### 🌱 GraphRAG 评估

- 推理路径质量评估
- 图结构分析（连通性、分支爆炸比）
- 路径相关性评分（可选 LLM Judge）

### 🍔 灵活相似度模式

- **Lexical**：快速、基于关键词（零配置）
- **Embedding**：语义相似度（通过 `EMBEDDING_ENDPOINT` 配置）
- **LLM Judge**：主观评分（通过 `LLM_ENDPOINT` 配置）

## 🎬 快速开始

### 📝 前置要求

- Python >= 3.10
- PostgreSQL >= 12
- （可选）外部 embedding/LLM API，用于非 lexical 相似度模式

### 🚀 启动步骤

1. 克隆仓库：

   ```bash
   git clone https://github.com/your-org/tracelens.git
   cd tracelens
   ```

2. 安装依赖：

   ```bash
   pip install -r requirements.txt
   ```

3. 创建数据库：

   ```bash
   createdb tracelens
   ```

4. 配置环境变量（复制 `.env.example` 为 `.env`）：

   ```bash
   cp .env.example .env
   # 编辑 .env：设置 DATABASE_URL，可选 API_KEY
   ```

5. 启动服务：

   ```bash
   uvicorn tracelens.main:app --reload
   ```

6. 验证：`curl http://localhost:8000/health` → `{"status":"ok"}`

### 📌 使用示例

**单 Run（SDK）：**

```python
from sdk.rag_client import RAGClient

client = RAGClient("http://localhost:8000", api_key="your-key")  # api_key 可选
run = client.start_run(name="single_query_test")
client.retrieval_completed(run.id, query="什么是 RAG？", retrieved_chunks=[
    {"chunk_id": "chunk_1", "content": "...", "score": 0.95}
])
client.prompt_built(run.id, ["chunk_1", "chunk_2"])
client.answer_generated(run.id, "RAG 是...")
client.run_finished(run.id)
metrics = client.get_metrics(run.id, similarity_mode="lexical")
```

**批量评测：**

```python
from sdk.evaluation_client import EvaluationClient
from sdk.rag_client import RAGClient

eval_client = EvaluationClient("http://localhost:8000")
rag_client = RAGClient("http://localhost:8000")

test_suite = eval_client.create_test_suite(name="RAG 测试集", description="100 个测试问题")
eval_client.upload_test_cases(test_suite["id"], [
    {"query": "什么是 RAG？", "gold_answer": "...", "gold_chunk_ids": ["chunk_1"]},
])
evaluation = eval_client.create_evaluation(
    name="v1.0", test_suite_id=test_suite["id"], version_id="v1.0"
)
# 运行你的 RAG 系统遍历测试用例，然后：
metrics = eval_client.get_evaluation_metrics(evaluation["id"])
comparison = eval_client.compare_evaluations(eval_v1_id, eval_v2_id)
```

## 🔧 配置说明

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATABASE_URL` | PostgreSQL 连接串 | `postgresql://postgres:postgres@localhost:5432/tracelens` |
| `API_KEY` | 写接口 API Key（空则无需鉴权） | `""` |
| `EMBEDDING_ENDPOINT` | Embedding HTTP 端点（OpenAI 兼容） | `""` |
| `EMBEDDING_API_KEY` | Embedding 服务 API Key | `""` |
| `LLM_ENDPOINT` | LLM HTTP 端点（OpenAI chat completions） | `""` |
| `LLM_API_KEY` | LLM 服务 API Key | `""` |

设置 `API_KEY` 后，所有写接口需携带 `X-API-Key` 请求头。`/health` 始终公开。

## 📚 文档

- [快速开始](docs/QUICKSTART.md)
- [RAG 批量评测指南](docs/RAG_EVALUATION_GUIDE.md)
- [GraphRAG 批量评测指南](docs/GRAPH_EVALUATION_GUIDE.md)
- [RAG 指标说明](docs/RAG_METRICS.md)
- [GraphRAG 指标说明](docs/GRAPHRAG_METRICS.md)
- [相似度引擎](docs/SIMILARITY_ENGINE.md)

### 示例代码

- [RAG 批量评测](examples/evaluation_example.py)
- [RAG 版本对比](examples/evaluation_comparison_example.py)
- [GraphRAG 批量评测](examples/graph_evaluation_example.py)
- [单次运行（SDK）](examples/rag_sdk_example.py)
- [相似度模式](examples/similarity_modes_example.py)

## 🙌 贡献

欢迎提交 Issue 和 Pull Request。

## 许可证

MIT
