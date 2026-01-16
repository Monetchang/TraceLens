from uuid import UUID
from typing import Optional
from sqlalchemy.orm import Session
from tracelens.storage.repository import RunRepository, SpanRepository, EventRepository


def parse_langfuse_trace(data: dict, db: Session) -> UUID:
    """将 Langfuse 导出的 trace 转换为 TraceLens Run/Span"""
    run_repo = RunRepository(db)
    span_repo = SpanRepository(db)
    
    # 创建 Run
    run = run_repo.create(
        name=data.get("name", "langfuse_import"),
        metadata={"source": "langfuse", "original_id": data.get("id")}
    )
    
    # 解析 observations (spans/generations)
    observations = data.get("observations", [])
    parent_map = {}
    
    # 第一遍：创建所有 span
    for obs in observations:
        span = span_repo.create(
            run_id=run.id,
            name=obs.get("name", "unknown"),
            parent_span_id=None,
            input=obs.get("input", {}),
            metadata={"source": "langfuse", "type": obs.get("type")}
        )
        span_repo.end(span.id, output=obs.get("output", {}))
        parent_map[obs.get("id")] = span.id
    
    # 第二遍：设置 parent 关系
    for obs in observations:
        if obs.get("parentObservationId"):
            span_id = parent_map.get(obs.get("id"))
            parent_id = parent_map.get(obs.get("parentObservationId"))
            if span_id and parent_id:
                span = span_repo.get(span_id)
                if span:
                    span.parent_span_id = parent_id
                    span_repo.db.commit()
    
    return run.id

