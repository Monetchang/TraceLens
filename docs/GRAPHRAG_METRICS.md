# TraceLens GraphRAG 指标文档

## 核心设计理念

TraceLens GraphRAG 专注于 **推理路径质量评估** 和 **版本变化分析**，不试图替代通用评测体系，而是回答：

> **当你更换剪枝策略、搜索算法或图结构时，推理能力到底发生了什么变化？**

GraphRAG 的评测不是"找得像不像"，而是 **推理走得对不对**。

TraceLens 评测的是 **推理轨迹（reasoning trace）**，而不是文本片段。

---

## 名词说明

- **graph_expand**：图扩展事件，每次 GraphRAG 探索一条新边时上报。
- **path_selected**：路径选择事件，GraphRAG 确定最终推理路径时上报。
- **explored_nodes**：搜索过程中所有被访问过的节点（含被剪枝的），通过 `graph_expand` 上报。
- **selected_path**：选中的推理路径（节点序列），通过 `path_selected` 上报。是 explored_nodes 的子集，数量通常更少。
- **gold_path**：人工标注的正确推理路径（可选），用于 Benchmark 评测。
- **gold_nodes**：应该覆盖到的关键节点集合（可选），gold_path 的节点提取结果。

---

## 指标分类

TraceLens GraphRAG 提供 **四层指标**：

1. **结构性指标（零成本）**：不依赖 embedding 或 LLM，纯路径结构计算。
   - `path_exists`：是否存在有效推理路径
   - `reasoning_hops`：推理跳数
   - `connectivity_score`：图连通性得分

2. **路径质量指标**（需要 `prev_run_id` 做版本对比，或需要 gold_nodes）：
   - `branch_explosion_ratio`：分支爆炸比（单 run 可算）
   - `irrelevant_branch_ratio`：无关分支比例（单 run 可算）
   - `path_coverage`：路径覆盖度（需要 gold_nodes）

3. **语义合理性指标（LLM Judge）**：需要 LLM 调用，成本较高。
   - `path_relevance_score`：路径语义相关性
   - `relation_chain_validity`：关系链合法性

4. **答案支撑指标（Answer Grounding）**：需要 LLM 调用。
   - `answer_grounded_in_path_score`：答案证据支撑度
   - `unsupported_claim_ratio`：无证据声明比例

---

## 一、核心指标详解

### 1. path_exists

**指标名称**: path_exists（是否存在推理路径）

> GraphRAG 系统的基础健康检查。若 `selected_path` 为空，说明图搜索未找到任何有效路径，后续所有路径质量指标均无意义。

**需要信息**:
- `selected_path`（通过 `path_selected` 上报）

**计算方式**:
```python
path_exists = len(selected_path) > 0
```

**使用场景**:
- GraphRAG 系统健康检查
- 监控"无路径回答"的发生频率
- 在路径不存在时提前告警，跳过其他指标计算

**指导价值**:
- **True**: 系统正常找到推理路径
- **False**: 图搜索失败，需检查图结构、起始节点或搜索配置

---

### 2. reasoning_hops

**指标名称**: reasoning_hops（推理跳数）

> 推理路径中边的数量，衡量推理链的长度与复杂度。跳数过少可能说明推理过于简单（未充分利用图结构），跳数过多可能存在冗余推理或搜索失控。

**需要信息**:
- `selected_path`（节点序列）

**计算方式**:
```python
reasoning_hops = len(selected_path) - 1  # 节点数 - 1 = 边数
```

**使用场景**:
- 判断推理链长度是否合理
- 调整 `max_hops` 参数
- 对比不同搜索策略下推理深度的变化

**指导价值**:

| hops | 含义 |
| ---- | ---- |
| 1-3  | 简单推理，适合事实性 query |
| 4-6  | 正常多跳推理 |
| >10  | 可能存在推理冗余，需审查路径 |

---

### 3. connectivity_score

**指标名称**: connectivity_score（图连通性得分）

