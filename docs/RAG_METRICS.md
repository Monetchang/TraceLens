# TraceLens RAG MVP 指标文档

## 核心设计理念

TraceLens 专注于 **检索质量评估** 和 **版本变化分析**，不试图替代 RAGAS 的完整评测体系，而是回答：

> **当你更换切分、向量模型或向量数据库时，检索能力到底发生了什么变化？**

## 名词说明

- **retrieved_chunks**：检索阶段返回的全部候选 chunks，通过 `retrieval_completed` 上报。
- **prompt_chunks**：从 retrieved_chunks 中筛选后、实际放入 LLM prompt 的 chunks，通过 `prompt_built` 上报。是 retrieved_chunks 的子集，数量通常更少。
- **topK chunks**：prompt_chunks 中排名前 K 个（默认 K=5）。只取头部用于评估最关键 chunks 的质量，避免尾部 chunks 稀释结果。
- **gold_chunks**：人工标注的"正确应被检索到的"chunks，通过 `gold_chunks` 事件上报（可选）。

## 指标分类

TraceLens RAG MVP 提供两类指标：

1. **基础指标**（需要 `prev_run_id` 做版本对比）：`new_chunks_ratio`, `rank_deltas`
2. **扩展指标**（需要 embedding 或 LLM）：
   - 单 run 指标（每次 run 独立计算）：
     - `topK_chunk_query_similarity`：prompt_chunks 前 K 个与 query 的关联度，衡量检索头部质量
     - `prompt_chunk_answer_similarity`：所有 prompt_chunks 对 answer 的支撑度
     - `exact_recall_vs_gold_chunks`：retrieved_chunks 对 gold chunks 的精确命中率（可选）
   - 版本对比指标（需要 `prev_run_id`，对比两个版本 retrieved_chunks 的差异）：
     - `new_chunks_query_similarity`：新增 retrieved chunks 与 query 的关联度
     - `dropped_chunks_query_similarity`：丢失 retrieved chunks 与 query 的关联度

---

## 一、核心指标详解

### 1. topK_chunk_query_similarity

**指标名称**: topK_chunk_query_similarity（prompt_chunks 前 K 个与 query 的关联度）

> prompt_chunks 是实际进入 LLM prompt 的 chunks（检索候选集的子集），取前 K 个是因为排名靠前的 chunks 对 LLM 回答影响最大。此指标衡量"最关键的 chunks 是否真的和 query 相关"。

**需要信息**:
- query 文本（通过 `retrieval_completed` 上报）
- 前 K 个 prompt_chunks 的 content（K 默认为 5）
- embedding 函数（服务端配置）

**计算方式**:
```python
query_emb = embed(query)
topK_chunks = prompt_chunks[:K]  # 前 K 个 prompt chunks
topK_embs = [embed(chunk.content) for chunk in topK_chunks]
similarities = [cosine_similarity(query_emb, chunk_emb) for chunk_emb in topK_embs]
topK_similarity = mean(similarities) if similarities else 0.0
```

**使用场景**:
- 无 gold data 时评估检索质量的参考指标
- 对比不同 embedding 模型或切分策略的效果
- 监控检索质量退化

**指导价值**:
- **高值（>0.7）**: 前 K 个 prompt chunks 与 query 高度相关，检索质量好
- **低值（<0.5）**: 前 K 个 prompt chunks 与 query 相关性低，检索或排序策略可能需要优化

---

### 2. prompt_chunk_answer_similarity

**指标名称**: prompt_chunk_answer_similarity（prompt_chunks 对 answer 的支撑度）

> 不同于 topK_chunk_query_similarity 只取前 K 个，此指标对**所有** prompt_chunks 计算，评估它们整体对最终 answer 的贡献。高值说明 LLM 确实在利用 prompt 中的 chunks 来生成回答；低值说明 chunks 和答案内容关联弱，可能检索到了不相关内容或 LLM 忽视了提供的上下文。

**需要信息**:
- 所有 prompt_chunks（通过 `prompt_built` 上报）
- answer 文本（通过 `answer_generated` 上报）
- embedding 函数（服务端配置）

