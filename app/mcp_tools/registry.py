from __future__ import annotations
from typing import Any, Dict, List, Optional


class ToolAdapter:
    """Minimal adapter contract for MCP tools."""

    id: str
    description: str

    def input_schema(self) -> Dict[str, Any]:  # JSON Schema
        raise NotImplementedError

    def output_schema(self) -> Optional[Dict[str, Any]]:  # Optional JSON Schema
        return None

    def invoke(self, ctx: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolAdapter] = {}

    def register(self, tool: ToolAdapter):
        self._tools[tool.id] = tool

    def list_tools(self) -> List[Dict[str, Any]]:
        out = []
        for tool in self._tools.values():
            out.append({
                "name": tool.id,
                "description": getattr(tool, "description", ""),
                "inputSchema": tool.input_schema(),
                "outputSchema": tool.output_schema() or {},
            })
        return out

    def invoke(self, name: str, ctx: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
        if name not in self._tools:
            return {"success": False, "error": {"code": -32601, "message": "Method not found", "data": {"name": name}}}
        try:
            return self._tools[name].invoke(ctx, args)
        except Exception as e:
            return {"success": False, "error": {"code": -32000, "message": "Tool execution error", "data": {"detail": str(e)}}}


# Singleton registry used by API
registry = ToolRegistry()