> 衡量检索到的节点是否形成连通子图。高连通性说明 GraphRAG 检索到的节点之间有紧密关联；低连通性说明搜索过于发散，检索到一堆孤立节点，推理路径可能不连贯。

**需要信息**:
- `explored_nodes`（所有被访问节点）
- 节点间的边关系（来自 `graph_expand` 事件）

**计算方式**:
```python
connectivity_score = largest_connected_component_size / total_retrieved_nodes
```

**使用场景**:
- 评估图搜索的聚焦程度
- 诊断搜索算法是否偏离主题
- 对比不同图结构下的连通性变化

**指导价值**:

| score   | 含义 |
| ------- | ---- |
| >0.8    | 图结构良好，节点高度关联 |
| 0.3-0.8 | 正常，部分发散可接受 |
| <0.3    | 搜索过于发散，需优化剪枝策略 |

---

### 4. branch_explosion_ratio

**指标名称**: branch_explosion_ratio（分支爆炸比）

> 衡量搜索空间的扩展程度：探索了多少节点，最终只用了多少。比值越高说明搜索效率越低，大量计算资源浪费在无效分支上。

**需要信息**:
- `explored_nodes`（总探索节点数，通过 `graph_expand` 累计）
- `selected_path`（最终选中的路径节点数）

**计算方式**:
```python
branch_explosion_ratio = total_explored_nodes / len(selected_path_nodes)
```

**使用场景**:
- 评估搜索算法效率
- 指导剪枝策略优化
- 对比不同搜索算法（BFS/DFS/Beam Search）的效率

**指导价值**:

| ratio | 含义 |
| ----- | ---- |
| <5    | 搜索效率优秀 |
| 5-10  | 良好，正常范围 |
| >10   | 搜索效率低，建议增强剪枝 |

---

### 5. irrelevant_branch_ratio

**指标名称**: irrelevant_branch_ratio（无关分支比例）

> 衡量探索节点中与 query 语义无关的比例。此指标需要 embedding 计算各节点与 query 的相似度，判断是否偏离主题。高值意味着大量搜索资源消耗在与 query 无关的方向上。

**需要信息**:
- `explored_nodes` 的内容（节点文本）
- query 文本
- embedding 函数（服务端配置）

**计算方式**:
```python
node_embs = [embed(node.content) for node in explored_nodes]
query_emb = embed(query)
similarities = [cosine_similarity(node_emb, query_emb) for node_emb in node_embs]

# 低于阈值（默认 0.3）的节点视为无关分支
irrelevant_count = sum(1 for s in similarities if s < IRRELEVANCE_THRESHOLD)
irrelevant_branch_ratio = irrelevant_count / len(explored_nodes)
```

**使用场景**:
- 判断搜索是否偏离 query 方向
- 优化语义过滤策略
- 对比不同 embedding 模型对搜索方向的影响

**指导价值**:
- **低值（<0.2）**: 搜索聚焦，探索节点大多与 query 相关
- **高值（>0.5）**: 搜索偏离严重，需优化语义过滤或起始节点选择

---

### 6. path_coverage

**指标名称**: path_coverage（路径覆盖度）

> **前提**：需要提前上报 `gold_nodes`。计算 selected_path 中的节点对 gold_nodes 的覆盖比例。此指标是 GraphRAG 版本的 `exact_recall_vs_gold_chunks`，评估推理路径是否覆盖了标注的关键节点。

> **注意**：此指标是节点 ID 的精确匹配，不做语义比较。

**需要信息**:
- `selected_path`（通过 `path_selected` 上报）
- `gold_nodes`（通过 `gold_path` 事件上报，可选）

**计算方式**:
```python
selected_node_ids = set(node.id for node in selected_path)
gold_node_ids = set(node.id for node in gold_nodes)
path_coverage = len(selected_node_ids & gold_node_ids) / len(gold_node_ids) if gold_node_ids else 0.0
```

**使用场景**:
- Benchmark 评测
- A/B 测试不同搜索策略
- 验证推理路径对标注关键节点的精确命中率

