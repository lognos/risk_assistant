from __future__ import annotations
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from app.config.settings import settings
from app.audit.logger import setup_logging, audit_span
from app.a2a.models import A2ARequest, A2AResponse
from app.models.request_models import ChatRequest, ChatResponse
from app.risk_agent import RiskAgent
from app.risk_core import RiskCore
from app.mcp_tools.monte_carlo import MonteCarloTool
from app.mcp_tools.tool_registry import MCP_TOOL_SCHEMAS

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.api_title, version=settings.api_version)

# Singletons for Phase 1
agent = RiskAgent()
core = RiskCore()
mc_tool = MonteCarloTool()


@app.post("/a2a/analyze", response_model=A2AResponse)
async def a2a_analyze(req: A2ARequest):
    with audit_span(logger, "a2a_analyze", correlation_id=req.correlation_id, extra={"message_type": req.message_type}):
        if req.task.type not in ("monte_carlo_simulation", "risk_analysis"):
            return A2AResponse(
                correlation_id=req.correlation_id,
                status="failed",
                error={"code": "UNSUPPORTED_TASK", "message": f"Task {req.task.type} not supported in Phase 1"}
            )

        # Build a minimal natural-language like query for interpret
        nl_query = "run monte carlo simulation"
        context = {**req.task.context, **req.task.parameters}
        plan = await agent.interpret_query(nl_query, context)

        if not plan.get("tools"):
            return A2AResponse(
                correlation_id=req.correlation_id,
                status="failed",
                error={"code": "UNCLEAR_REQUEST", "message": "No executable plan"}
            )

        # Execute the single MC step
        tool = plan["tools"][0]
        params = tool["parameters"]
        try:
            result = mc_tool.run(
                project_id=int(params["project_id"]),
                data_date=params.get("data_date"),
                duration_months=int(params.get("duration_months", 12)),
                iterations=int(params.get("iterations", 10000)),
                enable_correlation=bool(params.get("enable_correlation", True)),
                db_loader=core.db_loader_callback,
            )
        except Exception as e:
            return A2AResponse(
                correlation_id=req.correlation_id,
                status="failed",
                error={"code": "TOOL_ERROR", "message": str(e)}
            )

        if not result.get("success"):
            return A2AResponse(
                correlation_id=req.correlation_id,
                status="failed",
                error=result.get("error", {"code": "UNKNOWN", "message": "Execution failed"})
            )

        summary_text = await agent.generate_response(result, plan.get("language", "en"))
        return A2AResponse(
            correlation_id=req.correlation_id,
            status="completed",
            response_type="immediate",
            data={"summary": summary_text, "results": result},
        )


@app.post("/agent/chat", response_model=ChatResponse)
async def agent_chat(req: ChatRequest):
    with audit_span(logger, "agent_chat"):
        context = {**req.context}
        if req.language:
            context["language"] = req.language
        plan = await agent.interpret_query(req.query, context)
        if plan.get("intent") != "run_monte_carlo_simulation" or not plan.get("tools"):
            raise HTTPException(status_code=400, detail="Unable to understand the request in Phase 1")

        tool = plan["tools"][0]
        params = tool["parameters"]
        try:
            result = mc_tool.run(
                project_id=int(params.get("project_id") or context.get("project_id") or 1),
                data_date=params.get("data_date"),
                duration_months=int(params.get("duration_months", 12)),
                iterations=int(params.get("iterations", 10000)),
                enable_correlation=bool(params.get("enable_correlation", True)),
                db_loader=core.db_loader_callback,
            )
        except Exception as e:
            return JSONResponse(status_code=500, content=ChatResponse(
                success=False,
                error={"code": "TOOL_ERROR", "message": str(e)}
            ).model_dump())

        summary_text = await agent.generate_response(result, plan.get("language", req.language or "en"))
        return ChatResponse(success=True, data=result, summary=summary_text, language=plan.get("language", "en"))


# Minimal MCP-style endpoints for external tool calls (Phase 1)
@app.get("/mcp/tools")
async def mcp_list_tools():
    return {
        "tools": [
            {"name": name, **schema}
            for name, schema in MCP_TOOL_SCHEMAS.items()
        ]
    }


@app.post("/mcp/call")
async def mcp_call(payload: dict):
    name = payload.get("name")
    args = payload.get("arguments", {})
    if name not in MCP_TOOL_SCHEMAS:
        return JSONResponse(status_code=400, content={
            "error": {"code": -32601, "message": "Method not found", "data": {"name": name}}
        })

    if name == mc_tool.name:
        try:
            result = mc_tool.run(
                project_id=int(args.get("project_id")),
                data_date=args.get("data_date"),
                duration_months=int(args.get("duration_months", 12)),
                iterations=int(args.get("iterations", 10000)),
                enable_correlation=bool(args.get("enable_correlation", True)),
                db_loader=core.db_loader_callback,
            )
        except Exception as e:
            return JSONResponse(status_code=500, content={
                "error": {"code": -32000, "message": "Tool execution error", "data": {"detail": str(e)}}
            })
        if not result.get("success"):
            return JSONResponse(status_code=400, content={
                "error": {"code": -32001, "message": "Execution failed", "data": result.get("error")}
            })
        return {"result": result}

    return JSONResponse(status_code=400, content={
        "error": {"code": -32601, "message": "Tool not implemented", "data": {"name": name}}
    })
