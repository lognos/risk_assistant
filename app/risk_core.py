from __future__ import annotations
from typing import Dict, Any, Tuple
import logging
import pandas as pd

from app.audit.logger import audit_span
from app.database import DatabaseService
from app.montecarlo.mc_database_helpers import (
    normalize_capex_items,
    normalize_capex_actions,
    normalize_risks,
    normalize_risk_actions,
)

logger = logging.getLogger(__name__)


class RiskCore:
    """Domain manager for loading data and executing tools."""

    def __init__(self, db_service=None):
        self.db_service = db_service or DatabaseService()

    def load_project_data(self, project_id) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Load capex, actions, risks, risk_actions for the given project.
        Requirement: no synthetic fallback. If DB is unavailable, raise a clear error.
        """
        with audit_span(logger, "load_project_data", extra={"project_id": project_id}):
            if self.db_service is None or getattr(self.db_service, "client", None) is None:
                raise RuntimeError(
                    "DATA_SOURCE_UNAVAILABLE: Database service is not configured or unavailable. "
                    "Please configure Supabase credentials and database loaders."
                )
            # Fetch from Supabase and normalize to engine-ready DataFrames
            capex_items_rows = self.db_service.get_capex_items(project_id)
            capex_actions_rows = self.db_service.get_capex_actions(project_id)
            risks_rows = self.db_service.get_risks(project_id)
            risk_actions_rows = self.db_service.get_risk_actions(project_id)

            capex_items_df = normalize_capex_items(capex_items_rows)
            capex_actions_df = normalize_capex_actions(capex_actions_rows)
            risks_df = normalize_risks(risks_rows)
            risk_actions_df = normalize_risk_actions(risk_actions_rows)

            # Minimal presence check: CAPEX items are required for simulation
            if capex_items_df.empty:
                raise RuntimeError("INSUFFICIENT_DATA: No CAPEX items found for project")

            return capex_items_df, capex_actions_df, risks_df, risk_actions_df

    def db_loader_callback(self, project_id):
        return self.load_project_data(project_id)
