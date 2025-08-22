from __future__ import annotations

"""
Real MCP server entrypoint exposing the existing registry tools over stdio.

This uses the Model Context Protocol (MCP) Python SDK. It bridges our
ToolRegistry tools to MCP's tools/list and tools/call semantics.

Run (from repo root, with venv active):
  python -m app.mcp_server
"""

import asyncio
import json
from typing import Any, Dict, List

try:
    # Official MCP SDK (Python)
    from mcp.server import Server
    from mcp.types import Tool as McpTool
    from mcp.types import TextContent
except Exception as e:  # pragma: no cover - helpful error at runtime
    raise SystemExit(
        "The 'mcp' package is required for the MCP server. Install it via pip install mcp"
    ) from e

from app.mcp_tools.registry import registry
from app.mcp_tools.db_health import DbHealthTool
from app.mcp_tools.project_snapshot import ProjectSnapshotTool
from app.mcp_tools.monte_carlo_adapter import MonteCarloAdapter
from app.database import DatabaseService
from app.risk_core import RiskCore


server = Server("risk-assistant")


def _init_tools() -> None:
    """Initialize and register tools with the shared registry."""
    db = DatabaseService()
    core = RiskCore(db_service=db)
    registry.register(DbHealthTool(db))
    registry.register(ProjectSnapshotTool(core))
    registry.register(MonteCarloAdapter(core))


@server.list_tools()
async def list_tools() -> List[McpTool]:
    """Return tools from our registry in MCP Tool format."""
    tools: List[McpTool] = []
    for t in registry.list_tools():
        # t: { name, description, inputSchema, outputSchema }
        tools.append(
            McpTool(
                name=t.get("name", ""),
                description=t.get("description", ""),
                inputSchema=t.get("inputSchema") or {"type": "object", "properties": {}},
            )
        )
    return tools


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any] | None) -> List[TextContent]:
    """Invoke a tool via our registry and wrap response as MCP content."""
    args = arguments or {}
    result = registry.invoke(name, ctx={"source": "mcp"}, args=args)
    # Return JSON payload as text content. Clients can parse it.
    return [TextContent(text=json.dumps(result))]


async def amain() -> None:
    _init_tools()
    from mcp.server.stdio import stdio_server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, 
            server.create_initialization_options()
        )


def main() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    main()