**计算方式**:
```python
answer_emb = embed(answer)
prompt_embs = [embed(chunk.content) for chunk in prompt_chunks]
similarities = [cosine_similarity(chunk_emb, answer_emb) for chunk_emb in prompt_embs]
prompt_answer_similarity = mean(similarities) if similarities else 0.0
```

**使用场景**:
- 衡量 prompt_chunks 对答案的实际贡献
- 指导 prompt 构建或 chunk 筛选策略优化

**指导价值**:
- **高值（>0.6）**: prompt_chunks 对 answer 有实际贡献
- **低值（<0.4）**: prompt_chunks 对 answer 贡献低，可能需要优化 chunk 选择策略或检查 prompt 构建逻辑

---

### 3. exact_recall_vs_gold_chunks（可选）

**指标名称**: exact_recall_vs_gold_chunks（retrieved_chunks 对 gold chunks 的 chunk_id 精确命中率）

> **注意**：此指标是 chunk_id 的精确匹配，不做语义比较。即使内容高度相关但 chunk_id 不同，也不算命中。需要提前通过 `gold_chunks` 事件上报标注数据。

**需要信息**:
- retrieved_chunks（通过 `retrieval_completed` 上报）
- gold_chunk_ids（通过 `gold_chunks` 事件上报）

**计算方式**:
```python
# 只检查 chunk_id 是否匹配（非语义相似度）
retrieved_chunk_ids = {c.chunk_id for c in retrieved_chunks}
gold_chunk_ids = {g.chunk_id for g in gold_chunks}
hit_count = len(retrieved_chunk_ids & gold_chunk_ids)
exact_recall = hit_count / len(gold_chunk_ids) if gold_chunk_ids else 0.0
```

**使用场景**:
- 评估检索系统对 gold chunks 的精确召回能力
- Benchmark 评测
- 验证检索系统的准确性

**注意**：此指标为 chunk_id 精确命中率，不做语义匹配。同一内容若 chunk_id 不同则不计入命中。

---

### 4. rank_delta（版本对比）

**指标名称**: rank_delta（排名变化）

> **前提**：需要传入 `prev_run_id`。只对两个版本中都出现的 chunk_id 计算排名变化，新增或丢失的 chunks 不纳入此指标。

**需要信息**:
- 当前 run 的 retrieved_chunks（按 score 排序）
- 上一版本 run 的 retrieved_chunks（按 score 排序）

**计算方式**:
```python
对于同时在两个版本中出现的 chunk_id:
rank_delta = rank_in_current - rank_in_prev
```
- `rank_delta > 0`: 排名下降（变差）
- `rank_delta < 0`: 排名上升（变好）
- `rank_delta = 0`: 排名不变

**使用场景**:
- 评估检索排序的变化
- 评估 embedding 模型升级对排序的影响
- 发现哪些 chunks 排名显著变化

---

### 5. new_chunks_ratio（版本对比）

**指标名称**: new_chunks_ratio（新增 retrieved chunks 占当前版本的比例）

> **前提**：需要传入 `prev_run_id`。统计当前版本 retrieved_chunks 中有多少是上一版本没有的，反映版本切换后检索结果的"变化幅度"。

**需要信息**:
- 当前 run 的 retrieved_chunks
- 上一版本 run 的 retrieved_chunks

**计算方式**:
```python
new_chunks_ratio = len(set(current_chunks) - set(prev_chunks)) / len(current_chunks)
```

**使用场景**:
- 了解新增信息量
- 评估版本切换后新增的检索结果
- 评估切分策略或 embedding 模型变化的影响

---

### 6. new_chunks_query_similarity（版本对比 + embedding）

**指标名称**: new_chunks_query_similarity（新增 retrieved chunks 与 query 的关联度）

> **前提**：需要传入 `prev_run_id`。计算对象是当前版本相比上一版本**新增**的 retrieved chunks（不是 prompt_chunks），评估新引入的 chunks 是否与 query 相关。与 `new_chunks_ratio` 配合使用：ratio 说明变化多少，此指标说明变化是否有价值。

**需要信息**:
- 新增 chunks embeddings
- query embedding

