import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from tracelens.storage.database import Base


class TestSuite(Base):
    __tablename__ = "test_suites"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    test_cases = relationship("TestCase", back_populates="test_suite", cascade="all, delete-orphan")
    evaluations = relationship("Evaluation", back_populates="test_suite")


class TestCase(Base):
    __tablename__ = "test_cases"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_suite_id = Column(UUID(as_uuid=True), ForeignKey("test_suites.id"), nullable=False)
    query = Column(Text, nullable=False)
    
    # RAG gold 数据
    gold_answer = Column(Text, nullable=True)
    gold_chunk_ids = Column(JSONB, nullable=True)  # List of chunk IDs
    gold_doc_ids = Column(JSONB, nullable=True)    # List of document IDs
    
    # GraphRAG gold 数据
    gold_path = Column(JSONB, nullable=True)       # List[str]: 标准推理路径节点列表
    gold_nodes = Column(JSONB, nullable=True)      # List[str]: 应该检索到的关键节点
    
    metadata_ = Column("metadata", JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    test_suite = relationship("TestSuite", back_populates="test_cases")
    runs = relationship("Run", back_populates="test_case")


class Evaluation(Base):
    __tablename__ = "evaluations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    test_suite_id = Column(UUID(as_uuid=True), ForeignKey("test_suites.id"), nullable=False)
    version_id = Column(String(255), nullable=False)
    status = Column(String(50), default="running")  # running / completed / failed
    metadata_ = Column("metadata", JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    test_suite = relationship("TestSuite", back_populates="evaluations")
    runs = relationship("Run", back_populates="evaluation")

