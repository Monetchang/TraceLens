```markdown
# TraceLens GraphRAG 评测指标文档

> **GraphRAG 的评测不是"找得像不像"，而是"推理走得对不对"。**  
> **TraceLens 评测的是推理轨迹，而不是文本片段。**

---

## 核心理念

GraphRAG 的核心是**基于知识图谱的推理**，而不是简单的文本检索。TraceLens GraphRAG 评测体系专注于：

1. **推理路径是否存在** - 基础正确性
2. **推理路径是否连贯** - 结构完整性
3. **推理路径是否合理** - 语义合理性

---

## 指标体系（三层架构）

### 第一层：结构性指标（Structural Metrics）

**特点**：无需 LLM，纯结构分析，零成本

| 指标名称 | 类型 | 范围 | 说明 | 使用场景 |
|---------|------|------|------|----------|
| **path_exists** | boolean | True/False | 是否存在推理路径 | 基础正确性判断 |
| **reasoning_hops** | integer | [0, ∞) | 推理跳数 | 判断推理链长度是否合理 |
| **connectivity_score** | float | [0.0, 1.0] | 图连通性得分 | 判断检索节点是否形成连通子图 |

#### 1.1 path_exists

**定义**：判断是否存在从起点到终点的推理路径

**计算方式**：
```python
path_exists = len(selected_path) > 0
```

**使用场景**：
- 防止"拍脑袋回答"（没有推理路径）
- 判断 GraphRAG 系统是否正常工作

**示例**：
```python
# 如果 path_exists = False
# 说明：系统没有找到推理路径，可能是：
# 1. 图数据不完整
# 2. 搜索策略过于保守
# 3. 剪枝过度
```

---

#### 1.2 reasoning_hops

**定义**：推理路径的跳数（边的数量）

**计算方式**：
```python
reasoning_hops = len(selected_path_edges)
```

**使用场景**：
- 判断推理链是否过长或过短
- 指导 max_hops 参数调优
- 版本对比：同一问题，不同版本的推理跳数

**示例**：
```python
# Query: "Alice 和 Project_AI 的关系"
# Path: Alice -> Company_X -> Project_AI
# reasoning_hops = 2

# 如果 reasoning_hops = 10
# 可能需要优化：
# 1. 增加剪枝
# 2. 调整 beam_size
# 3. 引入更强的相关性过滤
```

---

#### 1.3 connectivity_score

**定义**：检索到的节点是否形成连通子图

**计算方式**：
```python
connectivity_score = largest_connected_component_size / total_retrieved_nodes
```

**使用场景**：
- 判断 Graph 搜索是否"散点化"
- 评估检索质量（连通的图更有可能形成有效推理）

**示例**：
```python
# 如果 connectivity_score = 0.3
# 说明：只有 30% 的节点是连通的
# 可能原因：
# 1. 检索策略过于发散
# 2. 缺少关键连接边
# 3. 图数据质量问题
```

---

### 第二层：路径质量指标（Quality Metrics）

**特点**：基于结构分析，可选 gold data

| 指标名称 | 类型 | 范围 | 说明 | 使用场景 |
|---------|------|------|------|----------|
| **branch_explosion_ratio** | float | [1.0, ∞) | 分支爆炸比 | 评估剪枝策略有效性 |
| **path_coverage** | float | [0.0, 1.0] | 路径覆盖度（需要 gold） | 评估推理路径正确性 |

#### 2.1 branch_explosion_ratio

**定义**：总探索节点数 / 选中路径节点数

**计算方式**：
```python
branch_explosion_ratio = total_explored_nodes / selected_path_nodes
```

**使用场景**：
- 判断剪枝策略是否有效
- 版本对比：优化后的版本应该降低此比值
- 成本优化：比值越低，搜索效率越高

**示例**：
```python
# 场景1：v1.0 baseline
# total_explored_nodes = 100
# selected_path_nodes = 5
# branch_explosion_ratio = 20.0

# 场景2：v2.0 优化剪枝
# total_explored_nodes = 30
# selected_path_nodes = 5
# branch_explosion_ratio = 6.0