**计算方式**:
```python
new_chunks = set(current_chunks) - set(prev_chunks)
new_chunks_embs = [embed(c.content) for c in new_chunks]
query_emb = embed(query)
similarities = [cosine_similarity(c_emb, query_emb) for c_emb in new_chunks_embs]
new_chunks_query_similarity = mean(similarities) if similarities else 0.0
```

**使用场景**:
- 评估版本升级后新引入的 retrieved chunks 是否与 query 相关
- 与 `dropped_chunks_query_similarity` 配合判断版本升级是否有效

**指导价值**:
- **高值（>0.6）**: 新增 chunks 与 query 高度相关，版本升级引入了有效内容
- **低值（<0.4）**: 新增 chunks 与 query 相关性低，版本升级可能引入了噪音

---

### 7. dropped_chunks_query_similarity（版本对比 + embedding）

**指标名称**: dropped_chunks_query_similarity（丢失 retrieved chunks 与 query 的关联度）

> **前提**：需要传入 `prev_run_id`。计算对象是上一版本有、当前版本没有的 retrieved chunks，评估被丢弃的内容是否原本与 query 相关。此指标是版本升级的"代价检测"——高值意味着丢掉了重要内容。

**需要信息**:
- 丢弃的 chunks embeddings
- query embedding

**计算方式**:
```python
dropped_chunks = set(prev_chunks) - set(current_chunks)
dropped_chunks_embs = [embed(c.content) for c in dropped_chunks]
query_emb = embed(query)
similarities = [cosine_similarity(c_emb, query_emb) for c_emb in dropped_chunks_embs]
dropped_chunks_query_similarity = mean(similarities) if similarities else 0.0
```

**使用场景**:
- 检测版本升级是否丢失了重要的检索内容
- 与 `new_chunks_query_similarity` 配合综合判断版本升级效果

**指导价值**:
- **高值（>0.6）**: 丢弃的 chunks 与 query 高度相关，新版本可能丢失了重要信息，需关注
- **低值（<0.4）**: 丢弃的 chunks 与 query 相关性低，说明丢弃的是噪音，版本升级有效

---

## 二、数据上报

### 数据库表结构

#### 1. run 表
```sql
CREATE TABLE run (
    id UUID PRIMARY KEY,
    name VARCHAR,
    query TEXT,
    answer TEXT,  -- 新增
    version_id VARCHAR,
    status VARCHAR,
    metadata JSONB,
    started_at TIMESTAMP,
    ended_at TIMESTAMP
);
```

#### 2. retrieved_chunk 表
```sql
CREATE TABLE retrieved_chunk (
    run_id UUID REFERENCES run(id),
    chunk_id VARCHAR,
    content TEXT,
    score FLOAT,
    PRIMARY KEY (run_id, chunk_id)
);
```

#### 3. prompt_chunk 表
```sql
CREATE TABLE prompt_chunk (
    run_id UUID REFERENCES run(id),
    chunk_id VARCHAR,
    PRIMARY KEY (run_id, chunk_id)
);
```

#### 4. gold_chunk 表（可选）
```sql
CREATE TABLE gold_chunk (
    run_id UUID REFERENCES run(id),
    chunk_id VARCHAR,
    PRIMARY KEY (run_id, chunk_id)
);
```

#### 5. metric 表
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

## 三、API 接口

### 上报接口

#### POST /api/v1/retrieval/completed

上报检索完成事件

```json
{
    "run_id": "uuid",
    "query": "What is RAG?",
    "retrieved_chunks": [
        {"chunk_id": "c1", "score": 0.95, "content": "..."},
        {"chunk_id": "c2", "score": 0.87, "content": "..."}
    ]
}
```

#### POST /api/v1/prompt/built

上报 prompt 构建事件（prompt_chunks 是 retrieved_chunks 的子集，即实际放入 LLM prompt 的 chunks）

```json
{
    "run_id": "uuid",
    "prompt_chunks": ["chunk_id1", "chunk_id2"]
}
```

#### POST /api/v1/answer/generated

上报 answer 生成事件

```json
{
    "run_id": "uuid",
    "answer": "RAG is a technique..."
}
```

#### POST /api/v1/gold/chunks

上报 gold chunks（可选）

