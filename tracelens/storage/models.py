import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Integer, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from tracelens.storage.database import Base


class Run(Base):
    __tablename__ = "runs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255))
    query = Column(Text, nullable=True)
    answer = Column(Text, nullable=True)
    version_id = Column(String(255), nullable=True)
    evaluation_id = Column(UUID(as_uuid=True), ForeignKey("evaluations.id"), nullable=True)
    test_case_id = Column(UUID(as_uuid=True), ForeignKey("test_cases.id"), nullable=True)
    status = Column(String(50), default="running")  # running / success / error
    metadata_ = Column("metadata", JSONB, default=dict)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    
    spans = relationship("Span", back_populates="run")
    events = relationship("Event", back_populates="run")
    metrics = relationship("Metric", back_populates="run")
    retrieved_chunks = relationship("RetrievedChunk", back_populates="run", cascade="all, delete-orphan")
    prompt_chunks = relationship("PromptChunk", back_populates="run", cascade="all, delete-orphan")
    gold_chunks = relationship("GoldChunk", back_populates="run", cascade="all, delete-orphan")
    evaluation = relationship("Evaluation", back_populates="runs")
    test_case = relationship("TestCase", back_populates="runs")
    # GraphRAG relationships
    graph_nodes = relationship("GraphNode", back_populates="run", cascade="all, delete-orphan")
    graph_edges = relationship("GraphEdge", back_populates="run", cascade="all, delete-orphan")
    reasoning_traces = relationship("ReasoningTrace", back_populates="run", cascade="all, delete-orphan")


class Span(Base):
    __tablename__ = "spans"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id"), nullable=False)
    name = Column(String(255))
    parent_span_id = Column(UUID(as_uuid=True), ForeignKey("spans.id"), nullable=True)
    input = Column(JSONB, default=dict)
    output = Column(JSONB, default=dict)
    metadata_ = Column("metadata", JSONB, default=dict)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    
    run = relationship("Run", back_populates="spans")
    parent = relationship("Span", remote_side=[id], backref="children")
    events = relationship("Event", back_populates="span")


class Event(Base):
    __tablename__ = "events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id"), nullable=False)
    span_id = Column(UUID(as_uuid=True), ForeignKey("spans.id"), nullable=True)
    name = Column(String(255))
    data = Column(JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    run = relationship("Run", back_populates="events")
    span = relationship("Span", back_populates="events")


class Metric(Base):
    __tablename__ = "metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id"), nullable=False)
    name = Column(String(255))
    value = Column(Float, nullable=True)
    value_json = Column(JSONB, nullable=True)
    metadata_ = Column("metadata", JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    run = relationship("Run", back_populates="metrics")