**指导价值**:
- **高值（>0.8）**: 推理路径覆盖了大部分关键节点
- **低值（<0.5）**: 推理路径遗漏了重要节点，需优化搜索策略

---

### 7. path_relevance_score

**指标名称**: path_relevance_score（路径语义相关性）

> 使用 LLM 判断推理路径整体是否与 query 相关、是否支持生成 answer。不同于 `irrelevant_branch_ratio` 只看节点级相似度，此指标从语义层面整体判断路径质量。

**需要信息**:
- query 文本
- `selected_path`（节点序列及关系标签）
- answer 文本（可选，辅助判断）
- LLM Judge 配置（服务端配置）

**计算方式**:
```python
score = llm_judge(
    prompt=f"Query: {query}\nReasoning Path: {format_path(selected_path)}\nAnswer: {answer}",
    task="rate_path_relevance"  # 输出 0.0-1.0
)
```

**使用场景**:
- 评估推理路径的整体语义质量
- 对比不同搜索策略生成路径的语义合理性
- 与结构指标配合：`path_exists=True` 但 `path_relevance_score` 低，说明找到了路径但路径不对

**指导价值**:
- **高值（>0.8）**: 路径与 query 高度相关，推理方向正确
- **低值（<0.5）**: 路径语义偏离，即使结构完整也无法支撑正确回答

---

### 8. relation_chain_validity

**指标名称**: relation_chain_validity（关系链合法性）

> 判断推理路径中相邻节点之间的关系是否构成合理的逻辑链。纯结构上连通不等于语义上合理——`Alice -> works_at -> Company_X -> located_in -> City_Y` 是合理链，但 `Alice -> born_in -> Company_X` 就是错误关系。

**需要信息**:
- `selected_path`（节点序列 + 关系标签，需在 `graph_expand` 时上报 `relation` 字段）

**计算方式**:
```python
# 方式一：规则判断（基于关系类型白名单）
valid_pairs = [(r1, r2) for r1, r2 in zip(path_relations[:-1], path_relations[1:])
               if is_valid_transition(r1, r2)]
validity = len(valid_pairs) / len(path_relations) if path_relations else 0.0

# 方式二：LLM Judge（更准确）
validity = llm_relation_check(
    prompt=f"Reasoning path: {format_path_with_relations(selected_path)}",
    task="validate_relation_chain"  # 输出 0.0-1.0
)
```

**使用场景**:
- 检测推理路径中的逻辑错误
- 验证图谱关系类型设计是否合理
- 诊断 GraphRAG 是否产生了"结构合理但语义荒谬"的路径

**指导价值**:
- **高值（>0.8）**: 关系链逻辑合理
- **低值（<0.5）**: 路径中存在关系跳跃或逻辑矛盾，需审查图谱数据质量

---

### 9. answer_grounded_in_path_score

**指标名称**: answer_grounded_in_path_score（答案证据支撑度）

> 判断最终 answer 中有多少内容可以在推理路径中找到证据支撑。对应 RAG 指标中的 `prompt_chunk_answer_similarity`，但 GraphRAG 版本针对结构化路径而非文本片段。

**需要信息**:
- answer 文本（通过 `answer_generated` 上报）
- `selected_path`（节点序列及关系）
- LLM Judge 配置

**计算流程**:
```python
# 1. 从 answer 中抽取 claims
claims = extract_claims(answer)

# 2. 对每个 claim，在推理路径中查找支撑证据
supported_claims = [
    claim for claim in claims
    if llm_judge(claim, reasoning_path, task="check_support")
]

# 3. 计算支持比例
answer_grounded_in_path_score = len(supported_claims) / len(claims) if claims else 0.0
```

**使用场景**:
- 衡量推理路径对最终回答的实际贡献
- 检测 LLM 是否忽略了图谱信息，自行编造答案
- 与 `path_relevance_score` 配合：路径相关但 grounding 低，说明 LLM 未充分利用路径

**指导价值**:
- **高值（>0.8）**: 答案大部分来自推理路径，幻觉少
- **低值（<0.5）**: 答案内容与推理路径关联弱，可能存在大量幻觉