```json
{
    "run_id": "uuid",
    "gold_chunk_ids": ["chunk_id1", "chunk_id2"]
}
```

#### POST /api/v1/run/finished

结束 run

```json
{
    "run_id": "uuid",
    "status": "success"
}
```

---

### 查询接口

#### GET /api/v1/run/{run_id}/metrics

获取 run 的基础指标

**查询参数**:
- `prev_run_id` (UUID, 可选): 上一版本的 run_id，用于计算版本对比指标（`new_chunks_ratio`, `rank_deltas`）
- `include_extended` (bool, 可选): 是否包含扩展指标，默认 `false`。需要配置 embedding 函数

**响应**:
```json
{
    "run_id": "uuid",
    "metrics": {
        "new_chunks_ratio": 0.2
    },
    "extended_metrics": null
}
```

如果 `include_extended=true` 且配置了 embedding 函数：
```json
{
    "run_id": "uuid",
    "metrics": {
        "new_chunks_ratio": 0.2
    },
    "extended_metrics": {
        "topK_chunk_query_similarity": 0.85,
        "prompt_chunk_answer_similarity": 0.78,
        "exact_recall_vs_gold_chunks": 0.8,
        "new_chunks_query_similarity": null,
        "dropped_chunks_query_similarity": null
    }
}
```

> `new_chunks_query_similarity` 和 `dropped_chunks_query_similarity` 需要 `prev_run_id` 才会有值，单独查询时返回 `null`。

#### GET /api/v1/run/{run_id}/retrieval_diff

获取两个 run 的检索差异（版本对比）。`new_chunks_query_similarity` 和 `dropped_chunks_query_similarity` 仅在此接口（传入 `prev_run_id`）时计算。

**查询参数**:
- `prev_run_id` (UUID, 必填): 上一版本的 run_id
- `include_extended` (bool, 可选): 是否包含语义扩展指标，默认 `false`

**响应**:
```json
{
    "run_id": "uuid",
    "prev_run_id": "uuid",
    "new_chunks_ratio": 0.2,
    "rank_deltas": {
        "chunk_001": -1,
        "chunk_002": 2,
        "chunk_003": 0
    },
    "new_chunks_query_similarity": 0.72,
    "dropped_chunks_query_similarity": 0.45
}
```

**rank_deltas 说明**:
- `rank_delta > 0`: 排名下降（变差）
- `rank_delta < 0`: 排名上升（变好）
- `rank_delta = 0`: 排名不变
- `rank_deltas` 会持久化到 `metrics.value_json`，可复用与审计

---

## 四、使用流程

1. **创建 run**
   ```python
   POST /api/v1/run/start
   {"name": "query", "metadata": {"version_id": "v1.0"}}
   ```

2. **上报检索结果**
   ```python
   POST /api/v1/retrieval/completed
   {"run_id": "...", "query": "...", "retrieved_chunks": [...]}
   ```

3. **上报 prompt chunks**
   ```python
   POST /api/v1/prompt/built
   {"run_id": "...", "prompt_chunks": [...]}
   ```

4. **上报 answer**
   ```python
   POST /api/v1/answer/generated
   {"run_id": "...", "answer": "..."}
   ```

5. **上报 gold chunks（可选）**
   ```python
   POST /api/v1/gold/chunks
   {"run_id": "...", "gold_chunk_ids": [...]}
   ```

6. **结束 run**
   ```python
   POST /api/v1/run/finished
   {"run_id": "...", "status": "success"}
   ```

7. **查询指标**
   ```python
   # 查询基础指标
   GET /api/v1/run/{run_id}/metrics
   
   # 查询基础指标 + 扩展指标
   GET /api/v1/run/{run_id}/metrics?include_extended=true
   
   # 查询版本对比指标
   GET /api/v1/run/{run_id}/retrieval_diff?prev_run_id={prev_run_id}
   
   # 查询版本对比指标 + 扩展指标
   GET /api/v1/run/{run_id}/retrieval_diff?prev_run_id={prev_run_id}&include_extended=true
   ```

---

## 五、SDK 使用示例

### Python SDK 示例

