from __future__ import annotations
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import threading


@dataclass
class TaskStatus:
    correlation_id: str
    status: str  # accepted|processing|completed|failed
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[Dict[str, Any]] = None
    estimated_completion: Optional[str] = None


class StatusStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._store: Dict[str, TaskStatus] = {}

    def start(self, correlation_id: str, estimated_completion: Optional[str] = None, data: Optional[Dict[str, Any]] = None):
        with self._lock:
            self._store[correlation_id] = TaskStatus(
                correlation_id=correlation_id,
                status="accepted",
                estimated_completion=estimated_completion,
                data=data or {},
            )

    def set_processing(self, correlation_id: str):
        with self._lock:
            if correlation_id in self._store:
                self._store[correlation_id].status = "processing"
                self._store[correlation_id].updated_at = datetime.utcnow()

    def complete(self, correlation_id: str, data: Dict[str, Any]):
        with self._lock:
            if correlation_id in self._store:
                self._store[correlation_id].status = "completed"
                self._store[correlation_id].data = data
                self._store[correlation_id].updated_at = datetime.utcnow()

    def fail(self, correlation_id: str, error: Dict[str, Any]):
        with self._lock:
            if correlation_id in self._store:
                self._store[correlation_id].status = "failed"
                self._store[correlation_id].error = error
                self._store[correlation_id].updated_at = datetime.utcnow()

    def get(self, correlation_id: str) -> Optional[TaskStatus]:
        with self._lock:
            return self._store.get(correlation_id)
