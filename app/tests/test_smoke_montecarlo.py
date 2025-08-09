import json
from app.mcp_tools.monte_carlo import MonteCarloTool
from app.risk_core import RiskCore


def test_monte_carlo_smoke():
    tool = MonteCarloTool()
    core = RiskCore()
    result = tool.run(project_id=1, iterations=1000, duration_months=3, db_loader=core.db_loader_callback)
    assert result["success"], f"Expected success, got: {json.dumps(result, indent=2)}"
    assert "timeseries" in result and len(result["timeseries"]) > 0
