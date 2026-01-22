# GraphRAG 批量评测指南

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

**GraphRAG 批量评测**是 TraceLens 提供的系统化评估 GraphRAG 系统的能力，专注于**推理路径质量**和**推理效率**的评估。

### 为什么需要 GraphRAG 批量评测？

在 GraphRAG 系统开发中，你可能需要：
- 优化剪枝策略，减少不相关节点的探索
- 对比不同搜索算法（BFS vs Beam Search）
- 调优 `max_hops`、`beam_size` 等参数
- 评估版本迭代效果

**GraphRAG 批量评测让这些从"凭感觉"变成"有数据支撑"的决策。**

### GraphRAG 评测 vs RAG 评测

| 维度 | RAG 批量评测 | GraphRAG 批量评测 |
|------|-------------|------------------|
| **关注点** | 检索质量、召回率 | **推理效率**、路径质量、连通性 |
| **Gold 数据** | gold_answer, gold_chunk_ids, gold_doc_ids | **gold_path**, **gold_nodes**（可选）|
| **关键指标** | retrieval_utilization, pollution_rate | **branch_explosion_ratio**, **reasoning_hops**, **path_coverage** |
| **版本对比重点** | 检索结果变化 | **推理跳数变化**、分支爆炸比改善 |

---

## 核心概念

### 1. TestSuite（测试集）

一组多跳推理测试问题的集合。

**示例**：
```python
test_suite = {
    "name": "GraphRAG Reasoning Test Suite",
    "description": "50个多跳推理测试问题"
}
```

### 2. TestCase（测试用例）

单个测试问题，包含：

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `query` | string | ✅ | 测试问题 |
| `gold_answer` | string | ❌ | 正确答案 |
| `gold_path` | list[str] | ❌ | 标准推理路径的节点序列 |
| `gold_nodes` | list[str] | ❌ | 应该检索到的关键节点 |
| `metadata` | object | ❌ | 其他元数据（如难度、类型） |

**gold_path vs gold_nodes**：

- **gold_path**：标准推理路径的**有序**节点列表，如 `["Alice", "Company_X", "Project_AI"]`
  - 用于计算 `path_coverage`（路径覆盖度）
  
- **gold_nodes**：应该检索到的关键节点的**无序**集合，如 `["Alice", "Company_X", "Project_AI", "Team_ML"]`
  - 用于计算节点召回率（如果需要）

**示例**：
```python
test_case = {
    "query": "Alice 和 Project_AI 的关系",
    "gold_answer": "Alice works at Company X, which runs Project AI.",
    "gold_path": ["Alice", "Company_X", "Project_AI"],
    "gold_nodes": ["Alice", "Company_X", "Project_AI"],
    "metadata": {"hops": 2, "type": "entity_relation"}
}
```

### 3. Evaluation（评测任务）

针对一个 TestSuite 的**特定版本** GraphRAG 系统的评测任务。

**关键字段**：
- `version_id`: 版本标识（如 `"v1.0_BFS"`, `"v2.0_BeamSearch"`）
- `test_suite_id`: 关联的测试集
- `metadata`: 可选的配置信息（如 `{"search_strategy": "BFS", "max_hops": 5}`）

### 4. Run

评测任务中的单次执行，对应一个 TestCase。

**自动关联**：
- 当 `start_run` 时提供 `test_case_id`，会自动加载 `gold_path` 和 `gold_nodes` 到 `run.metadata`

---

## 前置条件

在进行批量评测之前，你的 GraphRAG 系统必须已经集成了 TraceLens 的数据上报接口。

### 必需的上报接口

根据 [`GRAPHRAG_METRICS.md`](GRAPHRAG_METRICS.md)，GraphRAG 系统需要上报：

1. **节点扩展事件**：`POST /api/v1/graph/node/expanded`
2. **边遍历事件**：`POST /api/v1/graph/edge/traversed`
3. **路径选择事件**：`POST /api/v1/graph/path/selected`
4. **答案生成事件**：`POST /api/v1/answer/generated`

