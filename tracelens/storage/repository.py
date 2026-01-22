from uuid import UUID
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from tracelens.storage.models import Run, Span, Event, Metric


class RunRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, name: str, query: str = None, version_id: str = None, 
               evaluation_id: UUID = None, test_case_id: UUID = None, metadata: dict = None) -> Run:
        run = Run(
            name=name, query=query, version_id=version_id,
            evaluation_id=evaluation_id, test_case_id=test_case_id,
            metadata_=metadata or {}
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run
    
    def get(self, run_id: UUID) -> Optional[Run]:
        return self.db.query(Run).filter(Run.id == run_id).first()
    
    def end(self, run_id: UUID, status: str = "success") -> Optional[Run]:
        run = self.get(run_id)
        if run:
            run.status = status
            run.ended_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(run)
        return run
    
    def get_by_version(self, version_id: str) -> list[Run]:
        return self.db.query(Run).filter(Run.version_id == version_id).order_by(Run.started_at.desc()).all()


class SpanRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, run_id: UUID, name: str, parent_span_id: UUID = None, 
               input: dict = None, metadata: dict = None) -> Span:
        span = Span(
            run_id=run_id, name=name, parent_span_id=parent_span_id,
            input=input or {}, metadata_=metadata or {}
        )
        self.db.add(span)
        self.db.commit()
        self.db.refresh(span)
        return span
    
    def get(self, span_id: UUID) -> Optional[Span]:
        return self.db.query(Span).filter(Span.id == span_id).first()
    
    def end(self, span_id: UUID, output: dict = None) -> Optional[Span]:
        span = self.get(span_id)
        if span:
            span.output = output or {}
            span.ended_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(span)
        return span
    
    def get_by_run(self, run_id: UUID) -> list[Span]:
        return self.db.query(Span).filter(Span.run_id == run_id).all()


class EventRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, run_id: UUID, name: str, data: dict = None, 
               span_id: UUID = None) -> Event:
        event = Event(run_id=run_id, name=name, data=data or {}, span_id=span_id)
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event
    
    def get_by_run(self, run_id: UUID) -> list[Event]:
        return self.db.query(Event).filter(Event.run_id == run_id).all()


class MetricRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, run_id: UUID, name: str, value: float = None, 
               value_json: dict = None, metadata: dict = None) -> Metric:
        metric = Metric(
            run_id=run_id, name=name, value=value,
            value_json=value_json, metadata_=metadata or {}
        )
        self.db.add(metric)
        self.db.commit()
        self.db.refresh(metric)
        return metric
    
    def get_by_run(self, run_id: UUID) -> list[Metric]:
        return self.db.query(Metric).filter(Metric.run_id == run_id).all()

