# TraceLens RAG MVP 实现总结（最终版）

## 已完成功能

### 1. 数据库表结构

- ✅ `run`: 存储 run 基本信息（包含 query 和 **answer** 字段，version_id）
- ✅ `retrieved_chunk`: 存储检索到的 chunks
- ✅ `prompt_chunk`: 存储 prompt 中使用的 chunks（**移除了 used_in_answer 字段**）
- ✅ `gold_chunk`: 存储 gold chunks（可选）
- ✅ `metric`: 存储计算的指标

### 2. SDK 上报接口

- ✅ `retrieval_completed`: 上报检索结果
- ✅ `prompt_built`: 上报 prompt chunks
- ✅ `answer_generated`: 上报 answer 文本（**新增**）
- ✅ `gold_chunks`: 上报 gold chunks（可选）
- ✅ `run_finished`: 结束 run
- ❌ ~~`chunk_used`~~: 已移除（价值低）

### 3. 基础指标（版本对比）

- ✅ `new_chunks_ratio`: 新增 chunks 比例
- ✅ `rank_deltas`: 排名变化
- ❌ ~~`unused_chunks_count`~~: 已移除（依赖 chunk_used，价值低）
- ❌ ~~`dropped_chunks_ratio`~~: 已移除（可由 new_chunks_ratio 推导）

### 4. 扩展指标（需要 embedding）

- ✅ `topK_chunk_query_similarity`: Top-K chunks 与 query 的相似度
- ✅ `prompt_chunk_answer_similarity`: prompt chunks 与 answer 的相似度（**新增**）
- ✅ `semantic_recall_vs_gold`: 相对于 gold chunks 的召回率（简化版本）
- ✅ `new_chunks_query_similarity`: 新增 chunks 与 query 的相似度（**新增**）
- ✅ `dropped_chunks_query_similarity`: 丢弃 chunks 与 query 的相似度（**新增**）

### 5. 查询接口

- ✅ `GET /api/v1/run/{run_id}/metrics`: 获取指标（支持 prev_run_id 和 include_extended 参数）
- ✅ `GET /api/v1/run/{run_id}/retrieval_diff`: 获取版本对比（支持 include_extended 参数）
- ❌ ~~`GET /api/v1/run/{run_id}/topK_similarity`~~: 已整合到 metrics 接口

### 6. Python SDK

- ✅ `TraceLensClient`: 基础客户端
- ✅ `RAGClient`: RAG 专用客户端

### 7. 示例代码

- ✅ `rag_api_example.py`: API 接口接入示例
- ✅ `rag_sdk_example.py`: SDK 接入示例
- ✅ `rag_version_diff_example.py`: 版本对比示例

### 8. 文档

- ✅ `RAG_METRICS.md`: 详细的指标文档（已重写）
- ✅ `QUICKSTART.md`: 快速开始文档（已更新）

## 技术栈

- **Backend**: FastAPI
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **SDK**: Python
- **Similarity Engine**: 三层可插拔架构
  - Lexical（默认，零配置）
  - Embedding（可配置）
  - LLM（可配置）
- **GraphRAG Support**: 推理路径评测
  - 结构性指标（免费）
  - 路径质量指标（免费）
  - 语义合理性指标（可选）

## 核心设计原则

1. **去除冗余指标**: 移除 `unused_chunks_count`（依赖 chunk_used，价值低）
2. **增加 answer 相关性**: 新增 `prompt_chunk_answer_similarity`（衡量 chunks 对 answer 的贡献）
3. **版本对比质量评估**: 新增 `new_chunks_query_similarity` 和 `dropped_chunks_query_similarity`（评估版本变化质量）
4. **简化接口**: 整合 topK_similarity 到 metrics 接口
5. **可选 gold data**: 不强制要求 gold chunks
6. **三层相似度计算**: Lexical（默认）→ Embedding（可选）→ LLM（高精度）

## 指标体系对比

### 旧版本
- total_retrieved_chunks（无指导价值）
- unused_chunks_count（依赖 chunk_used，价值低）
- topK_chunk_query_similarity
- semantic_recall_vs_gold
- new_chunks_ratio
- dropped_chunks_ratio
- rank_deltas

