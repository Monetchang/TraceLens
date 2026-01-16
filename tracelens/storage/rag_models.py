import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Boolean, Text, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from tracelens.storage.database import Base


class RetrievedChunk(Base):
    __tablename__ = "retrieved_chunks"
    
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id"), nullable=False, primary_key=True)
    chunk_id = Column(String(255), nullable=False, primary_key=True)
    content = Column(Text, nullable=True)
    score = Column(Float, nullable=True)
    
    run = relationship("Run", back_populates="retrieved_chunks")


class PromptChunk(Base):
    __tablename__ = "prompt_chunks"
    
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id"), nullable=False, primary_key=True)
    chunk_id = Column(String(255), nullable=False, primary_key=True)
    
    run = relationship("Run", back_populates="prompt_chunks")


class GoldChunk(Base):
    __tablename__ = "gold_chunks"
    
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id"), nullable=False, primary_key=True)
    chunk_id = Column(String(255), nullable=False, primary_key=True)
    
    run = relationship("Run", back_populates="gold_chunks")

