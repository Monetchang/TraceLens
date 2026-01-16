import httpx
from uuid import UUID
from typing import Optional
from contextlib import contextmanager


class TraceLensClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self._current_run_id: Optional[UUID] = None
        self._current_span_id: Optional[UUID] = None
    
    def _post(self, path: str, json: dict) -> dict:
        with httpx.Client() as client:
            resp = client.post(f"{self.base_url}{path}", json=json)
            resp.raise_for_status()
            return resp.json()
    
    def _get(self, path: str) -> dict:
        with httpx.Client() as client:
            resp = client.get(f"{self.base_url}{path}")
            resp.raise_for_status()
            return resp.json()
    
    def start_run(self, name: str, metadata: dict = None) -> "Run":
        data = self._post("/api/v1/run/start", {"name": name, "metadata": metadata})
        run = Run(self, UUID(data["id"]), data)
        self._current_run_id = run.id
        return run
    
    def end_run(self, run_id: UUID = None, status: str = "success") -> dict:
        rid = run_id or self._current_run_id
        if not rid:
            raise ValueError("No active run")
        data = self._post(f"/api/v1/run/{rid}/end", {"status": status})
        if rid == self._current_run_id:
            self._current_run_id = None
        return data
    
    @contextmanager
    def span(self, name: str, input: dict = None, metadata: dict = None, parent_span_id: UUID = None):
        run_id = self._current_run_id
        if not run_id:
            raise ValueError("No active run")
        
        parent = parent_span_id or self._current_span_id
        data = self._post("/api/v1/span/start", {
            "run_id": str(run_id), "name": name,
            "parent_span_id": str(parent) if parent else None,
            "input": input, "metadata": metadata
        })
        span_id = UUID(data["id"])
        prev_span = self._current_span_id
        self._current_span_id = span_id
        
        try:
            span_obj = SpanContext(self, span_id)
            yield span_obj
            output = span_obj._output
        except Exception as e:
            self._post(f"/api/v1/span/{span_id}/end", {"output": {"error": str(e)}})
            raise
        else:
            self._post(f"/api/v1/span/{span_id}/end", {"output": output})
        finally:
            self._current_span_id = prev_span
    
    def event(self, name: str, data: dict = None, span_id: UUID = None):
        run_id = self._current_run_id
        if not run_id:
            raise ValueError("No active run")
        
        self._post("/api/v1/event", {
            "run_id": str(run_id), "name": name, "data": data,
            "span_id": str(span_id or self._current_span_id) if (span_id or self._current_span_id) else None
        })
    
    def metric(self, name: str, value: float = None, value_json: dict = None, metadata: dict = None):
        run_id = self._current_run_id
        if not run_id:
            raise ValueError("No active run")
        
        self._post("/api/v1/metric", {
            "run_id": str(run_id), "name": name,
            "value": value, "value_json": value_json, "metadata": metadata
        })
    
    def get_rag_metrics(self, run_id: UUID = None) -> dict:
        rid = run_id or self._current_run_id
        if not rid:
            raise ValueError("No run specified")
        return self._get(f"/api/v1/run/{rid}/rag-metrics")


class Run:
    def __init__(self, client: TraceLensClient, id: UUID, data: dict):
        self.client = client
        self.id = id
        self.data = data
    
    def end(self, status: str = "success"):
        return self.client.end_run(self.id, status)


class SpanContext:
    def __init__(self, client: TraceLensClient, id: UUID):
        self.client = client
        self.id = id
        self._output = {}
    
    def set_output(self, output: dict):
        self._output = output


# 全局单例
_client: Optional[TraceLensClient] = None

def init(base_url: str = "http://localhost:8000"):
    global _client
    _client = TraceLensClient(base_url)
    return _client

def get_client() -> TraceLensClient:
    global _client
    if not _client:
        _client = TraceLensClient()
    return _client

def start_run(name: str, metadata: dict = None) -> Run:
    return get_client().start_run(name, metadata)

def span(name: str, input: dict = None, metadata: dict = None):
    return get_client().span(name, input, metadata)

def event(name: str, data: dict = None, span_id: UUID = None):
    return get_client().event(name, data, span_id)

def metric(name: str, value: float = None, value_json: dict = None, metadata: dict = None):
    return get_client().metric(name, value, value_json, metadata)

def get_rag_metrics(run_id: UUID = None) -> dict:
    return get_client().get_rag_metrics(run_id)

