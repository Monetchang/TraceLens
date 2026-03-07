from uuid import UUID
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from tracelens.storage.evaluation_models import TestSuite, TestCase, Evaluation
from tracelens.storage.models import Run


class TestSuiteRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, name: str, description: Optional[str] = None) -> TestSuite:
        suite = TestSuite(name=name, description=description)
        self.db.add(suite)
        self.db.commit()
        self.db.refresh(suite)
        return suite
    
    def get(self, suite_id: UUID) -> Optional[TestSuite]:
        return self.db.query(TestSuite).filter(TestSuite.id == suite_id).first()
    
    def list(self, limit: int = 100, offset: int = 0) -> List[TestSuite]:
        return self.db.query(TestSuite).order_by(TestSuite.created_at.desc()).limit(limit).offset(offset).all()
    
    def get_test_case_count(self, suite_id: UUID) -> int:
        return self.db.query(func.count(TestCase.id)).filter(TestCase.test_suite_id == suite_id).scalar()


class TestCaseRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(
        self, 
        test_suite_id: UUID, 
        query: str, 
        gold_answer: Optional[str] = None,
        gold_chunk_ids: Optional[List[str]] = None,
        gold_doc_ids: Optional[List[str]] = None,
        metadata: Optional[dict] = None
    ) -> TestCase:
        test_case = TestCase(
            test_suite_id=test_suite_id,
            query=query,
            gold_answer=gold_answer,
            gold_chunk_ids=gold_chunk_ids,
            gold_doc_ids=gold_doc_ids,
            metadata_=metadata or {}
        )
        self.db.add(test_case)
        self.db.commit()
        self.db.refresh(test_case)
        return test_case
    
    def bulk_create(self, test_suite_id: UUID, test_cases: List[dict]) -> List[TestCase]:
        """批量创建测试用例"""
        created_cases = []
        for tc_data in test_cases:
            test_case = TestCase(
                test_suite_id=test_suite_id,
                query=tc_data["query"],
                gold_answer=tc_data.get("gold_answer"),
                gold_chunk_ids=tc_data.get("gold_chunk_ids"),
                gold_doc_ids=tc_data.get("gold_doc_ids"),
                gold_path=tc_data.get("gold_path"),
                gold_nodes=tc_data.get("gold_nodes"),
                metadata_=tc_data.get("metadata", {}),
            )
            self.db.add(test_case)
            created_cases.append(test_case)
        
        self.db.commit()
        for tc in created_cases:
            self.db.refresh(tc)
        return created_cases
    
    def get(self, test_case_id: UUID) -> Optional[TestCase]:
        return self.db.query(TestCase).filter(TestCase.id == test_case_id).first()
    
    def get_by_suite(self, test_suite_id: UUID, limit: int = 1000, offset: int = 0) -> List[TestCase]:
        return self.db.query(TestCase).filter(
            TestCase.test_suite_id == test_suite_id
        ).order_by(TestCase.created_at).limit(limit).offset(offset).all()


class EvaluationRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(
        self, 
        name: str,
        test_suite_id: UUID, 
        version_id: str,
        metadata: Optional[dict] = None
    ) -> Evaluation:
        evaluation = Evaluation(
            name=name,
            test_suite_id=test_suite_id,
            version_id=version_id,
            metadata_=metadata or {}
        )
        self.db.add(evaluation)
        self.db.commit()
        self.db.refresh(evaluation)
        return evaluation
    
    def get(self, evaluation_id: UUID) -> Optional[Evaluation]:
        return self.db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()
    
    def update_status(self, evaluation_id: UUID, status: str) -> Optional[Evaluation]:
        evaluation = self.get(evaluation_id)
        if evaluation:
            evaluation.status = status
            if status == "completed":
                evaluation.completed_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(evaluation)
        return evaluation

    def update_metadata(self, evaluation_id: UUID, updates: dict) -> Optional[Evaluation]:
        evaluation = self.get(evaluation_id)
        if evaluation:
            meta = dict(evaluation.metadata_ or {})
            meta.update(updates)
            evaluation.metadata_ = meta
            self.db.commit()
            self.db.refresh(evaluation)
        return evaluation
    
    def get_runs(self, evaluation_id: UUID, status: Optional[str] = None) -> List[Run]:
        query = self.db.query(Run).filter(Run.evaluation_id == evaluation_id)
        if status:
            query = query.filter(Run.status == status)
        return query.order_by(Run.started_at).all()
    
    def get_run_count(self, evaluation_id: UUID, status: Optional[str] = None) -> int:
        query = self.db.query(func.count(Run.id)).filter(Run.evaluation_id == evaluation_id)
        if status:
            query = query.filter(Run.status == status)
        return query.scalar()
    
    def list(self, limit: int = 100, offset: int = 0) -> List[Evaluation]:
        return self.db.query(Evaluation).order_by(Evaluation.created_at.desc()).limit(limit).offset(offset).all()

