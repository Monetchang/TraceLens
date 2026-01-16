from uuid import UUID
from dataclasses import dataclass
from sqlalchemy.orm import Session
from tracelens.storage.repository import EventRepository, SpanRepository


@dataclass
class ChunkAttribution:
    chunk_id: str
    retrieved: bool
    used: bool
    retrieval_score: float | None
    retrieval_span_id: str | None
    answer_span_id: str | None


def compute_chunk_attribution(run_id: UUID, db: Session) -> list[ChunkAttribution]:
    """
    从 events 和 spans 计算 chunk attribution
    
    规则:
    - chunk_retrieved event: 标记为 retrieved
    - chunk_used event: 标记为 used
    - retrieval span output 中的 chunks: 标记为 retrieved
    - answer span 关联的 chunk_used events: 标记为 used
    """
    event_repo = EventRepository(db)
    span_repo = SpanRepository(db)
    
    events = event_repo.get_by_run(run_id)
    spans = span_repo.get_by_run(run_id)
    
    chunk_map: dict[str, ChunkAttribution] = {}
    
    # 从 events 收集
    for event in events:
        chunk_id = event.data.get("chunk_id")
        if not chunk_id:
            continue
        
        if chunk_id not in chunk_map:
            chunk_map[chunk_id] = ChunkAttribution(
                chunk_id=chunk_id,
                retrieved=False,
                used=False,
                retrieval_score=None,
                retrieval_span_id=None,
                answer_span_id=None
            )
        
        attr = chunk_map[chunk_id]
        
        if event.name == "chunk_retrieved":
            attr.retrieved = True
            attr.retrieval_score = event.data.get("score")
            if event.span_id:
                attr.retrieval_span_id = str(event.span_id)
        
        elif event.name == "chunk_used":
            attr.used = True
            if event.span_id:
                attr.answer_span_id = str(event.span_id)
    
    # 从 retrieval span 收集
    for span in spans:
        if span.name == "retrieval" and span.output:
            chunks = span.output.get("chunks", [])
            for i, chunk in enumerate(chunks):
                chunk_id = chunk.get("chunk_id") or chunk.get("id")
                if not chunk_id:
                    continue
                
                if chunk_id not in chunk_map:
                    chunk_map[chunk_id] = ChunkAttribution(
                        chunk_id=chunk_id,
                        retrieved=True,
                        used=False,
                        retrieval_score=chunk.get("score"),
                        retrieval_span_id=str(span.id),
                        answer_span_id=None
                    )
                else:
                    attr = chunk_map[chunk_id]
                    attr.retrieved = True
                    if not attr.retrieval_score:
                        attr.retrieval_score = chunk.get("score")
                    if not attr.retrieval_span_id:
                        attr.retrieval_span_id = str(span.id)
    
    return list(chunk_map.values())

