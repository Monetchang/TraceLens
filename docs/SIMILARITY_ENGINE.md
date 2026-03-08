# TraceLens Similarity Engine 文档

## 概述

TraceLens 提供了三种可插拔的相似度计算模式，让开发者在**成本与精度之间**灵活选择：

1. **Lexical** - 基于词法的相似度（默认，零配置）
2. **Embedding** - 基于 embedding 的语义相似度（需要配置）
3. **LLM** - 基于 LLM 判断的相似度（最准确，成本最高）

## 设计理念

> **TraceLens 的核心不是"算一个分数"，而是让开发者在成本与精度之间，拥有连续、可对比、可解释的 RAG 评测能力。**

## 三种模式对比

| 模式 | 优点 | 缺点 | 适用场景 | 成本 |
|------|------|------|----------|------|
| **Lexical** | 零配置，快速，无外部依赖 | 语义理解有限 | 日常开发，快速评估 | 免费 |
| **Embedding** | 语义理解准确，响应快速 | 需要配置 embedding function | 生产环境，精确评估 | 低（$0.0001/1K tokens） |
| **LLM** | 最准确，可解释性强 | 成本高，速度慢 | Benchmark，关键决策 | 高（$0.01/1K tokens） |

---

## 一、Lexical 模式（默认）

### 特点

- ✅ **零配置**：无需任何外部依赖，开箱即用
- ✅ **快速**：本地计算，无网络请求
- ✅ **免费**：无任何成本
- ⚠️ **有限**：基于词法，语义理解有限

### 实现方式

基于 **TF-IDF + 余弦相似度**：

```python
from tracelens.similarity import get_similarity_engine

engine = get_similarity_engine("lexical")
similarity = engine.compute("What is RAG?", "RAG is a technique...")
print(similarity)  # 0.0 - 1.0
```

### 使用场景

- 日常开发和快速迭代
- 初步筛选和排序
- 不需要深度语义理解的场景

---

## 二、Embedding 模式

### 特点

- ✅ **语义准确**：捕捉文本的深层语义
- ✅ **响应快速**：向量计算，毫秒级响应
- ✅ **成本低**：embedding 成本约 $0.0001/1K tokens
- ⚠️ **需要配置**：需要配置 embedding function

### 配置方式

#### 方式 1：在服务端配置（推荐）

```python
# 在服务启动时配置
from tracelens.similarity import get_similarity_engine

# 使用 OpenAI embedding
def openai_embed(text: str):
    from openai import OpenAI
    client = OpenAI()
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

# 创建 engine 并配置
engine = get_similarity_engine("embedding", {
    "embedding_function": openai_embed
})

# 设置为默认 engine（可选）
from tracelens.similarity.factory import set_default_engine
set_default_engine(engine)
```

#### 方式 2：使用 Sentence Transformers（本地）

```python
from sentence_transformers import SentenceTransformer
from tracelens.similarity import get_similarity_engine

model = SentenceTransformer('all-MiniLM-L6-v2')

def local_embed(text: str):
    return model.encode(text)

engine = get_similarity_engine("embedding", {
    "embedding_function": local_embed
})
```

### 使用方式

```python
# API 调用
GET /api/v1/run/{run_id}/metrics?similarity_mode=embedding

# SDK 调用
metrics = rag_client.get_metrics(run_id, similarity_mode="embedding")
```

### Asymmetric Embedding（检索关联度优化）

默认的 Embedding 模式对 query 和 chunk 使用**相同**的编码方式（对称），衡量的是"语义相似度"。但 RAG 评估需要的是"检索关联度"——chunk 能否回答 query。部分 embedding 模型支持对 query 和 document 分别指定 `input_type`，可提升 query-chunk 关联度计算的准确性。

**配置方式**（环境变量）：

```bash
# 阿里云 text-embedding-v3 / Cohere embed-v3
EMBEDDING_INPUT_TYPE_QUERY=query
EMBEDDING_INPUT_TYPE_DOC=document
```

**支持 Asymmetric Embedding 的模型**：

| 模型 | `input_type` 参数名 | query 值 | doc 值 |
|------|---------------------|----------|--------|
| 阿里云百炼 `text-embedding-v3` | `input_type` | `query` | `document` |
| Cohere `embed-v3` | `input_type` | `search_query` | `search_document` |
| `BAAI/bge-m3`（Ollama/本地） | instruction 前缀 | 需自定义 function | 需自定义 function |
| OpenAI `text-embedding-3-*` | 不支持 | — | — |

**不支持** Asymmetric 的模型（如 OpenAI text-embedding-3）将使用对称模式，不设置 `EMBEDDING_INPUT_TYPE_*` 即可。

---

## 三、LLM 模式

### 特点

- ✅ **最准确**：LLM 能深度理解语义和上下文
- ✅ **可解释**：可返回判断理由（可选）
- ⚠️ **成本高**：约 $0.01/1K tokens
- ⚠️ **速度慢**：依赖 LLM API 响应速度

### 配置方式

```python
from tracelens.similarity import get_similarity_engine

# 使用 OpenAI LLM
def llm_client(prompt: str) -> str:
    from openai import OpenAI
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )
    return response.choices[0].message.content

engine = get_similarity_engine("llm", {
    "llm_client": llm_client
})
```

### Prompt 模板

LLM 模式使用两种 prompt 模板：