### 集成方式

你可以选择使用 TraceLens Python SDK 或直接调用 REST API。详细的集成指南和示例代码，请参考：
- [`GRAPHRAG_METRICS.md`](GRAPHRAG_METRICS.md) 中的 "数据上报" 章节
- [`examples/rag_sdk_example.py`](../examples/rag_sdk_example.py)

**重要提示**：如果你的 GraphRAG 系统尚未集成上报接口，批量评测将无法计算指标。请先完成集成，再进行批量评测。

---

## 完整工作流

### Step 1: 创建测试集

```python
from sdk.evaluation_client import EvaluationClient

eval_client = EvaluationClient(base_url="http://localhost:8000")

test_suite = eval_client.create_test_suite(
    name="GraphRAG Reasoning Test Suite",
    description="50个多跳推理测试问题"
)
```

### Step 2: 上传测试用例

```python
from uuid import UUID

test_cases = [
    {
        "query": "Alice 和 Project_AI 的关系",
        "gold_answer": "Alice works at Company X, which runs Project AI.",
        "gold_path": ["Alice", "Company_X", "Project_AI"],
        "gold_nodes": ["Alice", "Company_X", "Project_AI"],
        "metadata": {"hops": 2, "type": "entity_relation"}
    },
    {
        "query": "Bob 参与了哪些项目？",
        "gold_answer": "Bob contributes to Project Beta and Project Gamma.",
        "gold_path": ["Bob", "Team_Engineering", "Project_Beta"],
        "gold_nodes": ["Bob", "Team_Engineering", "Project_Beta", "Project_Gamma"],
        "metadata": {"hops": 2, "type": "entity_relation"}
    },
    # ... 更多测试用例
]

result = eval_client.upload_test_cases(UUID(test_suite["id"]), test_cases)
print(f"已上传 {result['created_count']} 个测试用例")
```

### Step 3: 创建评测任务 v1.0

```python
evaluation_v1 = eval_client.create_evaluation(
    name="GraphRAG v1.0 Evaluation (BFS)",
    test_suite_id=UUID(test_suite["id"]),
    version_id="v1.0_BFS",
    metadata={"search_strategy": "BFS", "max_hops": 5}
)
```

### Step 4: 运行评测

**核心步骤**：
1. 获取测试用例列表
2. 对每个测试用例，启动 run（关联 `evaluation_id` 和 `test_case_id`）
3. 调用你的 GraphRAG 系统（已集成上报接口）
4. 结束 run

```python
from sdk.client import TraceLensClient

tracelens = TraceLensClient(base_url="http://localhost:8000")

# 获取测试用例
test_cases_to_run = eval_client.get_evaluation_test_cases(UUID(evaluation_v1["id"]))

for tc in test_cases_to_run:
    # 启动 run，自动关联 test_case 的 gold_path
    run = tracelens.start_run(
        name=f"v1.0_{tc['id']}",
        metadata={
            "evaluation_id": str(evaluation_v1["id"]),
            "test_case_id": str(tc["id"])
        }
    )
    
    # 调用你的 GraphRAG 系统（已集成上报接口）
    your_graphrag_system.run(tc["query"], run.id)
    
    # 结束 run
    tracelens.end_run(run.id, status="success")
```

### Step 5: 获取聚合指标

```python
metrics_v1 = eval_client.get_graph_evaluation_metrics(UUID(evaluation_v1["id"]))

print(f"总 runs: {metrics_v1['total_runs']}")
print(f"成功 runs: {metrics_v1['completed_runs']}")

# 结构性指标
for metric_name, stats in metrics_v1["aggregate_metrics"]["structural"].items():
    print(f"{metric_name}: avg={stats['avg']:.2f}, p50={stats['p50']:.2f}")

# 质量指标
for metric_name, stats in metrics_v1["aggregate_metrics"]["quality"].items():
    print(f"{metric_name}: avg={stats['avg']:.2f}, p50={stats['p50']:.2f}")
```

