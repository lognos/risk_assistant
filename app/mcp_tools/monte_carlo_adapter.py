from __future__ import annotations
from typing import Any, Dict

from app.mcp_tools.registry import ToolAdapter
from app.mcp_tools.monte_carlo import MonteCarloTool
from app.risk_core import RiskCore


class MonteCarloAdapter(ToolAdapter):
    id = "run_monte_carlo_simulation"
    description = "Execute Monte Carlo cost evolution simulation with correlation analysis"

    def __init__(self, core: RiskCore):
        self.core = core
        self.tool = MonteCarloTool()

    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "project_id": {"type": ["string", "integer"], "description": "Project identifier"},
                "data_date": {"type": "string", "description": "YYYY-MM-DD"},
                "iterations": {"type": "integer", "default": 10000},
                "enable_correlation": {"type": "boolean", "default": True},
            },
            "required": ["project_id"],
            "additionalProperties": False,
        }

    def invoke(self, ctx: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
        return self.tool.run(
            project_id=args["project_id"],
            data_date=args.get("data_date"),
            iterations=int(args.get("iterations", 10000)),
            enable_correlation=bool(args.get("enable_correlation", True)),
            db_loader=self.core.db_loader_callback,
        )
