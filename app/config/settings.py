from pydantic import BaseModel
from typing import Optional


class Settings(BaseModel):
    # A2A
    a2a_enabled: bool = True
    a2a_authentication_required: bool = False
    a2a_max_timeout: int = 300

    # MCP
    mcp_server_enabled: bool = True
    mcp_server_name: str = "risk-assistant"
    mcp_max_tool_execution_time: int = 60
    mcp_enable_tool_introspection: bool = True

    # Tools
    monte_carlo_max_iterations: int = 50000

    # AI (placeholder for Gemini integration)
    gemini_model: str = "gemini-2.0-flash-exp"
    max_response_tokens: int = 2048

    # API
    api_title: str = "Risk Assistant"
    api_version: str = "0.1.0"


settings = Settings()