### Step 6: 运行 v2.0 评测

```python
# 创建 v2.0 评测任务
evaluation_v2 = eval_client.create_evaluation(
    name="GraphRAG v2.0 Evaluation (Beam Search)",
    test_suite_id=UUID(test_suite["id"]),
    version_id="v2.0_BeamSearch",
    metadata={"search_strategy": "BeamSearch", "beam_size": 3, "max_hops": 4}
)

# 运行评测（代码与 v1.0 类似）
# ...
```

### Step 7: 版本对比

```python
comparison = eval_client.compare_graph_evaluations(
    eval_a_id=UUID(evaluation_v1["id"]),
    eval_b_id=UUID(evaluation_v2["id"])
)

# 分析分支爆炸比
branch_delta = comparison["metrics_delta"]["quality"]["branch_explosion_ratio"]
print(f"分支爆炸比: {branch_delta['avg_a']:.2f} → {branch_delta['avg_b']:.2f}")
print(f"改善: {branch_delta['percent_change']:.1f}%")

# 分析推理跳数
hops_delta = comparison["metrics_delta"]["structural"]["reasoning_hops"]
print(f"推理跳数: {hops_delta['avg_a']:.2f} → {hops_delta['avg_b']:.2f}")
```

---

## API 参考

### 1. 创建测试集

```http
POST /api/v1/test_suite
Content-Type: application/json

{
  "name": "GraphRAG Reasoning Test Suite",
  "description": "50个多跳推理测试问题"
}
```

### 2. 批量上传测试用例

```http
POST /api/v1/test_suite/{suite_id}/test_cases
Content-Type: application/json

{
  "test_cases": [
    {
      "query": "Alice 和 Project_AI 的关系",
      "gold_answer": "Alice works at Company X, which runs Project AI.",
      "gold_path": ["Alice", "Company_X", "Project_AI"],
      "gold_nodes": ["Alice", "Company_X", "Project_AI"],
      "metadata": {"hops": 2}
    }
  ]
}
```

### 3. 创建评测任务

```http
POST /api/v1/evaluation
Content-Type: application/json

{
  "name": "GraphRAG v1.0 Evaluation (BFS)",
  "test_suite_id": "uuid",
  "version_id": "v1.0_BFS",
  "metadata": {"search_strategy": "BFS", "max_hops": 5}
}
```

### 4. 获取 GraphRAG 聚合指标

```http
GET /api/v1/evaluation/{evaluation_id}/graph_metrics?include_semantic=false&include_per_query=false
```

**响应示例**：

```json
{
  "evaluation_id": "uuid",
  "name": "GraphRAG v1.0 Evaluation (BFS)",
  "version_id": "v1.0_BFS",
  "total_runs": 50,
  "completed_runs": 48,
  "status": "completed",
  "aggregate_metrics": {
    "structural": {
      "path_exists": {
        "avg": 0.96,
        "p50": 1.0,
        "p95": 1.0,
        "min": 0.0,
        "max": 1.0
      },
      "reasoning_hops": {
        "avg": 3.5,
        "p50": 3.0,
        "p95": 5.0,
        "min": 1.0,
        "max": 6.0
      },
      "connectivity_score": {
        "avg": 0.78,
        "p50": 0.80,
        "p95": 0.95,
        "min": 0.5,
        "max": 1.0
      }
    },
    "quality": {
      "branch_explosion_ratio": {
        "avg": 12.5,
        "p50": 10.0,
        "p95": 20.0,
        "min": 3.0,
        "max": 30.0
      },
      "path_coverage": {
        "avg": 0.72,
        "p50": 0.75,
        "p95": 0.90,
        "min": 0.3,
        "max": 1.0
      }
    }
  },
  "per_query_metrics": null
}
```

### 5. 对比两个 GraphRAG 评测

```http
GET /api/v1/evaluation/graph_compare?eval_a={uuid}&eval_b={uuid}&include_semantic=false&include_per_query=false
```

**响应示例**：

