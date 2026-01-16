# TraceLens RAG MVP 指标文档（最终版）

## 核心设计理念

TraceLens 专注于 **检索质量评估** 和 **版本变化分析**，不试图替代 RAGAS 的完整评测体系，而是回答：

> **当你更换切分、向量模型或向量数据库时，检索能力到底发生了什么变化？**

## 指标分类

TraceLens RAG MVP 提供两类指标：

1. **基础指标**：`new_chunks_ratio`, `rank_deltas`（版本对比）
2. **扩展指标**（需要 embedding）：
   - `topK_chunk_query_similarity`（检索质量）
   - `prompt_chunk_answer_similarity`（chunk 对 answer 的贡献）
   - `semantic_recall_vs_gold`（召回质量，可选）
   - `new_chunks_query_similarity`（新增 chunks 质量）
   - `dropped_chunks_query_similarity`（丢失 chunks 质量）

---

## 一、核心指标详解

### 1. topK_chunk_query_similarity

**指标名称**: topK_chunk_query_similarity（Top-K prompt chunks 与 query 的相似度）

**需要信息**:
- query 文本（通过 `retrieval_completed` 上报）
- 前 K 个 prompt_chunks 的 content
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
- 评估 prompt 中最关键 chunks 与 query 的语义贴合度
- 无 gold data 时的质量参考指标
- 对比不同 embedding 模型的效果
- 监控检索质量退化

**指导价值**:
- **高值（>0.7）**: prompt chunks 与 query 高度相关，检索质量好
- **低值（<0.5）**: prompt chunks 与 query 相关性低，可能需要优化检索策略

---

### 2. prompt_chunk_answer_similarity

**指标名称**: prompt_chunk_answer_similarity（prompt chunks 与 answer 的相似度）

**需要信息**:
- prompt_chunks（通过 `prompt_built` 上报）
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
- 衡量 prompt chunks 对答案的实际贡献
- 指导 prompt 或 chunk 策略优化
- 发现检索到但未有效使用的 chunks

**指导价值**:
- **高值（>0.6）**: prompt chunks 对 answer 有实际贡献
- **低值（<0.4）**: prompt chunks 对 answer 贡献低，可能需要优化 chunk 选择或 prompt 构建策略

---

### 3. semantic_recall_vs_gold（可选）

**指标名称**: semantic_recall_vs_gold（相对于 gold chunks 的语义召回率）

**需要信息**:
- retrieved_chunks（通过 `retrieval_completed` 上报）
- gold_chunk_ids（通过 `gold_chunks` 事件上报）

**计算方式**:
```python
# 简化版本：只检查 chunk_id 是否匹配
retrieved_chunk_ids = {c.chunk_id for c in retrieved_chunks}
gold_chunk_ids = {g.chunk_id for g in gold_chunks}
hit_count = len(retrieved_chunk_ids & gold_chunk_ids)
semantic_recall = hit_count / len(gold_chunk_ids) if gold_chunk_ids else 0.0
```

**使用场景**:
- 评估检索系统对 gold chunks 的召回能力
- Benchmark 评测
- 验证检索系统的准确性

**注意**：当前实现为简化版本，只检查 chunk_id 是否匹配。如需语义相似度匹配（非严格 ID 匹配），需要扩展实现。

---

### 4. rank_delta（版本对比）

**指标名称**: rank_delta（排名变化）

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

**指标名称**: new_chunks_ratio（新增 chunks 比例）

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

**指标名称**: new_chunks_query_similarity（新增 chunks 与 query 的相似度）

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
- 评估新增 chunks 与 query 的相关度
- **高值表示新版本改进效果好**

**指导价值**:
- **高值（>0.6）**: 新增 chunks 与 query 高度相关，新版本改进有效
- **低值（<0.4）**: 新增 chunks 与 query 相关性低，新版本改进可能无效或引入噪音

---

### 7. dropped_chunks_query_similarity（版本对比 + embedding）

**指标名称**: dropped_chunks_query_similarity（丢弃 chunks 与 query 的相似度）

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
- 评估丢弃 chunks 与 query 的相关度
- **高值表示新版本改动可能影响质量**

**指导价值**:
- **高值（>0.6）**: 丢弃的 chunks 与 query 高度相关，新版本可能丢失了重要信息
- **低值（<0.4）**: 丢弃的 chunks 与 query 相关性低，新版本改进有效

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

上报 prompt 构建事件

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
- `prev_run_id` (UUID, 可选): 上一版本的 run_id，用于计算版本对比指标
- `include_extended` (bool, 可选): 是否包含扩展指标，默认 `false`

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
        "semantic_recall_vs_gold": 0.8,
        "new_chunks_query_similarity": 0.72,
        "dropped_chunks_query_similarity": 0.45
    }
}
```

#### GET /api/v1/run/{run_id}/retrieval_diff

获取两个 run 的检索差异（版本对比）

**查询参数**:
- `prev_run_id` (UUID, 必填): 上一版本的 run_id
- `include_extended` (bool, 可选): 是否包含扩展指标，默认 `false`

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
    
    # 1. topK_chunk_query_similarity
    query_emb = embed(query)
    topK_chunks = prompt_chunks[:K]
    topK_embs = [embed(c.content) for c in topK_chunks]
    topK_sim = mean([cosine_similarity(query_emb, c_emb) for c_emb in topK_embs])
    save_metric(run_id, "topK_chunk_query_similarity", topK_sim)
    
    # 2. prompt_chunk_answer_similarity
    answer_emb = embed(answer)
    prompt_embs = [embed(c.content) for c in prompt_chunks]
    prompt_answer_sim = mean([cosine_similarity(c_emb, answer_emb) for c_emb in prompt_embs])
    save_metric(run_id, "prompt_chunk_answer_similarity", prompt_answer_sim)

    # 3. semantic_recall_vs_gold (可选)
    gold = get_gold_chunks(run_id)
    if gold:
        retrieved = get_retrieved_chunks(run_id)
        hit_count = len(set(retrieved) & set(gold))
        semantic_recall = hit_count / len(gold)
        save_metric(run_id, "semantic_recall_vs_gold", semantic_recall)

    # 4. 版本对比的语义相似度指标
    if prev_run_id:
        prev_retrieved = get_retrieved_chunks(prev_run_id)
        new_chunks = set(current) - set(prev_retrieved)
        dropped_chunks = set(prev_retrieved) - set(current)

        # 新增 chunks 与 query 相似度
        new_chunks_query_sim = mean([cosine_similarity(embed(c.content), query_emb) for c in new_chunks]) if new_chunks else 0
        save_metric(run_id, "new_chunks_query_similarity", new_chunks_query_sim)

        # 丢弃 chunks 与 query 相似度
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
- [x] compute_semantic_recall_vs_gold (简化版本)
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
