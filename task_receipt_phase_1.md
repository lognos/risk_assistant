# Risk Assistant – Phase 1 Task Receipt

## Summary

Phase 1 delivers a multi-interface Risk Assistant that runs Monte Carlo simulations through three access paths: A2A, conversational chat, and MCP-style tool calls. It follows the three-stage workflow (Interpret → Execute → Respond), integrates the existing Monte Carlo engine, supports English/Spanish/French summaries, and includes protocol-specific error handling and audit logging.

## What’s included

- Three-stage workflow scaffolding
  - Interpret: lightweight multilingual intent/plan creation
  - Execute: MCP-style tool orchestration (Monte Carlo)
  - Respond: concise multilingual summaries (EN/ES/FR)
- Interfaces
  - A2A: POST `/a2a/analyze`
  - Chat: POST `/agent/chat`
  - MCP-style: GET `/mcp/tools`, POST `/mcp/call`
- Integration
  - Uses existing Monte Carlo engine in `app/montecarlo/`
  - Synthetic DB fallback data aligned to validators; DB loaders remain pluggable
- Observability
  - Simple audit spans (start/end/duration, correlation_id)
  - Protocol-specific error responses

## Key files added/updated (high level)

- `app/risk_api.py` – FastAPI app with A2A, chat, and MCP endpoints
- `app/risk_agent.py` – Interpret + multilingual response scaffolding
- `app/risk_core.py` – Domain manager with synthetic data fallback
- `app/mcp_tools/monte_carlo.py` – MCP-style Monte Carlo tool wrapper
- `app/mcp_tools/tool_registry.py` – Tool schema for discovery
- `app/a2a/models.py` – A2A request/response models
- `app/models/request_models.py` – Chat request/response models
- `app/audit/logger.py` – Audit span + logging setup
- `app/config/settings.py` – Settings for protocols/tools
- `app/prompts/query_interpretation.xml`, `app/prompts/response_generation.xml` – Prompt stubs
- `app/i18n/locales.py` – Minimal system messages
- `app/tests/test_smoke_montecarlo.py` – Smoke test for Monte Carlo tool

## How to run (macOS/zsh)

- Start API (uses existing venv):

```
cd /Users/facu/LOGNOS/01_APPS/ASSIST/RISK_ASSIST
source venv/bin/activate
uvicorn app.risk_api:app --host 127.0.0.1 --port 8000
```

- Exercise interfaces (examples):
  - MCP (list tools):
    - `curl -s http://127.0.0.1:8000/mcp/tools`
  - MCP (call Monte Carlo):
    - `curl -s -X POST http://127.0.0.1:8000/mcp/call -H "Content-Type: application/json" -d '{"name":"run_monte_carlo_simulation","arguments":{"project_id":1,"iterations":1500,"duration_months":3}}'`
  - A2A (Monte Carlo request):
    - `curl -s -X POST http://127.0.0.1:8000/a2a/analyze -H "Content-Type: application/json" -d '{"agent_id":"main","task":{"type":"monte_carlo_simulation","context":{"project_id":1},"parameters":{"iterations":1500,"duration_months":3}},"correlation_id":"proj1-risk-001"}'`
  - Chat (Spanish):
    - `curl -s -X POST http://127.0.0.1:8000/agent/chat -H "Content-Type: application/json" -d '{"query":"Ejecutar simulación Monte Carlo para el proyecto 1","context":{"project_id":1},"language":"es"}'`

## Verification (Phase 1)

- Environment: existing venv used; requirements installed
- Monte Carlo tool smoke run: PASS (timeseries produced, summary present)
- Endpoints tested live:
  - `/mcp/tools`: returns tool schema
  - `/mcp/call`: executes simulation and returns structured results
  - `/a2a/analyze`: returns `status=completed` with multilingual summary
  - `/agent/chat`: Spanish request returns Spanish summary

## Three-stage workflow mapping

- Interpret: `RiskAgent.interpret_query` creates a tool plan from EN/ES/FR queries
- Execute: `MonteCarloTool.run` routes to `MonteCarloEngine.simulate_cost_evolution`
- Respond: `RiskAgent.generate_response` emits multilingual summary per protocol needs

## Protocol compatibility

- A2A: Structured request/response models; correlation_id preserved; error codes on failure
- MCP-style: Tool schemas discoverable; JSON tool invocation with structured results/errors
- HTTP endpoints: FastAPI routes for A2A, chat, and MCP

## Language support

- English, Spanish, French supported for conversational summaries
- Parameter names standardized in English

## Error handling

- A2A: `{ status: failed, error: { code, message, details? } }`
- MCP: JSON-RPC style `{ error: { code, message, data } }`
- Chat: `400` for unclear intent; `500` with `TOOL_ERROR` when applicable

## Audit trail

- `audit_span` logs start/end/duration with optional `correlation_id`
- Applied in `/a2a/analyze` and `/agent/chat`, plus data loading

## Requirements coverage

- Protocol Compatibility (A2A/MCP/HTTP): Done
- Language Support (EN/ES/FR): Done
- Tool Extensibility (MCP-based): Done
- Error Handling (protocol-specific): Done
- Audit Trail (correlation/performance): Done
- Success Criteria: Receive requests via any interface → interpret → execute Monte Carlo → return results in user’s language: Done

## Notes & next steps

- DB integration: Implement Supabase-backed loaders (MCP for project id kxwradnyjqobvdheklsn) to replace synthetic fallback
- Interpretation/Response: Swap heuristics for Gemini 2.5 with XML prompts
- MCP: Optionally expose a full MCP server for external clients (discovery/introspection)
- A2A: Optional async/callback patterns, status updates, and retries