#### 1. Query ↔ Chunk 相似度

```
Please evaluate the semantic relevance between the query and the chunk on a scale of 0 to 1.

Query: {query}
Chunk: {chunk}

Return ONLY a number between 0.0 and 1.0.
Score:
```

#### 2. Chunk ↔ Answer 支撑度

```
Please evaluate how well the chunk supports or contributes to the answer on a scale of 0 to 1.

Chunk: {chunk}
Answer: {answer}

Return ONLY a number between 0.0 and 1.0.
Score:
```

### 使用方式

```python
# API 调用
GET /api/v1/run/{run_id}/metrics?similarity_mode=llm

# SDK 调用
metrics = rag_client.get_metrics(run_id, similarity_mode="llm")
```

---

## 四、使用建议

### 渐进式采用策略

```
阶段 1：开发阶段
  └─ 使用 Lexical 模式，快速迭代

阶段 2：测试阶段
  └─ 使用 Embedding 模式，精确评估

阶段 3：关键决策
  └─ 使用 LLM 模式，最终验证
```

### 成本优化

- **日常开发**：全部使用 Lexical（免费）
- **自动化测试**：使用 Embedding（低成本）
- **Benchmark**：使用 LLM（仅对关键 case）

### 混合使用

```python
# 先用 Lexical 快速筛选
metrics_lexical = rag_client.get_metrics(run_id, similarity_mode="lexical")

# 对异常 case 使用 Embedding 验证
if metrics_lexical['metrics']['some_metric'] < 0.5:
    metrics_embedding = rag_client.get_metrics(run_id, similarity_mode="embedding")
```

---

## 五、API 参数

### GET /api/v1/run/{run_id}/metrics

**查询参数**:
- `similarity_mode` (string): 相似度计算模式
  - `lexical` (默认)
  - `embedding`
  - `llm`
- `prev_run_id` (UUID, 可选): 上一版本 run_id

### GET /api/v1/run/{run_id}/retrieval_diff

**查询参数**:
- `prev_run_id` (UUID, 必填): 上一版本 run_id
- `similarity_mode` (string): 相似度计算模式（同上）

---

## 六、SDK 示例

### 基本使用

```python
from sdk.rag_client import RAGClient
from sdk.client import TraceLensClient

base_client = TraceLensClient("http://localhost:8000")
rag_client = RAGClient("http://localhost:8000")

# 使用 lexical 模式（默认）
metrics = rag_client.get_metrics(run_id, similarity_mode="lexical")

# 使用 embedding 模式
metrics = rag_client.get_metrics(run_id, similarity_mode="embedding")

# 使用 llm 模式
metrics = rag_client.get_metrics(run_id, similarity_mode="llm")
```

### 版本对比

```python
# 对比两个版本（使用 lexical）
diff = rag_client.get_retrieval_diff(
    run_v2_id,
    run_v1_id,
    similarity_mode="lexical"
)

print(f"new_chunks_query_similarity: {diff['new_chunks_query_similarity']}")
print(f"dropped_chunks_query_similarity: {diff['dropped_chunks_query_similarity']}")
```

---

## 七、常见问题

### Q1: 如何选择相似度模式？

**建议**：
1. 开发阶段 → Lexical
2. 测试阶段 → Embedding
3. Benchmark → LLM

### Q2: Embedding 模式返回 None 怎么办？

检查是否配置了 embedding function：

```python
from tracelens.similarity import get_similarity_engine

engine = get_similarity_engine("embedding", {
    "embedding_function": your_embed_function
})
```

### Q3: 三种模式的结果可以对比吗？

可以！这正是 TraceLens 的设计目标：

```python
# 对比三种模式
for mode in ["lexical", "embedding", "llm"]:
    metrics = rag_client.get_metrics(run_id, similarity_mode=mode)
    print(f"{mode}: {metrics['extended_metrics']}")
```

### Q4: 如何优化成本？

- 对所有 run 使用 Lexical
- 只对异常 case 使用 Embedding
- 仅对关键决策使用 LLM

---

## 八、最佳实践

### 1. 渐进式验证

```python
# Step 1: Lexical 快速评估
metrics_lex = get_metrics(run_id, "lexical")

# Step 2: 异常 case 用 Embedding 验证
if needs_verification(metrics_lex):
    metrics_emb = get_metrics(run_id, "embedding")
    
# Step 3: 关键 case 用 LLM 最终确认
if is_critical(metrics_emb):
    metrics_llm = get_metrics(run_id, "llm")
```

### 2. 批量评估

```python
# 对多个 run 批量评估（使用 lexical）
for run_id in run_ids:
    metrics = rag_client.get_metrics(run_id, similarity_mode="lexical")
    save_metrics(run_id, metrics)
```

### 3. A/B 测试

```python
# 对比两个版本（不同相似度模式）
diff_lex = get_retrieval_diff(v2, v1, "lexical")
diff_emb = get_retrieval_diff(v2, v1, "embedding")

# 对比结果
compare_diff(diff_lex, diff_emb)
```

---

## 总结

TraceLens Similarity Engine 提供了**三层相似度计算方案**：

- ✅ **Lexical**：零配置，快速，免费
- ⚡ **Embedding**：语义准确，成本低
- 🎯 **LLM**：最准确，可解释

**核心价值**：让开发者在成本与精度之间灵活选择，实现连续、可对比、可解释的 RAG 评测。

