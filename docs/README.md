# TraceLens 文档

## 文档导航

| 文档 | 说明 |
|------|------|
| [快速开始](QUICKSTART.md) | 安装、配置、单 Run 与批量评测入门 |
| [RAG 指标说明](RAG_METRICS.md) | 单 run 指标（topK、prompt_answer、版本对比等） |
| [RAG 批量评测指南](RAG_EVALUATION_GUIDE.md) | TestSuite、Evaluation、版本对比 |
| [GraphRAG 指标说明](GRAPHRAG_METRICS.md) | 推理路径、连通性、分支爆炸比、答案支撑指标 |
| [GraphRAG 批量评测指南](GRAPH_EVALUATION_GUIDE.md) | GraphRAG 批量评测与版本对比 |
| [相似度引擎](SIMILARITY_ENGINE.md) | Lexical / Embedding / LLM 模式 |

## 最近更新

- **API 测试脚本**（2026-03-09）：`tests/test_api.py` 覆盖 43 个接口，使用 TestClient 进程内测试；修复 `prompt_chunks`、`evaluation.version_id` 等请求体；新增 ingest、runs/diff、evaluation compute/metrics/compare、graph_metrics/graph_compare 等测试。
- **接口与存储修复**：`/evaluation/compare`、`/evaluation/graph_compare` 路由提前定义避免 422；`MetricRepository.upsert` 使用 `metadata` 列名；`TestCaseResponse` 中 `metadata` 为 None 时使用 `{}`。
- **GraphRAG 指标升级**：新增 `irrelevant_branch_ratio`、`relation_chain_validity`、`grounding_metrics`（`answer_grounded_in_path_score`、`unsupported_claim_ratio`）；引入 `GraphMetricsContext` 统一缓存；规则版 claim 抽取与 evidence 匹配；`get_graph_metrics(include_grounding=True)`。

## 示例代码

见 [examples/](../examples/) 目录。

## 运行测试

```bash
python3 tests/test_api.py
```
