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
        For Phase 1, if DB is not configured, return synthetic demo data.
        """
        with audit_span(logger, "load_project_data", extra={"project_id": project_id}):
            if self.db_service is None or getattr(self.db_service, "client", None) is None:
                # Synthetic small dataset
                capex_items = pd.DataFrame([
                    {"item_id": 1, "item_name": "Equipment A", "min_cost": 80_000, "ml_cost": 100_000, "max_cost": 130_000},
                    {"item_id": 2, "item_name": "Installation", "min_cost": 50_000, "ml_cost": 70_000, "max_cost": 100_000},
                ])
                capex_actions = pd.DataFrame([
                    {"cost_action_id": 1001, "item_id": 1, "cost_action_name": "Negotiate vendor",
                     "cost_action_due": "2025-11-01", "pm_min_cost": 75_000, "pm_ml_cost": 95_000, "pm_max_cost": 120_000},
                ])
                risks = pd.DataFrame([
                    {"risk_id": 1, "risk_name": "Delay", "min_impact": 10_000, "ml_impact": 20_000, "max_impact": 40_000, "risk_probability": 0.3, "risk_log": "2025-08-01"},
                ])
                risk_actions = pd.DataFrame([
                    {"risk_action_id": 2001, "risk_id": 1, "risk_action_name": "Expedite approvals",
                     "risk_action_due": "2025-10-15", "pm_min_impact": 5_000, "pm_ml_impact": 12_000, "pm_max_impact": 20_000, "pm_risk_probability": 0.2},
                ])
                return capex_items, capex_actions, risks, risk_actions
            else:
                # Placeholder: fetch from real DB using self.db_service
                # TODO: implement database loaders according to normalized schema
                raise NotImplementedError("Database loaders not implemented in Phase 1")

    def db_loader_callback(self, project_id: int):
        return self.load_project_data(project_id)
