from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.models import Run, Retrieval, Chunk, RetrievalChunk, PromptChunk, Answer, ChunkAttribution
from app.schemas import (
    RunCreate, RunResponse, RetrievalCreate, RetrievalResponse,
    PromptChunksCreate, AnswerCreate, RAGMetrics, ChunkAttributionOut,
    DiffResponse, ChunkDiff
)
from app.attribution import compute_attribution, is_chunk_used, tokenize

router = APIRouter(prefix="/api/v1")


@router.post("/run", response_model=RunResponse)
def create_run(data: RunCreate, db: Session = Depends(get_db)):
    run = Run(app_id=data.app_id, query=data.query, index_version=data.index_version)
    db.add(run)
    db.commit()
    return RunResponse(run_id=run.run_id)


@router.post("/retrieval", response_model=RetrievalResponse)
def create_retrieval(data: RetrievalCreate, db: Session = Depends(get_db)):
    run = db.query(Run).filter(Run.run_id == data.run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    retrieval = Retrieval(run_id=data.run_id, retriever_name=data.retriever_name, top_k=data.top_k)
    db.add(retrieval)
    db.flush()
    
    for c in data.chunks:
        existing = db.query(Chunk).filter(Chunk.chunk_id == c.chunk_id).first()
        if not existing:
            chunk = Chunk(chunk_id=c.chunk_id, doc_id=c.doc_id, index_version=run.index_version, content=c.content)
            db.add(chunk)
        rc = RetrievalChunk(retrieval_id=retrieval.retrieval_id, chunk_id=c.chunk_id, score=c.score, rank=c.rank)
        db.add(rc)
    
    db.commit()
    return RetrievalResponse(retrieval_id=retrieval.retrieval_id)


@router.post("/prompt/chunks")
def add_prompt_chunks(data: PromptChunksCreate, db: Session = Depends(get_db)):
    run = db.query(Run).filter(Run.run_id == data.run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    for c in data.chunks:
        pc = PromptChunk(run_id=data.run_id, chunk_id=c.chunk_id, order_index=c.order_index)
        db.add(pc)
    db.commit()
    return {"status": "ok"}


@router.post("/answer")
def create_answer(data: AnswerCreate, db: Session = Depends(get_db)):
    run = db.query(Run).filter(Run.run_id == data.run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    answer = Answer(run_id=data.run_id, answer_text=data.answer_text)
    db.add(answer)
    db.flush()
    
    prompt_chunks = db.query(PromptChunk).filter(PromptChunk.run_id == data.run_id).all()
    for pc in prompt_chunks:
        chunk = db.query(Chunk).filter(Chunk.chunk_id == pc.chunk_id).first()
        if chunk:
            overlap_tokens, overlap_ratio = compute_attribution(data.answer_text, chunk.content)
            attr = ChunkAttribution(
                run_id=data.run_id,
                chunk_id=pc.chunk_id,
                overlap_tokens=overlap_tokens,
                overlap_ratio=overlap_ratio
            )
            db.add(attr)
    
    db.commit()
    return {"status": "ok"}


@router.get("/run/{run_id}/rag-metrics", response_model=RAGMetrics)
def get_rag_metrics(run_id: UUID, db: Session = Depends(get_db)):
    run = db.query(Run).filter(Run.run_id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    answer = db.query(Answer).filter(Answer.run_id == run_id).first()
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")
    
    total_answer_tokens = len(tokenize(answer.answer_text))
    
    retrievals = db.query(Retrieval).filter(Retrieval.run_id == run_id).all()
    retrieved_chunk_ids = set()
    for r in retrievals:
        rcs = db.query(RetrievalChunk).filter(RetrievalChunk.retrieval_id == r.retrieval_id).all()
        for rc in rcs:
            retrieved_chunk_ids.add(rc.chunk_id)
    retrieved_chunks = len(retrieved_chunk_ids)
    
    prompt_chunk_count = db.query(PromptChunk).filter(PromptChunk.run_id == run_id).count()
    
    attributions = db.query(ChunkAttribution).filter(ChunkAttribution.run_id == run_id).all()
    
    attr_out = []
    used_count = 0
    for a in attributions:
        used = is_chunk_used(a.overlap_ratio)
        if used:
            used_count += 1
        attr_out.append(ChunkAttributionOut(
            chunk_id=a.chunk_id,
            overlap_tokens=a.overlap_tokens,
            overlap_ratio=a.overlap_ratio,
            used=used
        ))
    
    retrieval_utilization = used_count / retrieved_chunks if retrieved_chunks > 0 else 0.0
    unused_prompt = prompt_chunk_count - used_count
    pollution_rate = unused_prompt / prompt_chunk_count if prompt_chunk_count > 0 else 0.0
    
    return RAGMetrics(
        run_id=run_id,
        total_answer_tokens=total_answer_tokens,
        retrieved_chunks=retrieved_chunks,
        prompt_chunks=prompt_chunk_count,
        used_chunks=used_count,
        retrieval_utilization=retrieval_utilization,
        pollution_rate=pollution_rate,
        attributions=attr_out
    )


@router.get("/diff", response_model=DiffResponse)
def get_diff(run_a: UUID, run_b: UUID, db: Session = Depends(get_db)):
    run_a_obj = db.query(Run).filter(Run.run_id == run_a).first()
    run_b_obj = db.query(Run).filter(Run.run_id == run_b).first()
    if not run_a_obj or not run_b_obj:
        raise HTTPException(status_code=404, detail="Run not found")
    
    attrs_a = {a.chunk_id: a for a in db.query(ChunkAttribution).filter(ChunkAttribution.run_id == run_a).all()}
    attrs_b = {a.chunk_id: a for a in db.query(ChunkAttribution).filter(ChunkAttribution.run_id == run_b).all()}
    
    all_chunk_ids = set(attrs_a.keys()) | set(attrs_b.keys())
    
    diffs = []
    for cid in all_chunk_ids:
        chunk = db.query(Chunk).filter(Chunk.chunk_id == cid).first()
        ratio_a = attrs_a[cid].overlap_ratio if cid in attrs_a else None
        ratio_b = attrs_b[cid].overlap_ratio if cid in attrs_b else None
        delta = (ratio_b or 0) - (ratio_a or 0)
        diffs.append(ChunkDiff(
            chunk_id=cid,
            doc_id=chunk.doc_id if chunk else "",
            run_a_overlap_ratio=ratio_a,
            run_b_overlap_ratio=ratio_b,
            delta=delta
        ))
    
    diffs.sort(key=lambda x: abs(x.delta), reverse=True)
    
    return DiffResponse(
        query=run_a_obj.query,
        run_a=run_a,
        run_b=run_b,
        index_version_a=run_a_obj.index_version,
        index_version_b=run_b_obj.index_version,
        diffs=diffs
    )

