from __future__ import annotations
import logging
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from app.config.settings import settings
from app.audit.logger import setup_logging, audit_span
from app.a2a.models import A2ARequest, A2AResponse
from app.models.request_models import ChatRequest, ChatResponse
from app.risk_agent import RiskAgent
from app.risk_core import RiskCore
from app.database import DatabaseService
from app.mcp_tools.monte_carlo import MonteCarloTool
from app.a2a.status_store import StatusStore

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.api_title, version=settings.api_version)

# Singletons
status_store = StatusStore()
agent = RiskAgent()
db = DatabaseService()
core = RiskCore(db_service=db)
mc_tool = MonteCarloTool()
conversations: dict = {}

"""MCP-style HTTP/WS endpoints were removed. For real MCP, use app/mcp_server.py."""


# MCP WebSocket endpoint removed.

@app.get("/health")
async def health():
    ok = getattr(db, "client", None) is not None
    return {"status": "ok" if ok else "degraded", "db": ok}


def _run_a2a_simulation(correlation_id: str, params: dict):
    try:
        status_store.set_processing(correlation_id)
        result = mc_tool.run(
            project_id=params["project_id"],
            data_date=params.get("data_date"),
            iterations=int(params.get("iterations", 10000)),
            enable_correlation=bool(params.get("enable_correlation", True)),
            db_loader=core.db_loader_callback,
        )
        if not result.get("success"):
            status_store.fail(correlation_id, result.get("error") or {"code": "UNKNOWN"})
        else:
            status_store.complete(correlation_id, result)
    except Exception as e:
        status_store.fail(correlation_id, {"code": "TOOL_ERROR", "message": str(e)})


@app.post("/a2a/analyze", response_model=A2AResponse)
async def a2a_analyze(req: A2ARequest, background_tasks: BackgroundTasks):
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

        # Execute the single MC step (sync or async)
        tool = plan["tools"][0]
        params = tool["parameters"]
        if req.callback:
            # Async path
            from datetime import datetime, timedelta
            est = (datetime.utcnow() + timedelta(seconds=min(req.timeout or 300, 300))).isoformat()
            status_store.start(req.correlation_id, estimated_completion=est, data={"accepted": True})
            background_tasks.add_task(_run_a2a_simulation, req.correlation_id, params)
            return A2AResponse(
                correlation_id=req.correlation_id,
                status="accepted",
                response_type="callback",
                data={"message": "Processing started"},
                estimated_completion=est,
            )
        else:
            # Sync path
            try:
                result = mc_tool.run(
                    project_id=params["project_id"],
                    data_date=params.get("data_date"),
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


@app.get("/a2a/status/{correlation_id}")
async def a2a_status(correlation_id: str):
    st = status_store.get(correlation_id)
    if not st:
        return JSONResponse(status_code=404, content={"error": {"code": "NOT_FOUND", "message": "Unknown correlation_id"}})
    return {
        "correlation_id": st.correlation_id,
        "status": st.status,
        "data": st.data,
        "estimated_completion": st.estimated_completion,
        "error": st.error,
    "created_at": st.created_at.isoformat(),
    "updated_at": st.updated_at.isoformat(),
    }


@app.post("/agent/chat", response_model=ChatResponse)
async def agent_chat(req: ChatRequest):
    with audit_span(logger, "agent_chat"):
        # Conversation memory (lightweight)
        context = {**conversations.get(req.conversation_id, {}), **req.context}
        if req.language:
            context["language"] = req.language
        plan = await agent.interpret_query(req.query, context)
        if plan.get("intent") != "run_monte_carlo_simulation" or not plan.get("tools"):
            raise HTTPException(status_code=400, detail="Unable to understand the request in Phase 1")

        tool = plan["tools"][0]
        params = tool["parameters"]
        try:
            result = mc_tool.run(
                project_id=params.get("project_id") or context.get("project_id") or "1",
                data_date=params.get("data_date"),
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
        if req.conversation_id:
            conversations[req.conversation_id] = {"last_summary": summary_text, **context}
        return ChatResponse(success=True, data=result, summary=summary_text, language=plan.get("language", "en"))


"""MCP HTTP endpoints removed; use app.mcp_server for real MCP over stdio."""