---

### 10. unsupported_claim_ratio

**指标名称**: unsupported_claim_ratio（无证据声明比例）

> `answer_grounded_in_path_score` 的补集，直接衡量答案中 hallucination 的比例。高值意味着 LLM 在推理路径之外自行"编造"了大量内容。

**需要信息**:
- answer 文本
- `selected_path`
- LLM Judge 配置

**计算方式**:
```python
unsupported_claim_ratio = 1.0 - answer_grounded_in_path_score
# 或
unsupported_claim_ratio = unsupported_claims / total_claims
```

**使用场景**:
- 检测答案中的 hallucination
- 监控 GraphRAG 系统的可信度
- 对比不同 LLM 在相同推理路径下的幻觉率

**指导价值**:

| ratio   | 含义 |
| ------- | ---- |
| <0.1    | 几乎无 hallucination |
| 0.1-0.3 | 可接受，存在少量推断 |
| >0.3    | 幻觉较多，需关注 |

---

## 二、数据上报

### 数据库表结构

GraphRAG 复用 RAG 的 `run` 和 `metric` 表，新增图谱专用表：

#### 1. run 表（复用）
```sql
CREATE TABLE run (
    id UUID PRIMARY KEY,
    name VARCHAR,
    query TEXT,
    answer TEXT,
    version_id VARCHAR,
    status VARCHAR,
    metadata JSONB,
    started_at TIMESTAMP,
    ended_at TIMESTAMP
);
```

#### 2. graph_expand 表
```sql
CREATE TABLE graph_expand (
    id UUID PRIMARY KEY,
    run_id UUID REFERENCES run(id),
    from_node VARCHAR,
    to_node VARCHAR,
    relation VARCHAR,
    step_index INT,
    created_at TIMESTAMP
);
```

#### 3. graph_path 表
```sql
CREATE TABLE graph_path (
    run_id UUID REFERENCES run(id) PRIMARY KEY,
    path JSONB,  -- 节点序列，如 ["Alice", "Company_X", "Project_AI"]
    created_at TIMESTAMP
);
```

#### 4. gold_path 表（可选）
```sql
CREATE TABLE gold_path (
    run_id UUID REFERENCES run(id) PRIMARY KEY,
    gold_nodes JSONB,  -- 关键节点 ID 列表
    created_at TIMESTAMP
);
```

#### 5. metric 表（复用）
```sql
CREATE TABLE metric (
    id UUID PRIMARY KEY,
    run_id UUID REFERENCES run(id),
    name VARCHAR,
    value FLOAT,
    value_json JSONB,
    metadata JSONB,
    created_at TIMESTAMP
);
```

---

### 上报接口

#### POST /api/v1/graph/expand

上报图扩展事件（每探索一条边调用一次）

```json
{
    "run_id": "uuid",
    "from_node": "Alice",
    "to_node": "Company_X",
    "relation": "works_at",
    "step_index": 1
}
```

#### POST /api/v1/graph/path_selected

上报最终选中的推理路径

```json
{
    "run_id": "uuid",
    "path": ["Alice", "Company_X", "Project_AI"]
}
```

#### POST /api/v1/gold/path（可选）

上报 gold path 标注数据

```json
{
    "run_id": "uuid",
    "gold_nodes": ["Alice", "Company_X", "Project_AI"]
}
```

#### POST /api/v1/answer/generated（复用）

上报 answer 生成事件（与 RAG 共用）

```json
{
    "run_id": "uuid",
    "answer": "Alice works at Company_X which is located in City_Y."
}
```

#### POST /api/v1/run/finished（复用）

```json
{
    "run_id": "uuid",
    "status": "success"
}
```

---

## 三、API 接口

### 查询接口

#### GET /api/v1/run/{run_id}/graph-metrics

获取 GraphRAG run 的完整指标

**查询参数**:
- `include_semantic` (bool, 可选): 是否计算语义指标（`path_relevance_score`, `relation_chain_validity`），需要 LLM，默认 `false`
- `include_grounding` (bool, 可选): 是否计算答案支撑指标，默认 `true`；无 answer 时返回 `null`

