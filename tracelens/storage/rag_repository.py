from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import desc
from tracelens.storage.rag_models import RetrievedChunk, PromptChunk, GoldChunk


class RetrievedChunkRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def bulk_create(self, run_id: UUID, chunks: list[dict]):
        """批量创建 retrieved chunks"""
        for chunk in chunks:
            rc = RetrievedChunk(
                run_id=run_id,
                chunk_id=chunk["chunk_id"],
                content=chunk.get("content"),
                score=chunk.get("score")
            )
            self.db.add(rc)
        self.db.commit()
    
    def get_by_run(self, run_id: UUID) -> list[RetrievedChunk]:
        return self.db.query(RetrievedChunk).filter(RetrievedChunk.run_id == run_id).order_by(desc(RetrievedChunk.score).nulls_last()).all()


class PromptChunkRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def bulk_create(self, run_id: UUID, chunk_ids: list[str]):
        """批量创建 prompt chunks"""
        for chunk_id in chunk_ids:
            pc = PromptChunk(
                run_id=run_id,
                chunk_id=chunk_id
            )
            self.db.add(pc)
        self.db.commit()
    
    def get_by_run(self, run_id: UUID) -> list[PromptChunk]:
        return self.db.query(PromptChunk).filter(PromptChunk.run_id == run_id).all()


class GoldChunkRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def bulk_create(self, run_id: UUID, chunk_ids: list[str]):
        """批量创建 gold chunks"""
        for chunk_id in chunk_ids:
            gc = GoldChunk(run_id=run_id, chunk_id=chunk_id)
            self.db.add(gc)
        self.db.commit()
    
    def get_by_run(self, run_id: UUID) -> list[GoldChunk]:
        return self.db.query(GoldChunk).filter(GoldChunk.run_id == run_id).all()

