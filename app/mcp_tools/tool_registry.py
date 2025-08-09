MCP_TOOL_SCHEMAS = {
    "run_monte_carlo_simulation": {
        "description": "Execute Monte Carlo cost evolution simulation with correlation analysis",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer", "description": "Project identifier"},
                "data_date": {"type": "string", "description": "YYYY-MM-DD"},
                "duration_months": {"type": "integer", "default": 12, "minimum": 1, "maximum": 60},
                "iterations": {"type": "integer", "default": 10000, "minimum": 1000, "maximum": 50000},
                "enable_correlation": {"type": "boolean", "default": True}
            },
            "required": ["project_id"]
        },
        "triggers": ["simulation", "monte carlo", "cost evolution", "risk analysis"],
        "returns": "Structured simulation results with statistical analysis",
        "complexity": "medium",
        "estimated_time_ms": 5000
    }
}