# 结论：v2.0 减少了 70% 的不必要探索
```

**优化建议**：
- `< 5.0`: 优秀，剪枝策略有效
- `5.0 - 10.0`: 良好
- `> 10.0`: 需要优化剪枝

---

#### 2.2 path_coverage（可选，需要 gold path）

**定义**：选中路径对 gold path 的覆盖度

**计算方式**：
```python
path_coverage = len(selected_nodes ∩ gold_nodes) / len(gold_nodes)
```

**使用场景**：
- Benchmark 测试
- 判断推理路径是否在正确轨道上
- A/B 测试不同策略

**示例**：
```python
# Gold Path: Alice -> Company_X -> Project_AI -> Team_ML
# Selected Path: Alice -> Company_X -> Project_AI

# path_coverage = 3/4 = 0.75

# 解读：
# - 覆盖了 75% 的 gold path
# - 缺少最后一跳（可能被剪枝）
```

---

### 第三层：语义合理性指标（Semantic Metrics）

**特点**：使用 LLM Judge，成本较高，精度最高

| 指标名称 | 类型 | 范围 | 说明 | 使用场景 |
|---------|------|------|------|----------|
| **path_relevance_score** | float | [0.0, 1.0] | 推理路径相关性 | 评估路径是否逻辑上支持答案 |

#### 3.1 path_relevance_score

**定义**：使用 LLM 判断推理路径是否逻辑上支持回答 query

**计算方式**：
```python
# 输入给 LLM：
# - Query
# - Reasoning Path (A → B → C)
# - Answer

# 输出：0.0 - 1.0 相关性得分
```

**Prompt 模板**：
```
Please evaluate whether the reasoning path logically supports answering the query.

Query: {query}

Reasoning Path:
{path_desc}

Answer: {answer}

Provide a relevance score (0.0 to 1.0) where:
- 0.0: Path is irrelevant or illogical
- 0.5: Path is partially relevant
- 1.0: Path strongly supports the answer

Return ONLY a number between 0.0 and 1.0.
Score:
```

**使用场景**：
- 高精度评估
- Benchmark 测试
- 关键决策验证

**示例**：
```python
# Query: "Alice 和 Project_AI 的关系"
# Path: Alice --[works_at]-> Company_X --[runs]-> Project_AI
# Answer: "Alice works at Company X, which runs Project AI."

# path_relevance_score = 0.95
# 解读：推理路径高度支持答案
```

---

## 指标使用建议

### 渐进式评估策略

```
阶段1：开发阶段
  └─ 使用结构性指标（免费，快速）

阶段2：测试阶段
  └─ 添加路径质量指标（如果有 gold data）

阶段3：关键决策
  └─ 使用语义合理性指标（LLM Judge）
```

### 成本优化

| 指标层级 | 成本 | 速度 | 精度 | 建议使用频率 |
|---------|------|------|------|-------------|
| 结构性 | 免费 | 毫秒级 | 中 | 100% |
| 质量 | 免费 | 毫秒级 | 中-高 | 80% |
| 语义 | 高 | 秒级 | 高 | 20% (关键 case) |

---

## API 使用示例

### 基本使用

```python
from sdk.graph_client import GraphRAGClient

graph_client = GraphRAGClient("http://localhost:8000")

# 1. 上报图扩展事件
graph_client.graph_expand(
    run_id=run_id,
    from_node="Alice",
    to_node="Company_X",
    relation="works_at",
    step_index=1
)

# 2. 上报路径选择
graph_client.path_selected(
    run_id=run_id,
    path=["Alice", "Company_X", "Project_AI"]
)

# 3. 获取指标（结构性 + 质量）
metrics = graph_client.get_graph_metrics(run_id)
print(metrics['structural_metrics'])
print(metrics['quality_metrics'])

# 4. 获取指标（包含语义）
metrics = graph_client.get_graph_metrics(run_id, include_semantic=True)
print(metrics['semantic_metrics'])
```

### 版本对比

```python
# 对比两个版本的推理效率
metrics_v1 = graph_client.get_graph_metrics(run_v1_id)
metrics_v2 = graph_client.get_graph_metrics(run_v2_id)

v1_explosion = metrics_v1['quality_metrics']['branch_explosion_ratio']
v2_explosion = metrics_v2['quality_metrics']['branch_explosion_ratio']

reduction = (1 - v2_explosion / v1_explosion) * 100
print(f"v2.0 减少了 {reduction:.1f}% 的不必要探索")
```

---

## 典型使用场景

### 场景1：评估剪枝策略

**问题**：GraphRAG 探索了太多不相关节点，效率低

**评估方法**：
```python
metrics = graph_client.get_graph_metrics(run_id)