```json
{
  "evaluation_a": {
    "id": "uuid",
    "version_id": "v1.0_BFS",
    "name": "GraphRAG v1.0 Evaluation (BFS)"
  },
  "evaluation_b": {
    "id": "uuid",
    "version_id": "v2.0_BeamSearch",
    "name": "GraphRAG v2.0 Evaluation (Beam Search)"
  },
  "metrics_delta": {
    "structural": {
      "reasoning_hops": {
        "avg_a": 4.5,
        "avg_b": 3.2,
        "delta": -1.3,
        "percent_change": -28.9,
        "p50_a": 4.0,
        "p50_b": 3.0,
        "p95_a": 6.0,
        "p95_b": 5.0
      }
    },
    "quality": {
      "branch_explosion_ratio": {
        "avg_a": 15.2,
        "avg_b": 8.5,
        "delta": -6.7,
        "percent_change": -44.1,
        "p50_a": 12.0,
        "p50_b": 7.0,
        "p95_a": 25.0,
        "p95_b": 15.0
      },
      "path_coverage": {
        "avg_a": 0.68,
        "avg_b": 0.75,
        "delta": 0.07,
        "percent_change": 10.3,
        "p50_a": 0.70,
        "p50_b": 0.80,
        "p95_a": 0.85,
        "p95_b": 0.95
      }
    }
  },
  "per_query_comparison": null
}
```

---

## SDK 使用

### 完整示例

详细示例代码请参考：
- [`examples/graph_evaluation_example.py`](../examples/graph_evaluation_example.py) - 完整工作流
- [`examples/graph_evaluation_comparison_example.py`](../examples/graph_evaluation_comparison_example.py) - 版本对比分析

### 快速开始

```python
from uuid import UUID
from sdk.evaluation_client import EvaluationClient

eval_client = EvaluationClient(base_url="http://localhost:8000")

# 1. 创建测试集
test_suite = eval_client.create_test_suite(
    name="GraphRAG Test",
    description="50个测试问题"
)

# 2. 上传测试用例
test_cases = [...]
eval_client.upload_test_cases(UUID(test_suite["id"]), test_cases)

# 3. 创建评测任务
evaluation = eval_client.create_evaluation(
    name="v1.0 Evaluation",
    test_suite_id=UUID(test_suite["id"]),
    version_id="v1.0_BFS"
)

# 4. 运行评测
# ... (调用你的 GraphRAG 系统)

# 5. 获取指标
metrics = eval_client.get_graph_evaluation_metrics(UUID(evaluation["id"]))

# 6. 版本对比
comparison = eval_client.compare_graph_evaluations(eval_a_id, eval_b_id)
```

---

## 聚合指标解读

### 三层指标体系

GraphRAG 评测指标分为三层：

#### 1. 结构性指标（Structural）

| 指标 | 含义 | 范围 | 理想值 | 解读 |
|------|------|------|--------|------|
| `path_exists` | 是否存在推理路径 | [0, 1] | 1.0 | 接近 1.0 说明系统能稳定找到推理路径 |
| `reasoning_hops` | 推理跳数 | [1, ∞) | 视业务而定 | 过高可能效率低，过低可能推理浅 |
| `connectivity_score` | 连通性得分 | [0, 1] | ≥ 0.8 | 高连通性说明检索的节点形成有意义的子图 |

#### 2. 质量指标（Quality）

| 指标 | 含义 | 范围 | 理想值 | 解读 |
|------|------|------|--------|------|
| `branch_explosion_ratio` | 分支爆炸比 | [1, ∞) | < 10 | **越低越好**。高值说明探索了大量无用节点 |
| `path_coverage` | 路径覆盖度 | [0, 1] | ≥ 0.7 | 需要 `gold_path`。高值说明路径准确 |

#### 3. 语义指标（Semantic，可选）

| 指标 | 含义 | 范围 | 理想值 | 解读 |
|------|------|------|--------|------|
| `path_relevance_score` | 路径相关性 | [0, 1] | ≥ 0.8 | 需要 LLM Judge。高值说明路径逻辑合理 |

