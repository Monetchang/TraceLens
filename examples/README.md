# TraceLens 示例

| 示例 | 说明 |
|------|------|
| [rag_sdk_example.py](rag_sdk_example.py) | 单 Run RAG 评测（SDK） |
| [rag_api_example.py](rag_api_example.py) | 单 Run RAG 评测（API） |
| [evaluation_example.py](evaluation_example.py) | RAG 批量评测 |
| [evaluation_comparison_example.py](evaluation_comparison_example.py) | RAG 版本对比 |
| [graph_evaluation_example.py](graph_evaluation_example.py) | GraphRAG 批量评测 |
| [graph_evaluation_comparison_example.py](graph_evaluation_comparison_example.py) | GraphRAG 版本对比 |
| [similarity_modes_example.py](similarity_modes_example.py) | Lexical / Embedding / LLM 模式 |

运行前需启动服务：`uvicorn tracelens.main:app --reload`

