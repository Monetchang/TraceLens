from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.database import Base


class Run(Base):
    __tablename__ = "runs"
    run_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    app_id = Column(String(255), nullable=False, index=True)
    query = Column(Text, nullable=False)
    index_version = Column(String(100), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())


class Retrieval(Base):
    __tablename__ = "retrievals"
    retrieval_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.run_id"), nullable=False, index=True)
    retriever_name = Column(String(255), nullable=False)
    top_k = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class Chunk(Base):
    __tablename__ = "chunks"
    chunk_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doc_id = Column(String(255), nullable=False, index=True)
    index_version = Column(String(100), nullable=False, index=True)
    content = Column(Text, nullable=False)


class RetrievalChunk(Base):
    __tablename__ = "retrieval_chunks"
    retrieval_id = Column(UUID(as_uuid=True), ForeignKey("retrievals.retrieval_id"), primary_key=True)
    chunk_id = Column(UUID(as_uuid=True), ForeignKey("chunks.chunk_id"), primary_key=True)
    score = Column(Float, nullable=False)
    rank = Column(Integer, nullable=False)


class PromptChunk(Base):
    __tablename__ = "prompt_chunks"
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.run_id"), primary_key=True)
    chunk_id = Column(UUID(as_uuid=True), ForeignKey("chunks.chunk_id"), primary_key=True)
    order_index = Column(Integer, nullable=False)


class Answer(Base):
    __tablename__ = "answers"
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.run_id"), primary_key=True)
    answer_text = Column(Text, nullable=False)


class ChunkAttribution(Base):
    __tablename__ = "chunk_attribution"
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.run_id"), primary_key=True)
    chunk_id = Column(UUID(as_uuid=True), ForeignKey("chunks.chunk_id"), primary_key=True)
    overlap_tokens = Column(Integer, nullable=False)
    overlap_ratio = Column(Float, nullable=False)

