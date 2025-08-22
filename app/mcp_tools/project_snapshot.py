from __future__ import annotations
from typing import Any, Dict

import pandas as pd

from app.mcp_tools.registry import ToolAdapter
from app.risk_core import RiskCore


class ProjectSnapshotTool(ToolAdapter):
    id = "project.snapshot"
    description = "Return normalized project data counts and a small preview"

    def __init__(self, core: RiskCore):
        self.core = core

    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {"project_id": {"type": "integer"}},
            "required": ["project_id"],
            "additionalProperties": False,
        }

    def invoke(self, ctx: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
        pid = int(args["project_id"])
        capex_items, capex_actions, risks, risk_actions = self.core.db_loader_callback(pid)
        def head(df: pd.DataFrame):
            return df.head(5).to_dict(orient="records") if not df.empty else []
        return {
            "success": True,
            "counts": {
                "capex_items": int(len(capex_items.index)),
                "capex_actions": int(len(capex_actions.index)),
                "risks": int(len(risks.index)),
                "risk_actions": int(len(risk_actions.index)),
            },
            "preview": {
                "capex_items": head(capex_items),
                "risks": head(risks),
            },
        }