```python
from sdk.rag_client import RAGClient
from sdk.client import TraceLensClient

# 初始化客户端
base_client = TraceLensClient("http://localhost:8000")
rag_client = RAGClient("http://localhost:8000")

# 1. 创建 run
run = base_client.start_run(
    name="rag_query",
    metadata={"version_id": "v1.0"}
)

# 2. 上报检索结果
rag_client.retrieval_completed(
    run_id=run.id,
    query="What is RAG?",
    retrieved_chunks=[
        {"chunk_id": "c1", "score": 0.95, "content": "..."},
        {"chunk_id": "c2", "score": 0.87, "content": "..."}
    ]
)

# 3. 上报 prompt chunks
rag_client.prompt_built(
    run_id=run.id,
    prompt_chunks=["c1", "c2"]
)

# 4. 上报 answer
rag_client.answer_generated(run.id, "RAG is a technique...")

# 5. 上报 gold chunks（可选）
rag_client.gold_chunks(run.id, ["c1", "c2"])

# 6. 结束 run
rag_client.run_finished(run.id, "success")

# 7. 查询指标
metrics = rag_client.get_metrics(run.id, include_extended=True)
print(metrics['metrics'])
print(metrics['extended_metrics'])

# 8. 版本对比（如果有上一版本）
diff = rag_client.get_retrieval_diff(run.id, prev_run_id, include_extended=True)
print(diff)
```

---

## 六、指标计算伪代码

### 基础指标计算

```python
def compute_metrics(run_id, prev_run_id=None):
    # 版本对比指标
    if prev_run_id:
        # 1. new_chunks_ratio
        current = get_retrieved_chunks(run_id)
        prev = get_retrieved_chunks(prev_run_id)
        new_count = len(set(current) - set(prev))
        new_chunks_ratio = new_count / len(current) if current else 0.0
        save_metric(run_id, "new_chunks_ratio", new_chunks_ratio)
        
        # 2. rank_delta
        rank_delta = compute_rank_delta(prev, current)
        save_metric(run_id, "rank_delta", rank_delta)
```

### 扩展指标计算（需要 embedding）

```python
def compute_extended_metrics(run_id, prev_run_id=None):
    # 读取数据
    query = get_query(run_id)
    answer = get_answer(run_id)
    prompt_chunks = get_prompt_chunks(run_id)
    
    # 1. topK_chunk_query_similarity（基于 prompt_chunks 前 K 个）
    query_emb = embed(query)
    topK_chunks = prompt_chunks[:K]  # prompt_chunks 是 retrieved_chunks 的子集
    topK_embs = [embed(c.content) for c in topK_chunks]
    topK_sim = mean([cosine_similarity(query_emb, c_emb) for c_emb in topK_embs])
    save_metric(run_id, "topK_chunk_query_similarity", topK_sim)
    
    # 2. prompt_chunk_answer_similarity（基于全部 prompt_chunks）
    answer_emb = embed(answer)
    prompt_embs = [embed(c.content) for c in prompt_chunks]
    prompt_answer_sim = mean([cosine_similarity(c_emb, answer_emb) for c_emb in prompt_embs])
    save_metric(run_id, "prompt_chunk_answer_similarity", prompt_answer_sim)

    # 3. exact_recall_vs_gold_chunks (可选)
    gold = get_gold_chunks(run_id)
    if gold:
        retrieved = get_retrieved_chunks(run_id)
        hit_count = len(set(retrieved) & set(gold))
        exact_recall = hit_count / len(gold)
        save_metric(run_id, "exact_recall_vs_gold_chunks", exact_recall)

    # 4. 版本对比的语义关联度指标（需要 prev_run_id）
    if prev_run_id:
        prev_retrieved = get_retrieved_chunks(prev_run_id)
        new_chunks = set(current) - set(prev_retrieved)    # 当前有、上一版没有
        dropped_chunks = set(prev_retrieved) - set(current)  # 上一版有、当前没有

        # 新增 retrieved chunks 与 query 关联度
        new_chunks_query_sim = mean([cosine_similarity(embed(c.content), query_emb) for c in new_chunks]) if new_chunks else 0
        save_metric(run_id, "new_chunks_query_similarity", new_chunks_query_sim)

        # 丢失 retrieved chunks 与 query 关联度
        dropped_chunks_query_sim = mean([cosine_similarity(embed(c.content), query_emb) for c in dropped_chunks]) if dropped_chunks else 0
        save_metric(run_id, "dropped_chunks_query_similarity", dropped_chunks_query_sim)
```

