from uuid import UUID
from typing import Optional
from sqlalchemy.orm import Session
from tracelens.storage.repository import RunRepository, SpanRepository, EventRepository


def parse_langsmith_run(data: dict, db: Session) -> UUID:
    """将 LangSmith 导出的 run 转换为 TraceLens Run/Span"""
    run_repo = RunRepository(db)
    span_repo = SpanRepository(db)
    
    # 创建 Run
    run = run_repo.create(
        name=data.get("name", "langsmith_import"),
        metadata={"source": "langsmith", "original_id": data.get("id")}
    )
    
    # 解析 spans
    if "child_runs" in data:
        _parse_spans(data["child_runs"], run.id, None, span_repo)
    
    return run.id


def _parse_spans(spans: list, run_id: UUID, parent_id: Optional[UUID], repo: SpanRepository):
    for span_data in spans:
        span = repo.create(
            run_id=run_id,
            name=span_data.get("name", "unknown"),
            parent_span_id=parent_id,
            input=span_data.get("inputs", {}),
            metadata={"source": "langsmith", "run_type": span_data.get("run_type")}
        )
        repo.end(span.id, output=span_data.get("outputs", {}))
        
        if "child_runs" in span_data:
            _parse_spans(span_data["child_runs"], run_id, span.id, repo)

