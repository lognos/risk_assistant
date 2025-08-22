# Risk Assistant (Phase 1)

Multi-interface Risk Assistant with A2A and MCP-style tool integration.

## Endpoints
- POST /a2a/analyze
- POST /agent/chat

## Run locally
Use uvicorn to start the API after installing requirements.

## Notes
- Phase 1 uses simple heuristics for interpretation and multilingual summaries.
- Monte Carlo tool is wired to existing engine with synthetic data fallback.

## POC usage: A2A and MCP flows

- A2A (HTTP)
	- Sync: POST /a2a/analyze with body { agent_id, correlation_id, task:{ type:"risk_analysis", context:{}, parameters:{ project_id, iterations, duration_months } } }
		- Response: status "completed" with results, or "failed" with an error code (e.g., DATA_SOURCE_UNAVAILABLE, INSUFFICIENT_DATA).
	- Async: include a non-null callback to receive 202-like behavior and poll GET /a2a/status/{correlation_id}. The status payload includes created_at/updated_at timestamps.

- MCP (HTTP mimic)
	- GET /mcp/tools → lists tools (monte carlo, db.health, project.snapshot).
	- POST /mcp/call with { name, arguments } → invokes a tool and returns a result or an error.

- MCP (WebSocket)
	- Connect to /mcp/ws and send JSON objects:
		- {"id":1,"method":"tool.list"}
		- {"id":2,"method":"tool.call","params":{"name":"db.health","arguments":{}}}
		- {"id":3,"method":"tool.call","params":{"name":"project.snapshot","arguments":{"project_id":1}}}

Notes
- This is a POC: no auth, in-memory A2A status, and DB may be empty. Tools return clear error codes when inputs/data are insufficient.

 