---

## 七、常见问题

### Q1: 如何配置 embedding 函数？

扩展指标需要 embedding 函数。在服务端启动时配置：

```python
from tracelens.core.embedding_utils import set_embedding_function

def my_embed_function(text: str) -> np.ndarray:
    # 使用你的 embedding 模型
    # 例如: OpenAI, Sentence-BERT, etc.
    return model.encode(text)

set_embedding_function(my_embed_function)
```

### Q2: 扩展指标为什么返回 None？

扩展指标需要配置 embedding 函数。如果没有配置，扩展指标将返回 `None`。

### Q3: 如何进行版本对比？

在 run 的 metadata 中设置 `version_id`，然后使用 `retrieval_diff` 接口对比两个 run：

```python
# 版本 v1.0
run_v1 = client.start_run(name="query", metadata={"version_id": "v1.0"})

# 版本 v2.0
run_v2 = client.start_run(name="query", metadata={"version_id": "v2.0"})

# 对比
diff = rag_client.get_retrieval_diff(run_v2.id, run_v1.id, include_extended=True)
```

### Q4: 为什么移除了 unused_chunks_count？

`unused_chunks_count` 依赖 `chunk_used` 事件标记，但在实际使用中：
1. 开发者很少主动标记 `chunk_used`
2. 没有标记时，所有 chunks 都会被算作"未使用"，指标失去意义
3. 新增的 `prompt_chunk_answer_similarity` 更能反映 chunks 对 answer 的实际贡献

### Q5: 如何解读版本对比指标？

**理想的版本升级**:
- `new_chunks_ratio` 适中（10-30%）
- `new_chunks_query_similarity` 高（>0.6）
- `dropped_chunks_query_similarity` 低（<0.4）
- `rank_delta` 平均值接近 0

**需要警惕的版本升级**:
- `new_chunks_query_similarity` 低（<0.4）：新增 chunks 质量差
- `dropped_chunks_query_similarity` 高（>0.6）：丢失了重要信息
- `rank_delta` 平均值大幅上升：排序质量下降

---

## 八、开发任务清单

### Phase 1: 数据库与上报接口（已完成）
- [x] 创建数据库表：run (添加 answer 字段), retrieved_chunk, prompt_chunk, gold_chunk, metric
- [x] 移除 prompt_chunk.used_in_answer 字段
- [x] 实现上报接口：retrieval_completed, prompt_built, answer_generated, gold_chunks, run_finished

### Phase 2: 基础指标（已完成）
- [x] compute_new_chunks_ratio
- [x] compute_rank_deltas
- [x] 移除 unused_chunks_count

### Phase 3: 扩展指标（已完成）
- [x] compute_topK_chunk_query_similarity
- [x] compute_prompt_chunk_answer_similarity
- [x] compute_semantic_recall_vs_gold → exact_recall_vs_gold_chunks (chunk_id 精确命中)
- [x] compute_new_chunks_query_similarity
- [x] compute_dropped_chunks_query_similarity

### Phase 4: 查询接口（已完成）
- [x] GET /api/v1/run/{run_id}/metrics
- [x] GET /api/v1/run/{run_id}/retrieval_diff

### Phase 5: SDK 与示例（已完成）
- [x] Python SDK
- [x] API 接入示例
- [x] SDK 接入示例
- [x] 版本对比示例

---

## 总结

TraceLens RAG MVP 是一个**轻量级、专注于检索分析的 RAG 评测平台**。核心价值：

✅ **检索质量评估**：topK_chunk_query_similarity, prompt_chunk_answer_similarity  
✅ **版本对比分析**：rank_delta, new_chunks_ratio, new/dropped_chunks_query_similarity  
✅ **可选 gold data**：不强制要求标准答案  
✅ **易于集成**：SDK + API 双接入方式  

**去掉冗余指标，增加与答案/版本相关度指标，保留开发者最关心的核心信息。**
