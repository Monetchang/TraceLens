# TraceLens 示例代码

本目录包含 TraceLens 的各类示例代码，帮助你快速上手不同的使用场景。

## 📊 RAG 批量评测

### 完整工作流
- [`evaluation_example.py`](evaluation_example.py) - RAG 批量评测完整示例
  - 创建测试集和测试用例
  - 运行批量评测
  - 获取聚合指标
  - 适用场景：评估 RAG 系统在多个测试问题上的表现

### 版本对比
- [`evaluation_comparison_example.py`](evaluation_comparison_example.py) - RAG 版本对比详细分析
  - 对比两个评测任务的指标差异
  - Per-query 详细分析
  - 识别改进和退化的问题
  - 适用场景：量化不同版本 RAG 系统的改进效果

## 🕸️ GraphRAG 批量评测

### 完整工作流
- [`graph_evaluation_example.py`](graph_evaluation_example.py) - GraphRAG 批量评测完整示例
  - 创建包含 gold_path 的测试集
  - 运行 GraphRAG 批量评测
  - 获取推理路径质量指标
  - 适用场景：评估剪枝策略优化效果

### 版本对比
- [`graph_evaluation_comparison_example.py`](graph_evaluation_comparison_example.py) - GraphRAG 版本对比详细分析
  - 对比分支爆炸比、推理跳数等指标
  - 识别哪些问题改进显著
  - 决策建议（效率 vs 准确性权衡）
  - 适用场景：对比不同搜索算法（BFS vs Beam Search）

## 🔍 单次运行示例

### API 方式
- [`rag_api_example.py`](rag_api_example.py) - 使用 REST API 进行单次 RAG 评测
  - 直接调用 HTTP API
  - 上报检索结果、prompt、答案
  - 获取单次运行指标
  - 适用场景：不使用 SDK 的集成方式

### SDK 方式
- [`rag_sdk_example.py`](rag_sdk_example.py) - 使用 Python SDK 进行单次 RAG 评测
  - 使用 RAGClient SDK
  - 简化的 API 调用
  - 推荐的集成方式
  - 适用场景：Python 项目快速集成

## 🎨 高级功能

### 相似度计算模式
- [`similarity_modes_example.py`](similarity_modes_example.py) - 三种相似度计算模式示例
  - Lexical（快速，基于关键词）
  - Embedding（准确，基于语义向量）
  - LLM Judge（主观，基于 LLM 判断）
  - 适用场景：了解不同相似度计算方式的差异

---

## 📝 使用建议

### 新手入门
1. 先运行 [`rag_sdk_example.py`](rag_sdk_example.py) 了解基本的单次评测流程
2. 再运行 [`evaluation_example.py`](evaluation_example.py) 学习批量评测

### 版本对比
1. 运行 [`evaluation_example.py`](evaluation_example.py) 建立 v1.0 基线
2. 修改你的 RAG 系统
3. 运行 [`evaluation_comparison_example.py`](evaluation_comparison_example.py) 对比效果

### GraphRAG 用户
1. 参考 [`graph_evaluation_example.py`](graph_evaluation_example.py) 集成 GraphRAG 上报
2. 使用 [`graph_evaluation_comparison_example.py`](graph_evaluation_comparison_example.py) 优化剪枝策略

---

## 🔗 相关文档

- [快速开始](../docs/QUICKSTART.md) - 详细的入门教程
- [RAG 批量评测指南](../docs/RAG_EVALUATION_GUIDE.md) - RAG 批量评测完整指南
- [GraphRAG 批量评测指南](../docs/GRAPH_EVALUATION_GUIDE.md) - GraphRAG 批量评测完整指南
- [RAG 指标说明](../docs/RAG_METRICS.md) - RAG 单次运行指标详解
- [GraphRAG 指标说明](../docs/GRAPHRAG_METRICS.md) - GraphRAG 推理路径指标详解
- [相似度引擎](../docs/SIMILARITY_ENGINE.md) - 相似度计算模式详解

---

## 🚀 运行示例

确保 TraceLens 服务已启动：

```bash
# 启动 TraceLens 服务
uvicorn tracelens.main:app --reload
```

运行示例：

```bash
# 进入 examples 目录
cd examples

# 运行任意示例
python evaluation_example.py
python graph_evaluation_example.py
python rag_sdk_example.py
```

**注意**：示例代码中的数据是模拟的，实际使用时需要替换为你的 RAG 系统调用。

