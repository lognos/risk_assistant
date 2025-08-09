from __future__ import annotations
from typing import Dict, Any, Tuple
import logging
import pandas as pd

from app.audit.logger import audit_span

logger = logging.getLogger(__name__)


class RiskCore:
    """Domain manager for loading data and executing tools."""

    def __init__(self, db_service=None):
        self.db_service = db_service

    def load_project_data(self, project_id: int) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Load capex, actions, risks, risk_actions for the given project.
        Requirement: no synthetic fallback. If DB is unavailable, raise a clear error.
        """
        with audit_span(logger, "load_project_data", extra={"project_id": project_id}):
            if self.db_service is None or getattr(self.db_service, "client", None) is None:
                raise RuntimeError(
                    "DATA_SOURCE_UNAVAILABLE: Database service is not configured or unavailable. "
                    "Please configure Supabase credentials and database loaders."
                )
            # Placeholder: fetch from real DB using self.db_service
            # TODO: implement database loaders according to normalized schema (development/ docs)
            raise NotImplementedError("Database loaders not implemented yet")

    def db_loader_callback(self, project_id: int):
        return self.load_project_data(project_id)