### 聚合统计量

每个指标提供 5 个统计量：

- **avg**：平均值，反映整体水平
- **p50**（中位数）：更鲁棒的中心趋势
- **p95**：95% 的 runs 都在此值以下，反映尾部性能
- **min / max**：极值，用于发现异常

**建议关注顺序**：avg > p50 > p95 > max

---

## 版本对比最佳实践

### 场景 1：评估剪枝策略优化

**问题**：GraphRAG 探索了太多不相关节点，需要优化剪枝。

**方案**：

1. 创建测试集（50个多跳推理问题）
2. v1.0：使用现有剪枝策略运行评测
3. v2.0：使用新剪枝策略运行评测
4. 对比 `branch_explosion_ratio`

**期望结果**：v2.0 的 `avg_branch_explosion_ratio` 下降 30-50%

**示例**：

```python
comparison = eval_client.compare_graph_evaluations(eval_a_id, eval_b_id)

branch_delta = comparison["metrics_delta"]["quality"]["branch_explosion_ratio"]
if branch_delta["delta"] < -5.0:
    print("✅ 显著改善：剪枝策略优化有效")
```

### 场景 2：对比搜索算法（BFS vs Beam Search）

**问题**：不确定 BFS 还是 Beam Search 更适合当前场景。

**方案**：

1. 使用同一测试集
2. eval_A：使用 BFS 策略
3. eval_B：使用 Beam Search 策略
4. 对比 `branch_explosion_ratio`, `reasoning_hops`, `path_coverage`

**分析维度**：

- **效率**：哪个 `branch_explosion_ratio` 更低？
- **准确性**：哪个 `path_coverage` 更高？
- **平衡**：是否值得牺牲一些准确性换取效率？

**示例**：

```python
comparison = eval_client.compare_graph_evaluations(
    eval_a_id,  # BFS
    eval_b_id,  # Beam Search
    include_per_query=True
)

# 效率分析
branch = comparison["metrics_delta"]["quality"]["branch_explosion_ratio"]
print(f"效率: {branch['avg_a']:.1f} → {branch['avg_b']:.1f} ({branch['percent_change']:.1f}%)")

# 准确性分析
coverage = comparison["metrics_delta"]["quality"]["path_coverage"]
print(f"准确性: {coverage['avg_a']:.2%} → {coverage['avg_b']:.2%} ({coverage['percent_change']:.1f}%)")

# 决策
if branch["delta"] < 0 and coverage["delta"] > 0:
    print("✅ 推荐 Beam Search：效率和准确性都提升")
elif branch["delta"] < 0 and coverage["delta"] < 0:
    print("⚠️ 权衡：Beam Search 更高效但准确性下降")
```

### 场景 3：参数调优（max_hops, beam_size）

**问题**：不确定 `max_hops=5` 还是 `max_hops=3` 更好。

**方案**：

1. 创建多个评测任务，分别使用不同参数
2. 对比 `reasoning_hops` 和 `path_coverage`

**示例**：

```python
# max_hops=5
eval_5 = eval_client.create_evaluation(
    name="max_hops=5",
    test_suite_id=suite_id,
    version_id="v1_hops5",
    metadata={"max_hops": 5}
)

# max_hops=3
eval_3 = eval_client.create_evaluation(
    name="max_hops=3",
    test_suite_id=suite_id,
    version_id="v1_hops3",
    metadata={"max_hops": 3}
)

# 对比
comparison = eval_client.compare_graph_evaluations(eval_5["id"], eval_3["id"])
```

---

## 常见问题

### 1. 如果没有 gold_path，还能计算指标吗？

**可以**。`gold_path` 是可选的。

**不需要 gold_path 的指标**（gold-optional）：
- `path_exists`
- `reasoning_hops`
- `connectivity_score`
- `branch_explosion_ratio`

**需要 gold_path 的指标**（gold-aware）：
- `path_coverage`

