from uuid import UUID
from dataclasses import dataclass, field
from typing import Optional
from sqlalchemy.orm import Session
from tracelens.storage.repository import SpanRepository, EventRepository


@dataclass
class Node:
    id: str
    type: str  # "span" or "event"
    name: str
    data: dict = field(default_factory=dict)


@dataclass
class Edge:
    from_id: str
    to_id: str
    relation: str  # "parent", "sequence", "trigger"


@dataclass
class RunGraph:
    run_id: UUID
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "run_id": str(self.run_id),
            "nodes": [{"id": n.id, "type": n.type, "name": n.name, "data": n.data} for n in self.nodes],
            "edges": [{"from": e.from_id, "to": e.to_id, "relation": e.relation} for e in self.edges]
        }


def build_run_graph(run_id: UUID, db: Session) -> RunGraph:
    span_repo = SpanRepository(db)
    event_repo = EventRepository(db)
    
    graph = RunGraph(run_id=run_id)
    
    spans = span_repo.get_by_run(run_id)
    events = event_repo.get_by_run(run_id)
    
    # 添加 span 节点
    for span in spans:
        graph.nodes.append(Node(
            id=f"span:{span.id}",
            type="span",
            name=span.name,
            data={"input": span.input, "output": span.output}
        ))
        
        # 添加 parent 边
        if span.parent_span_id:
            graph.edges.append(Edge(
                from_id=f"span:{span.parent_span_id}",
                to_id=f"span:{span.id}",
                relation="parent"
            ))
    
    # 添加 event 节点
    for event in events:
        graph.nodes.append(Node(
            id=f"event:{event.id}",
            type="event",
            name=event.name,
            data=event.data
        ))
        
        # 添加 event -> span 边
        if event.span_id:
            graph.edges.append(Edge(
                from_id=f"span:{event.span_id}",
                to_id=f"event:{event.id}",
                relation="trigger"
            ))
    
    return graph