### 新版本（最终版）
- **基础指标**:
  - new_chunks_ratio（版本对比）
  - rank_deltas（版本对比）
- **扩展指标**（需要 embedding）:
  - topK_chunk_query_similarity（检索质量）
  - **prompt_chunk_answer_similarity**（chunk 对 answer 的贡献，新增）
  - semantic_recall_vs_gold（召回质量，可选）
  - **new_chunks_query_similarity**（新增 chunks 质量，新增）
  - **dropped_chunks_query_similarity**（丢弃 chunks 质量，新增）

## 指标计算流程

```
1. 创建 run (version_id)
   ↓
2. 上报 retrieval_completed (query, retrieved_chunks)
   ↓
3. 上报 prompt_built (prompt_chunks)
   ↓
4. 上报 answer_generated (answer)  ← 新增
   ↓
5. 上报 gold_chunks (可选)
   ↓
6. 结束 run
   ↓
7. 查询指标
   - 基础指标: new_chunks_ratio, rank_deltas
   - 扩展指标: topK_chunk_query_similarity, prompt_chunk_answer_similarity,
               semantic_recall_vs_gold, new_chunks_query_similarity, dropped_chunks_query_similarity
```

## 使用场景

### 场景 1: 基础检索监控

```python
# 只需要上报 retrieval_completed, prompt_built, answer_generated
rag_client.retrieval_completed(run_id, query, chunks)
rag_client.prompt_built(run_id, prompt_chunks)
rag_client.answer_generated(run_id, answer)
rag_client.run_finished(run_id)

# 查询基础指标（无需 embedding）
metrics = rag_client.get_metrics(run_id)
```

### 场景 2: 版本对比

```python
# 运行两个版本
run_v1 = run_rag_query(version="v1.0")
run_v2 = run_rag_query(version="v2.0")

# 对比（基础指标，无需 embedding）
diff = rag_client.get_retrieval_diff(run_v2, run_v1)
print(f"new_chunks_ratio: {diff['new_chunks_ratio']}")
print(f"rank_deltas: {diff['rank_deltas']}")
```

### 场景 3: 不同相似度模式

```python
# Lexical 模式（默认，零配置）
metrics_lex = rag_client.get_metrics(run_id, similarity_mode="lexical")

# Embedding 模式（需要配置 embedding function）
from tracelens.similarity import get_similarity_engine
engine = get_similarity_engine("embedding", {"embedding_function": my_embed_fn})
metrics_emb = rag_client.get_metrics(run_id, similarity_mode="embedding")

# LLM 模式（需要配置 LLM client）
engine = get_similarity_engine("llm", {"llm_client": my_llm_client})
metrics_llm = rag_client.get_metrics(run_id, similarity_mode="llm")

# 版本对比 + 扩展指标
diff = rag_client.get_retrieval_diff(run_v2, run_v1, similarity_mode="lexical")
print(f"new_chunks_query_similarity: {diff['new_chunks_query_similarity']}")
print(f"dropped_chunks_query_similarity: {diff['dropped_chunks_query_similarity']}")
```

## 核心改进点

### 1. 移除低价值指标
- ❌ `total_retrieved_chunks`: 只是数量统计，无指导价值
- ❌ `unused_chunks_count`: 依赖 chunk_used 事件，实际使用中很少标记，指标失去意义
- ❌ `dropped_chunks_ratio`: 可由 `new_chunks_ratio` 推导，冗余

### 2. 新增高价值指标
- ✅ `prompt_chunk_answer_similarity`: 衡量 chunks 对 answer 的实际贡献，替代 `unused_chunks_count`
- ✅ `new_chunks_query_similarity`: 评估新增 chunks 与 query 的相关度，判断版本升级质量
- ✅ `dropped_chunks_query_similarity`: 评估丢弃 chunks 与 query 的相关度，发现版本退化

### 3. 简化数据模型
- 移除 `prompt_chunk.used_in_answer` 字段
- 移除 `chunk_used` API 接口
- 新增 `run.answer` 字段
- 新增 `answer_generated` API 接口

### 4. 简化 API 接口
- 整合 `topK_similarity` 到 `metrics` 接口
- `retrieval_diff` 接口支持 `include_extended` 参数