**建议**：
- 初期没有 gold_path 时，关注 `branch_explosion_ratio` 和 `reasoning_hops`
- 后期有能力标注 gold_path 时，再关注 `path_coverage`

### 2. 如何标注 gold_path？

**方法 1：手动标注**
- 对于关键测试问题，由领域专家标注标准推理路径

**方法 2：从优秀 runs 中提取**
- 运行评测后，找到效果好的 runs
- 提取其 reasoning path 作为 gold_path

**方法 3：LLM 辅助标注**
- 使用 LLM 生成候选路径
- 人工审核确认

### 3. 评测任务运行失败的 runs 怎么处理？

聚合指标**只计算 status=success 的 runs**。

失败的 runs（status=error）会被排除，不影响聚合结果。

### 4. 如何集成 LLM Judge 计算语义指标？

目前 `path_relevance_score` 需要 LLM，但默认不启用。

**启用方法**（待实现）：
```python
metrics = eval_client.get_graph_evaluation_metrics(
    evaluation_id,
    include_semantic=True  # 启用 LLM Judge
)
```

需要配置 LLM 客户端（如 OpenAI API）。

### 5. 批量评测会自动加载 gold_path 吗？

**会**。

当你调用 `start_run` 并提供 `test_case_id` 时：
1. TraceLens 会自动从 `TestCase` 中读取 `gold_path` 和 `gold_nodes`
2. 存储到 `run.metadata`
3. 计算指标时会自动使用

**无需手动传递 gold_path**。

### 6. 可以在同一个 TestSuite 上运行多次评测吗？

**可以**。

一个 TestSuite 可以关联多个 Evaluation，每个 Evaluation 对应一个版本或配置。

**示例**：
```python
# 同一个 test_suite，多次评测
eval_v1 = eval_client.create_evaluation(suite_id, version_id="v1.0")
eval_v2 = eval_client.create_evaluation(suite_id, version_id="v2.0")
eval_v3 = eval_client.create_evaluation(suite_id, version_id="v3.0")
```

### 7. per_query_metrics 包含什么？

当 `include_per_query=True` 时，返回每个测试用例的详细指标。

**用途**：
- 识别哪些问题改进显著
- 识别哪些问题仍需优化
- 深入分析特定问题的推理路径

**示例**：
```python
metrics = eval_client.get_graph_evaluation_metrics(
    evaluation_id,
    include_per_query=True
)

for item in metrics["per_query_metrics"]:
    print(f"Query: {item['query']}")
    print(f"  branch_explosion_ratio: {item['metrics']['quality']['branch_explosion_ratio']}")
```

### 8. 评测任务可以暂停和恢复吗？

**可以**。

评测任务只是一个逻辑分组，实际的执行是逐个 run 完成的。

你可以：
- 先运行部分 test_cases
- 随时停止
- 稍后继续运行剩余的 test_cases
- 调用 `get_evaluation_status` 查看进度

---

## 总结

GraphRAG 批量评测系统的核心价值：

> **让 GraphRAG 的推理效率和路径质量从"凭感觉"变成"有数据支撑"的系统化评估。**

**三个关键能力**：
1. 🎯 **聚合指标**：系统化评估推理效率（branch_explosion）和路径质量（path_coverage）
2. 📊 **版本对比**：量化剪枝策略、搜索算法优化的效果
3. 🔍 **Per-Query 分析**：识别哪些问题改进显著、哪些仍需优化

**适用场景**：
- 剪枝策略优化验证
- 搜索算法选型（BFS/DFS/Beam）
- max_hops / beam_size 参数调优
- 版本回归测试

---

**相关文档**：
- [`GRAPHRAG_METRICS.md`](GRAPHRAG_METRICS.md) - GraphRAG 单次指标计算详解
- [`RAG_EVALUATION_GUIDE.md`](RAG_EVALUATION_GUIDE.md) - RAG 批量评测指南
- [`examples/graph_evaluation_example.py`](../examples/graph_evaluation_example.py) - 完整示例代码