# 关注指标
branch_explosion = metrics['quality_metrics']['branch_explosion_ratio']

# 判断
if branch_explosion > 10.0:
    print("剪枝策略不够有效，建议优化")
```

---

### 场景2：对比两种搜索策略

**问题**：BFS vs Beam Search，哪个更好？

**评估方法**：
```python
# 运行两个版本
run_bfs = run_graphrag(strategy="BFS")
run_beam = run_graphrag(strategy="Beam")

# 获取指标
metrics_bfs = graph_client.get_graph_metrics(run_bfs)
metrics_beam = graph_client.get_graph_metrics(run_beam)

# 对比
print(f"BFS 分支爆炸比: {metrics_bfs['quality_metrics']['branch_explosion_ratio']}")
print(f"Beam 分支爆炸比: {metrics_beam['quality_metrics']['branch_explosion_ratio']}")
```

---

### 场景3：验证推理路径质量

**问题**：推理路径看起来合理吗？

**评估方法**：
```python
# 获取推理路径
path_data = graph_client.get_reasoning_path(run_id)

# 查看选中路径
for step in path_data['selected_path']:
    print(f"{step['from_node']} --[{step['relation']}]-> {step['to_node']}")

# 获取语义评分
metrics = graph_client.get_graph_metrics(run_id, include_semantic=True)
relevance = metrics['semantic_metrics']['path_relevance_score']

if relevance < 0.5:
    print("⚠️ 推理路径相关性较低，需要检查")
```

---

## 数据上报规范

### 1. 图扩展事件（graph_expand）

**何时上报**：每次 GraphRAG 探索一条新边时

**数据结构**：
```json
{
  "run_id": "uuid",
  "from_node": "Alice",
  "to_node": "Company_X",
  "relation": "works_at",
  "step_index": 1
}
```

---

### 2. 路径选择事件（path_selected）

**何时上报**：GraphRAG 确定最终推理路径时

**数据结构**：
```json
{
  "run_id": "uuid",
  "path": ["Alice", "Company_X", "Project_AI"]
}
```

**注意**：
- `path` 是节点 ID 的有序列表
- 系统会自动匹配 `graph_expand` 事件，标记选中的边

---

## MVP 范围说明

### ✅ MVP 包含

1. 结构性指标（path_exists, reasoning_hops, connectivity_score）
2. 路径质量指标（branch_explosion_ratio, path_coverage）
3. 语义合理性指标（path_relevance_score）
4. 推理路径可视化
5. 版本对比能力

### ❌ MVP 不包含

1. 自动最优路径搜索
2. 全图最短路径证明
3. 多路径 ensemble 评测
4. 自动 gold path 构建
5. 实时路径推荐

---

## 常见问题

### Q1: GraphRAG 指标和 RAG 指标有什么区别？

**A**: 
- **RAG 指标**：评估文本检索质量（topK 相似度、chunk 覆盖度）
- **GraphRAG 指标**：评估推理路径质量（推理跳数、分支爆炸比、路径连通性）

核心差异：**RAG 评测"找得像不像"，GraphRAG 评测"推理走得对不对"**

---

### Q2: 如何选择合适的指标？

**建议**：
1. **日常开发**：只看结构性指标（免费，快速）
2. **版本对比**：关注 branch_explosion_ratio（效率提升）
3. **Benchmark**：使用 path_coverage + path_relevance_score（精度）

---

### Q3: branch_explosion_ratio 多少算合理？

**参考值**：
- `< 5.0`: 优秀
- `5.0 - 10.0`: 良好
- `10.0 - 20.0`: 一般，建议优化
- `> 20.0`: 需要优化剪枝策略

---

### Q4: 如何降低 branch_explosion_ratio？

**优化方向**：
1. 引入更强的相关性过滤
2. 减小 beam_size
3. 降低 max_hops
4. 使用语义剪枝（LLM Judge 提前剪枝）

---

## 批量评测

TraceLens 提供了 **GraphRAG 批量评测**功能，支持系统化地评估 GraphRAG 系统的推理效率和路径质量。

### 核心能力

1. **测试集管理**：创建和管理多跳推理测试问题集
2. **版本对比**：量化不同剪枝策略、搜索算法的优化效果
3. **聚合指标**：自动计算 avg / p50 / p95 等统计量
4. **Per-Query 分析**：识别哪些问题改进显著、哪些仍需优化

### 关键概念

- **TestSuite**：一组多跳推理测试问题的集合
- **TestCase**：单个测试问题，包含 `query`, `gold_path`, `gold_nodes` 等
- **Evaluation**：针对特定版本 GraphRAG 系统的评测任务
- **聚合指标**：对所有 runs 的指标进行统计（avg, p50, p95）

### Gold 数据设计

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `gold_path` | list[str] | ❌ | 标准推理路径的节点序列，如 `["Alice", "Company_X", "Project_AI"]` |
| `gold_nodes` | list[str] | ❌ | 应该检索到的关键节点集合 |

- `gold_path` 用于计算 `path_coverage`（路径覆盖度）
- `gold_nodes` 用于计算节点召回率
- 全部可选，支持无 gold 数据的场景

### 使用场景

#### 场景 1：评估剪枝策略优化

```python
# 创建测试集
test_suite = eval_client.create_test_suite(
    name="GraphRAG Reasoning Test Suite",
    description="50个多跳推理测试问题"
)

