from __future__ import annotations
from typing import Any, Dict

from app.mcp_tools.registry import ToolAdapter
from app.database import DatabaseService


class DbHealthTool(ToolAdapter):
    id = "db.health"
    description = "Check database connectivity status"

    def __init__(self, db: DatabaseService):
        self.db = db

    def input_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}, "additionalProperties": False}

    def invoke(self, ctx: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
        ok = getattr(self.db, "client", None) is not None
        return {"success": True, "status": "ok" if ok else "degraded", "db": ok}