**响应**:
```json
{
    "run_id": "uuid",
    "structural_metrics": {
        "path_exists": true,
        "reasoning_hops": 2,
        "connectivity_score": 0.85
    },
    "quality_metrics": {
        "branch_explosion_ratio": 6.0,
        "irrelevant_branch_ratio": 0.15,
        "path_coverage": 0.75
    },
    "semantic_metrics": {
        "path_relevance_score": 0.92,
        "relation_chain_validity": 0.88
    },
    "grounding_metrics": {
        "answer_grounded_in_path_score": 0.81,
        "unsupported_claim_ratio": 0.12
    }
}
```

> `semantic_metrics` 和 `grounding_metrics` 在未传入对应 include 参数时返回 `null`。

#### GET /api/v1/run/{run_id}/graph_diff

获取两个 run 的图推理差异（版本对比）

**查询参数**:
- `prev_run_id` (UUID, 必填): 上一版本的 run_id

**响应**:
```json
{
    "run_id": "uuid",
    "prev_run_id": "uuid",
    "path_length_delta": -1,
    "new_nodes": ["Project_AI"],
    "dropped_nodes": ["Company_Y"],
    "connectivity_delta": 0.05,
    "branch_explosion_delta": -2.0
}
```

**字段说明**:
- `path_length_delta`: 推理跳数变化（负值=路径变短）
- `new_nodes`: 当前版本路径中新增的节点（上一版本没有）
- `dropped_nodes`: 上一版本路径中丢失的节点（当前版本没有）
- `connectivity_delta`: 连通性得分变化
- `branch_explosion_delta`: 分支爆炸比变化（负值=搜索效率提升）

---

## 四、使用流程

1. **创建 run**
   ```python
   POST /api/v1/run/start
   {"name": "graph_query", "metadata": {"version_id": "v1.0"}}
   ```

2. **上报图扩展事件**（每探索一条边调用一次）
   ```python
   POST /api/v1/graph/expand
   {"run_id": "...", "from_node": "Alice", "to_node": "Company_X", "relation": "works_at", "step_index": 1}
   ```

3. **上报选中推理路径**
   ```python
   POST /api/v1/graph/path_selected
   {"run_id": "...", "path": ["Alice", "Company_X", "Project_AI"]}
   ```

4. **上报 answer**
   ```python
   POST /api/v1/answer/generated
   {"run_id": "...", "answer": "Alice works at Company_X..."}
   ```

5. **上报 gold path（可选）**
   ```python
   POST /api/v1/gold/path
   {"run_id": "...", "gold_nodes": ["Alice", "Company_X"]}
   ```

6. **结束 run**
   ```python
   POST /api/v1/run/finished
   {"run_id": "...", "status": "success"}
   ```

7. **查询指标**
   ```python
   # 查询结构指标 + 质量指标 + grounding
   GET /api/v1/run/{run_id}/graph-metrics

   # 查询全量指标（含 LLM 语义指标）
   GET /api/v1/run/{run_id}/graph-metrics?include_semantic=true&include_grounding=true

   # 查询版本对比
   GET /api/v1/run/{run_id}/graph_diff?prev_run_id={prev_run_id}
   ```

---

## 五、SDK 示例

