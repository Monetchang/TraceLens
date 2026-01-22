# TraceLens 文档

欢迎使用 TraceLens！本目录包含所有详细文档。

## 📚 文档导航

### 🚀 快速入门

- **[快速开始 (QUICKSTART.md)](QUICKSTART.md)**
  - 安装和配置
  - 第一个单次运行示例
  - SDK 和 API 使用方式
  - 适合新手快速上手

---

## 📊 批量评测指南

### RAG 批量评测
- **[RAG 批量评测指南 (RAG_EVALUATION_GUIDE.md)](RAG_EVALUATION_GUIDE.md)**
  - 完整的 RAG 批量评测工作流
  - TestSuite 和 Evaluation 管理
  - 聚合指标解读（avg / p50 / p95）
  - 版本对比最佳实践
  - 适用场景：
    - Embedding 模型切换评估
    - 检索参数调优（top_k, chunk_size）
    - 版本回归测试

### GraphRAG 批量评测
- **[GraphRAG 批量评测指南 (GRAPH_EVALUATION_GUIDE.md)](GRAPH_EVALUATION_GUIDE.md)**
  - 完整的 GraphRAG 批量评测工作流
  - Gold Path 和 Gold Nodes 设计
  - 推理路径质量指标解读
  - 版本对比最佳实践
  - 适用场景：
    - 剪枝策略优化验证
    - 搜索算法选型（BFS vs Beam Search）
    - max_hops / beam_size 参数调优

---

## 📈 指标说明

### RAG 指标
- **[RAG 指标说明 (RAG_METRICS.md)](RAG_METRICS.md)**
  - 单次运行指标详解
  - 检索质量评估
  - Prompt-Answer 对齐度
  - Gold-aware 指标（需要 gold 数据）
  - Gold-optional 指标（无需 gold 数据）
  - 核心指标：
    - `topK_chunk_query_similarity` - 检索质量
    - `prompt_chunk_answer_similarity` - 答案支撑度
    - `semantic_recall_vs_gold` - 召回率

### GraphRAG 指标
- **[GraphRAG 指标说明 (GRAPHRAG_METRICS.md)](GRAPHRAG_METRICS.md)**
  - 单次运行指标详解
  - 推理路径质量评估
  - 图结构分析
  - 三层指标体系：
    - **结构性指标**：path_exists, reasoning_hops, connectivity_score
    - **质量指标**：branch_explosion_ratio, path_coverage
    - **语义指标**：path_relevance_score（LLM Judge）

---

## 🎨 高级功能

### 相似度引擎
- **[相似度引擎 (SIMILARITY_ENGINE.md)](SIMILARITY_ENGINE.md)**
  - 三种相似度计算模式
  - **Lexical**（快速，基于关键词）
    - TF-IDF / 关键词重叠
    - 适合快速评测
  - **Embedding**（准确，基于语义）
    - 使用 embedding 模型计算 cosine 相似度
    - 适合语义匹配场景
  - **LLM Judge**（主观，基于 LLM 判断）
    - 使用 LLM 评分
    - 适合复杂推理场景
  - 如何选择合适的相似度模式

---

## 📖 阅读建议

### 新手路径
1. 先阅读 [快速开始](QUICKSTART.md) 了解基础概念
2. 再阅读 [RAG 指标说明](RAG_METRICS.md) 了解单次指标
3. 最后阅读 [RAG 批量评测指南](RAG_EVALUATION_GUIDE.md) 学习批量评测

### RAG 开发者
1. [RAG 指标说明](RAG_METRICS.md) - 了解可用指标
2. [RAG 批量评测指南](RAG_EVALUATION_GUIDE.md) - 系统化评测流程
3. [相似度引擎](SIMILARITY_ENGINE.md) - 选择合适的相似度模式

### GraphRAG 开发者
1. [GraphRAG 指标说明](GRAPHRAG_METRICS.md) - 了解推理路径指标
2. [GraphRAG 批量评测指南](GRAPH_EVALUATION_GUIDE.md) - 系统化评测流程
3. [相似度引擎](SIMILARITY_ENGINE.md) - 语义相关性评估

### 版本对比场景
1. [RAG 批量评测指南](RAG_EVALUATION_GUIDE.md) 的"版本对比最佳实践"章节
2. [GraphRAG 批量评测指南](GRAPH_EVALUATION_GUIDE.md) 的"版本对比最佳实践"章节

---

## 🔗 相关资源

- [示例代码](../examples/) - 各类使用示例
- [主页 README](../README.md) - 项目概述和快速开始
- [SDK 代码](../sdk/) - Python SDK 源码

---

## 💡 快速查找

### 我想...

- **开始使用 TraceLens** → [快速开始](QUICKSTART.md)
- **了解 RAG 指标含义** → [RAG 指标说明](RAG_METRICS.md)
- **批量评测 RAG 系统** → [RAG 批量评测指南](RAG_EVALUATION_GUIDE.md)
- **评估 GraphRAG 推理路径** → [GraphRAG 指标说明](GRAPHRAG_METRICS.md)
- **对比不同版本的 GraphRAG** → [GraphRAG 批量评测指南](GRAPH_EVALUATION_GUIDE.md)
- **选择相似度计算模式** → [相似度引擎](SIMILARITY_ENGINE.md)
- **运行示例代码** → [示例代码目录](../examples/)

---

## 📮 反馈

如有疑问或建议，请提交 Issue 或 Pull Request！

