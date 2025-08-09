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
