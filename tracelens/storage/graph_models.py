"""
GraphRAG 数据模型
用于存储图结构和推理轨迹
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from tracelens.storage.database import Base


class GraphNode(Base):
    """图节点"""
    __tablename__ = "graph_nodes"
    
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id"), nullable=False, primary_key=True)
    node_id = Column(String(255), nullable=False, primary_key=True)
    node_type = Column(String(50), nullable=False)  # entity, chunk, concept
    label = Column(String(255), nullable=True)
    metadata_ = Column("metadata", JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    run = relationship("Run", back_populates="graph_nodes")


class GraphEdge(Base):
    """图边"""
    __tablename__ = "graph_edges"
    
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id"), nullable=False, primary_key=True)
    from_node = Column(String(255), nullable=False, primary_key=True)
    to_node = Column(String(255), nullable=False, primary_key=True)
    relation = Column(String(255), nullable=False, primary_key=True)
    metadata_ = Column("metadata", JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    run = relationship("Run", back_populates="graph_edges")


class ReasoningTrace(Base):
    """推理轨迹"""
    __tablename__ = "reasoning_traces"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id"), nullable=False)
    step_index = Column(Integer, nullable=False)
    from_node = Column(String(255), nullable=False)
    to_node = Column(String(255), nullable=False)
    relation = Column(String(255), nullable=True)
    reason = Column(Text, nullable=True)
    is_selected = Column(Boolean, default=False)  # 是否被选中用于最终推理
    created_at = Column(DateTime, default=datetime.utcnow)
    
    run = relationship("Run", back_populates="reasoning_traces")