```python
from sdk.graph_client import GraphClient
from sdk.client import TraceLensClient

# 初始化
base_client = TraceLensClient("http://localhost:8000")
graph_client = GraphClient("http://localhost:8000")

# 1. 创建 run
run = base_client.start_run(
    name="graph_query",
    metadata={"version_id": "v1.0"}
)

# 2. 上报图扩展事件
graph_client.graph_expand(
    run_id=run.id,
    from_node="Alice",
    to_node="Company_X",
    relation="works_at",
    step_index=1
)
graph_client.graph_expand(
    run_id=run.id,
    from_node="Company_X",
    to_node="Project_AI",
    relation="owns",
    step_index=2
)

# 3. 上报选中路径
graph_client.path_selected(
    run_id=run.id,
    path=["Alice", "Company_X", "Project_AI"]
)

# 4. 上报 answer
graph_client.answer_generated(run.id, "Alice works at Company_X which owns Project_AI.")

# 5. 上报 gold path（可选）
graph_client.gold_path(run.id, gold_nodes=["Alice", "Company_X"])

# 6. 结束 run
graph_client.run_finished(run.id, "success")

# 7. 查询指标
metrics = graph_client.get_graph_metrics(run.id, include_semantic=True, include_grounding=True)
print(metrics["structural_metrics"])
print(metrics["quality_metrics"])
print(metrics["semantic_metrics"])
print(metrics["grounding_metrics"])

# 8. 版本对比（如果有上一版本）
diff = graph_client.get_graph_diff(run.id, prev_run_id)
print(diff)
```

---

## 六、指标计算伪代码

### 结构性指标（零成本）

```python
def compute_structural_metrics(run_id):
    path = get_selected_path(run_id)
    explored = get_explored_nodes(run_id)
    edges = get_graph_edges(run_id)

    # path_exists
    path_exists = len(path) > 0
    save_metric(run_id, "path_exists", float(path_exists))

    if not path_exists:
        return

    # reasoning_hops
    reasoning_hops = len(path) - 1
    save_metric(run_id, "reasoning_hops", reasoning_hops)

    # connectivity_score
    graph = build_subgraph(explored, edges)
    largest_cc = max(connected_components(graph), key=len)
    connectivity_score = len(largest_cc) / len(explored) if explored else 0.0
    save_metric(run_id, "connectivity_score", connectivity_score)
```

### 路径质量指标

```python
def compute_quality_metrics(run_id):
    path = get_selected_path(run_id)
    explored = get_explored_nodes(run_id)
    query = get_query(run_id)

    # branch_explosion_ratio
    branch_explosion_ratio = len(explored) / len(path) if path else 0.0
    save_metric(run_id, "branch_explosion_ratio", branch_explosion_ratio)

    # irrelevant_branch_ratio（需要 embedding）
    query_emb = embed(query)
    node_embs = [embed(node.content) for node in explored]
    similarities = [cosine_similarity(node_emb, query_emb) for node_emb in node_embs]
    irrelevant_count = sum(1 for s in similarities if s < IRRELEVANCE_THRESHOLD)
    irrelevant_branch_ratio = irrelevant_count / len(explored) if explored else 0.0
    save_metric(run_id, "irrelevant_branch_ratio", irrelevant_branch_ratio)

    # path_coverage（需要 gold_nodes）
    gold = get_gold_nodes(run_id)
    if gold:
        selected_ids = set(n.id for n in path)
        gold_ids = set(n.id for n in gold)
        path_coverage = len(selected_ids & gold_ids) / len(gold_ids)
        save_metric(run_id, "path_coverage", path_coverage)
```

### 语义指标（需要 LLM）

```python
def compute_semantic_metrics(run_id):
    query = get_query(run_id)
    answer = get_answer(run_id)
    path = get_selected_path(run_id)

    # path_relevance_score
    path_relevance_score = llm_judge(query, path, answer, task="rate_path_relevance")
    save_metric(run_id, "path_relevance_score", path_relevance_score)

    # relation_chain_validity
    relation_chain_validity = llm_relation_check(path, task="validate_relation_chain")
    save_metric(run_id, "relation_chain_validity", relation_chain_validity)
```

### 答案支撑指标（需要 LLM）

```python
def compute_grounding_metrics(run_id):
    answer = get_answer(run_id)
    path = get_selected_path(run_id)

    claims = extract_claims(answer)
    supported = [c for c in claims if llm_judge(c, path, task="check_support")]

    answer_grounded_score = len(supported) / len(claims) if claims else 0.0
    unsupported_ratio = 1.0 - answer_grounded_score

    save_metric(run_id, "answer_grounded_in_path_score", answer_grounded_score)
    save_metric(run_id, "unsupported_claim_ratio", unsupported_ratio)
```