# 上传测试用例（包含 gold_path）
test_cases = [
    {
        "query": "Alice 和 Project_AI 的关系",
        "gold_path": ["Alice", "Company_X", "Project_AI"],
        "gold_nodes": ["Alice", "Company_X", "Project_AI"]
    },
    # ... 更多测试用例
]
eval_client.upload_test_cases(suite_id, test_cases)

# 运行 v1.0 评测（BFS）
evaluation_v1 = eval_client.create_evaluation(
    name="v1.0 BFS",
    test_suite_id=suite_id,
    version_id="v1.0_BFS",
    metadata={"search_strategy": "BFS", "max_hops": 5}
)
# ... 运行评测 ...

# 运行 v2.0 评测（Beam Search）
evaluation_v2 = eval_client.create_evaluation(
    name="v2.0 Beam Search",
    test_suite_id=suite_id,
    version_id="v2.0_BeamSearch",
    metadata={"search_strategy": "BeamSearch", "beam_size": 3}
)
# ... 运行评测 ...

# 版本对比
comparison = eval_client.compare_graph_evaluations(
    eval_a_id=evaluation_v1["id"],
    eval_b_id=evaluation_v2["id"]
)

# 分析结果
branch_delta = comparison["metrics_delta"]["quality"]["branch_explosion_ratio"]
print(f"分支爆炸比: {branch_delta['avg_a']:.2f} → {branch_delta['avg_b']:.2f}")
print(f"改善: {branch_delta['percent_change']:.1f}%")
```

#### 场景 2：参数调优（max_hops, beam_size）

```python
# 创建多个评测任务，分别使用不同参数
eval_hops3 = eval_client.create_evaluation(
    name="max_hops=3",
    test_suite_id=suite_id,
    version_id="v1_hops3",
    metadata={"max_hops": 3}
)

eval_hops5 = eval_client.create_evaluation(
    name="max_hops=5",
    test_suite_id=suite_id,
    version_id="v1_hops5",
    metadata={"max_hops": 5}
)

# 对比
comparison = eval_client.compare_graph_evaluations(
    eval_a_id=eval_hops3["id"],
    eval_b_id=eval_hops5["id"]
)
```

### API 端点

- `GET /api/v1/evaluation/{evaluation_id}/graph_metrics` - 获取 GraphRAG 聚合指标
- `GET /api/v1/evaluation/graph_compare?eval_a={uuid}&eval_b={uuid}` - 对比两个评测

### 详细文档

完整的 GraphRAG 批量评测指南，请参考：
- **[GRAPH_EVALUATION_GUIDE.md](GRAPH_EVALUATION_GUIDE.md)** - 完整的批量评测指南
- **[examples/graph_evaluation_example.py](../examples/graph_evaluation_example.py)** - 完整示例代码
- **[examples/graph_evaluation_comparison_example.py](../examples/graph_evaluation_comparison_example.py)** - 版本对比示例

---

## 总结

TraceLens GraphRAG 评测体系的核心价值：

> **让 GraphRAG 的推理过程从"黑盒"变成"可观测、可对比、可优化"的系统。**

三层指标体系：
- ✅ **结构性指标**：零成本，快速判断
- ⚡ **质量指标**：评估效率和正确性
- 🎯 **语义指标**：高精度验证

**适用场景**：
- 剪枝策略优化
- 搜索算法对比
- 版本回归测试
- Benchmark 评测
- **批量评测与版本对比**（新增）
```

