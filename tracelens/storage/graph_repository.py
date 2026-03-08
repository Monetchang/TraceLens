"""
GraphRAG 数据访问层
"""
from uuid import UUID
from typing import List, Optional
from sqlalchemy.orm import Session
from tracelens.storage.graph_models import GraphNode, GraphEdge, ReasoningTrace


class GraphNodeRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, run_id: UUID, node_id: str, node_type: str, label: Optional[str] = None, metadata: Optional[dict] = None):
        """创建图节点"""
        node = GraphNode(
            run_id=run_id,
            node_id=node_id,
            node_type=node_type,
            label=label,
            metadata_=metadata or {}
        )
        self.db.add(node)
        self.db.commit()
        return node
    
    def get_by_run(self, run_id: UUID) -> List[GraphNode]:
        """获取 run 的所有节点"""
        return self.db.query(GraphNode).filter(GraphNode.run_id == run_id).all()
    
    def get_by_node_id(self, run_id: UUID, node_id: str) -> Optional[GraphNode]:
        """获取指定节点"""
        return self.db.query(GraphNode).filter(
            GraphNode.run_id == run_id,
            GraphNode.node_id == node_id
        ).first()


class GraphEdgeRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, run_id: UUID, from_node: str, to_node: str, relation: str, metadata: Optional[dict] = None):
        """创建图边"""
        edge = GraphEdge(
            run_id=run_id,
            from_node=from_node,
            to_node=to_node,
            relation=relation,
            metadata_=metadata or {}
        )
        self.db.add(edge)
        self.db.commit()
        return edge
    
    def get_by_run(self, run_id: UUID) -> List[GraphEdge]:
        """获取 run 的所有边"""
        return self.db.query(GraphEdge).filter(GraphEdge.run_id == run_id).all()
    
    def get_outgoing_edges(self, run_id: UUID, node_id: str) -> List[GraphEdge]:
        """获取节点的出边"""
        return self.db.query(GraphEdge).filter(
            GraphEdge.run_id == run_id,
            GraphEdge.from_node == node_id
        ).all()


class ReasoningTraceRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(
        self,
        run_id: UUID,
        step_index: int,
        from_node: str,
        to_node: str,
        relation: Optional[str] = None,
        reason: Optional[str] = None,
        is_selected: bool = False
    ):
        """创建推理轨迹"""
        trace = ReasoningTrace(
            run_id=run_id,
            step_index=step_index,
            from_node=from_node,
            to_node=to_node,
            relation=relation,
            reason=reason,
            is_selected=is_selected
        )
        self.db.add(trace)
        self.db.commit()
        return trace
    
    def get_by_run(self, run_id: UUID) -> List[ReasoningTrace]:
        """获取 run 的所有推理轨迹"""
        return self.db.query(ReasoningTrace).filter(
            ReasoningTrace.run_id == run_id
        ).order_by(ReasoningTrace.step_index).all()
    
    def get_selected_path(self, run_id: UUID) -> List[ReasoningTrace]:
        """获取被选中的推理路径"""
        return self.db.query(ReasoningTrace).filter(
            ReasoningTrace.run_id == run_id,
            ReasoningTrace.is_selected == True
        ).order_by(ReasoningTrace.step_index).all()
    
    def mark_as_selected(self, run_id: UUID, step_indices: List[int]):
        """标记指定步骤为选中"""
        self.db.query(ReasoningTrace).filter(
            ReasoningTrace.run_id == run_id,
            ReasoningTrace.step_index.in_(step_indices)
        ).update({"is_selected": True}, synchronize_session=False)
        self.db.commit()

    def get_selected_path_edges(self, run_id: UUID) -> List["ReasoningTrace"]:
        """获取选中路径的边（与 get_selected_path 相同，别名）"""
        return self.get_selected_path(run_id)

    def get_explored_branches(self, run_id: UUID) -> List["ReasoningTrace"]:
        """获取所有探索分支（每个 graph_expand 事件一条）"""
        return self.get_by_run(run_id)