---

## 七、常见问题

### Q1: 如何配置 LLM Judge？

语义指标和答案支撑指标需要 LLM Judge。在服务端启动时配置：

```python
from tracelens.core.llm_judge import set_llm_judge

def my_llm_judge(prompt: str, task: str) -> float:
    # 使用你的 LLM（OpenAI、Anthropic 等）
    response = llm.chat(prompt)
    return parse_score(response)

set_llm_judge(my_llm_judge)
```

### Q2: semantic_metrics / grounding_metrics 返回 null？

需要在请求时传入 `include_semantic=true` 或 `include_grounding=true`，且服务端已配置 LLM Judge。

### Q3: 如何进行版本对比？

```python
# 版本 v1.0
run_v1 = base_client.start_run(name="graph_query", metadata={"version_id": "v1.0"})

# 版本 v2.0（更换了搜索策略）
run_v2 = base_client.start_run(name="graph_query", metadata={"version_id": "v2.0"})

# 对比
diff = graph_client.get_graph_diff(run_v2.id, run_v1.id)
```

### Q4: path_exists=True 但 path_relevance_score 很低？

说明 GraphRAG 找到了一条连通路径，但路径方向偏离了 query。常见原因：
1. 起始节点选择错误（entity linking 阶段的问题）
2. 关系权重设置不合理，导致搜索走向了不相关方向
3. `max_hops` 设置过大，路径走偏后仍在继续扩展

### Q5: 如何解读版本对比指标？

**理想的版本升级**:
- `path_length_delta` 接近 0（推理深度稳定）
- `branch_explosion_delta` < 0（搜索效率提升）
- `connectivity_delta` > 0（图结构更紧凑）
- `new_nodes` 中节点与 query 相关性高

**需要警惕的版本升级**:
- `path_length_delta` 大幅增加：推理冗余增多
- `branch_explosion_delta` 大幅增加：搜索效率下降
- `connectivity_delta` < 0：图结构变得更发散

---

## 八、开发任务清单

### Phase 1: 数据库与上报接口
- [ ] 创建数据库表：graph_expand, graph_path, gold_path
- [ ] 实现上报接口：graph/expand, graph/path_selected, gold/path
- [ ] 复用 run, metric, answer_generated 表和接口

### Phase 2: 结构性指标（零成本）
- [ ] compute_path_exists
- [ ] compute_reasoning_hops
- [ ] compute_connectivity_score

### Phase 3: 路径质量指标
- [ ] compute_branch_explosion_ratio
- [ ] compute_irrelevant_branch_ratio（需要 embedding）
- [ ] compute_path_coverage（需要 gold_nodes）

### Phase 4: 语义与答案支撑指标（需要 LLM）
- [ ] compute_path_relevance_score
- [ ] compute_relation_chain_validity
- [ ] compute_answer_grounded_in_path_score
- [ ] compute_unsupported_claim_ratio

### Phase 5: 查询接口
- [ ] GET /api/v1/run/{run_id}/graph_metrics
- [ ] GET /api/v1/run/{run_id}/graph_diff

### Phase 6: SDK 与示例
- [ ] Python SDK（GraphClient）
- [ ] API 接入示例
- [ ] 版本对比示例

---

## 总结

TraceLens GraphRAG 是一个**专注于推理路径可观测性的 GraphRAG 评测平台**。核心价值：

✅ **结构健康检查**：path_exists, reasoning_hops, connectivity_score  
✅ **搜索效率评估**：branch_explosion_ratio, irrelevant_branch_ratio  
✅ **路径质量验证**：path_relevance_score, relation_chain_validity  
✅ **幻觉检测**：answer_grounded_in_path_score, unsupported_claim_ratio  
✅ **版本对比分析**：graph_diff 接口，追踪推理路径变化  
✅ **可选 gold data**：不强制要求标准答案  

> 让 GraphRAG 推理从 **黑盒推理 → 可观测推理 → 可优化推理**