## 文件结构

```
TraceLens/
├── tracelens/
│   ├── api/
│   │   ├── rag_routes.py          # RAG API 路由
│   │   ├── rag_schemas.py         # RAG API schemas
│   │   ├── graph_routes.py        # GraphRAG API 路由（新增）
│   │   └── graph_schemas.py       # GraphRAG API schemas（新增）
│   ├── core/
│   │   ├── rag_metrics_simple.py  # RAG 基础指标
│   │   ├── rag_metrics_extended.py # RAG 扩展指标
│   │   ├── graph_metrics.py       # GraphRAG 指标（新增）
│   │   └── embedding_utils.py     # Embedding 工具
│   ├── similarity/                # 相似度引擎模块
│   │   ├── __init__.py
│   │   ├── base.py                # 抽象基类
│   │   ├── lexical.py             # Lexical 相似度（默认）
│   │   ├── embedding.py           # Embedding 相似度
│   │   ├── llm_judge.py           # LLM 相似度
│   │   └── factory.py             # 工厂方法
│   ├── storage/
│   │   ├── models.py              # 核心数据模型
│   │   ├── rag_models.py          # RAG 数据模型
│   │   ├── rag_repository.py      # RAG 数据访问
│   │   ├── graph_models.py        # GraphRAG 数据模型（新增）
│   │   └── graph_repository.py    # GraphRAG 数据访问（新增）
│   └── main.py                    # FastAPI 应用
├── sdk/
│   ├── client.py                  # 基础客户端
│   ├── rag_client.py              # RAG 客户端
│   └── graph_client.py            # GraphRAG 客户端（新增）
├── examples/
│   ├── rag_api_example.py         # RAG API 示例
│   ├── rag_sdk_example.py         # RAG SDK 示例
│   ├── rag_version_diff_example.py # RAG 版本对比示例
│   ├── similarity_modes_example.py # 相似度模式示例
│   ├── graphrag_example.py        # GraphRAG 示例（新增）
│   └── graphrag_comparison_example.py # GraphRAG 版本对比（新增）
├── RAG_METRICS.md                 # RAG 指标文档
├── GRAPHRAG_METRICS.md            # GraphRAG 指标文档（新增）
├── SIMILARITY_ENGINE.md           # 相似度引擎文档
├── QUICKSTART.md                  # 快速开始
└── requirements.txt               # 依赖
```

## 开发清单（已完成）

- [x] 数据库表设计（添加 answer 字段，移除 used_in_answer 字段）
- [x] SDK 上报接口（添加 answer_generated，移除 chunk_used）
- [x] 基础指标计算（移除 unused_chunks_count）
- [x] 扩展指标计算（新增 prompt_chunk_answer_similarity, new_chunks_query_similarity, dropped_chunks_query_similarity）
- [x] **三层相似度引擎**（新增）
  - [x] Lexical 相似度（默认，零配置）
  - [x] Embedding 相似度（可配置）
  - [x] LLM 相似度（可配置）
- [x] 查询接口（简化，整合 topK_similarity，支持 similarity_mode）
- [x] Python SDK（更新，支持 similarity_mode）
- [x] 示例代码（更新）
- [x] 文档（重写）

## 总结

TraceLens RAG MVP 最终版是一个**轻量级、专注于检索分析和版本对比的 RAG 评测平台**。

核心价值：
- ✅ **检索质量评估**：topK_chunk_query_similarity, prompt_chunk_answer_similarity
- ✅ **版本对比分析**：rank_delta, new_chunks_ratio, new/dropped_chunks_query_similarity
- ✅ **可选 gold data**：不强制要求标准答案
- ✅ **易于集成**：SDK + API 双接入方式
- ✅ **去除冗余**：移除低价值指标，保留核心指标
- ✅ **三层相似度引擎**：Lexical（默认）→ Embedding（可选）→ LLM（高精度）

**专注于回答：当你更换切分、向量模型或向量数据库时，检索能力到底发生了什么变化？**

**核心设计哲学：让开发者在成本与精度之间，拥有连续、可对比、可解释的 RAG 评测能力。**
