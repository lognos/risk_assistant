# Assistant Workflow Extensions: A2A & MCP Integration Guide

## Overview

This document extends the core [assistant_workflow.md](./assistant_workflow.md) with specific guidance for implementing **Agent-to-Agent (A2A)** protocols and **Model Context Protocol (MCP)** integration. Use this as complementary guidance to the proven three-stage workflow pattern.

## Core Workflow Compatibility

The A2A and MCP integrations **maintain full compatibility** with the established three-stage pattern:

```
┌─────────────────┐    A2A       ┌──────────────────┐    MCP      ┌─────────────────┐
│ External Agent  │◄────────────►│ Assistant        │◄───────────►│ External Tools  │
│ (A2A Client)    │              │ (Core Workflow)  │             │ (MCP Clients)   │
└─────────────────┘              └──────────────────┘             └─────────────────┘
                                          │
                                          ▼
                                 ┌─────────────────┐
                                 │ Three-Stage     │
                                 │ Workflow        │
                                 │ 1. Interpret    │
                                 │ 2. Execute      │
                                 │ 3. Respond      │
                                 └─────────────────┘
```

## A2A Protocol Integration

### Extension to Agent Class

```python
class RiskAgent:  # Extends core Agent pattern
    def __init__(self):
        # Core workflow components (from assistant_workflow.md)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        self.tools_registry = self._build_tools_registry()
        
        # A2A extensions
        self.a2a_handlers = self._build_a2a_handlers()
    
    async def process_a2a_request(self, a2a_message: A2AMessage) -> Dict:
        """A2A-specific entry point that feeds into core workflow"""
        
        # Convert A2A message to internal query format
        internal_query = self._convert_a2a_to_query(a2a_message)
        
        # Use existing core workflow
        result = await self.interpret_query(
            query=internal_query,
            context=a2a_message.context
        )
        
        # Format response for A2A protocol
        return self._format_for_a2a(result, a2a_message)
```

### A2A Message Patterns

**Structured Request Format:**
```python
{
    "agent_id": "source-agent-name",
    "target_agent": "risk-assistant", 
    "message_type": "analysis_request|status_query|capability_inquiry",
    "task": {
        "type": "monte_carlo_simulation|risk_assessment|mitigation_planning",
        "context": {"project_id": 123, "trigger": "scope_change"},
        "parameters": {"duration_months": 12, "confidence_level": 0.95}
    },
    "callback": {"endpoint": "/agent/callback", "format": "structured|summary"},
    "correlation_id": "unique-request-id",
    "priority": "normal|high|critical",
    "timeout": 300
}
```

**A2A Response Format:**
```python
{
    "correlation_id": "matching-request-id",
    "status": "accepted|processing|completed|failed",
    "agent_id": "risk-assistant",
    "response_type": "immediate|callback|streaming",
    "data": {
        "executive_summary": "AI-generated summary for agent consumption",
        "structured_results": {...},
        "confidence_score": 0.85,
        "processing_metadata": {...}
    },
    "next_actions": ["suggested_followup_tasks"],
    "estimated_completion": "ISO-8601-timestamp"
}
```

## MCP Tool Integration

### Extension to Executor Class

```python
class RiskExecutor:  # Extends core Executor pattern
    def __init__(self, domain_manager):
        # Core workflow components (from assistant_workflow.md)
        self.domain_manager = domain_manager
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        self.results_cache = {}
        
        # MCP extensions
        self._mcp_server = Server("risk-assistant-tools")
        self._register_mcp_tools()
        
        # Unified tool mapping (core + MCP)
        self.tool_methods = {
            "run_monte_carlo_simulation": self._execute_via_mcp,
            "analyze_risk_trends": self._execute_via_mcp,
            # Traditional tools still supported
            "legacy_tool": self.domain_manager.legacy_method
        }
    
    def _register_mcp_tools(self):
        """Register tools following MCP protocol"""
        
        @self._mcp_server.list_tools()
        async def list_tools():
            return [Tool(name=name, **schema) for name, schema in TOOL_SCHEMAS.items()]
        
        @self._mcp_server.call_tool()
        async def call_tool(name: str, arguments: dict):
            # Execute using domain manager
            result = await self.domain_manager.execute_tool(name, arguments)
            return [TextContent(type="text", text=json.dumps(result))]
    
    async def execute_plan(self, plan: Dict) -> Dict:
        """Enhanced execution supporting both traditional and MCP tools"""
        
        # Core execution logic (from assistant_workflow.md)
        results = {}
        
        for tool_step in sorted(plan.get("tools", []), key=lambda x: x.get("order", 0)):
            tool_name = tool_step["tool"]
            parameters = self._resolve_parameters(tool_step["parameters"], results)
            
            # Execute via appropriate method (MCP or traditional)
            if tool_name in self.mcp_tools:
                result = await self._execute_via_mcp(tool_name, parameters)
            else:
                result = await self._execute_traditional_tool(tool_name, parameters)
            
            # Cache result (core workflow pattern)
            step_id = f"step_{tool_step.get('order', len(results))}"
            results[step_id] = result
        
        return self._aggregate_results(results)
```

### MCP Tool Schema Standards

**Follow the core tools registry pattern with MCP extensions:**

```python
MCP_TOOL_SCHEMAS = {
    "run_monte_carlo_simulation": {
        "description": "Execute Monte Carlo cost evolution simulation with correlation analysis",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer", "description": "Project identifier"},
                "duration_months": {"type": "integer", "default": 12, "minimum": 1, "maximum": 60},
                "iterations": {"type": "integer", "default": 10000, "minimum": 1000, "maximum": 50000},
                "enable_correlation": {"type": "boolean", "default": True}
            },
            "required": ["project_id"]
        },
        # Core workflow extensions
        "triggers": ["simulation", "monte carlo", "cost evolution", "risk analysis"],
        "returns": "Structured simulation results with statistical analysis",
        "complexity": "medium",
        "estimated_time_ms": 5000
    }
}
```

## Protocol-Specific Best Practices

### A2A Communication Patterns

**DO:**
- ✅ Maintain correlation IDs across all interactions
- ✅ Provide clear status updates for long-running tasks
- ✅ Use structured error codes for programmatic handling
- ✅ Include confidence scores in responses
- ✅ Support both synchronous and asynchronous patterns

**DON'T:**
- ❌ Expose internal implementation details in A2A responses
- ❌ Create circular A2A dependencies between agents
- ❌ Use A2A for simple function calls (use direct APIs instead)
- ❌ Ignore timeout specifications from requesting agents

### MCP Tool Design Patterns

**DO:**
- ✅ Keep tool interfaces stateless and idempotent
- ✅ Provide comprehensive input validation schemas
- ✅ Return structured, machine-readable results
- ✅ Include execution metadata (timing, resource usage)
- ✅ Support tool discovery and introspection

**DON'T:**
- ❌ Create MCP tools that depend on conversation context
- ❌ Return unstructured text from MCP tools
- ❌ Ignore parameter validation requirements
- ❌ Create tools with hidden side effects

## Integration with Core Workflow Anti-Patterns

### Additional A2A Anti-Patterns

**❌ Protocol Complexity:**
- Don't create complex A2A message routing logic
- Don't implement custom A2A authentication schemes without security review
- Don't use A2A for real-time communication (use webhooks/events instead)

**❌ MCP Overengineering:**
- Don't create MCP tools for simple utility functions
- Don't implement complex state management in MCP tools
- Don't use MCP for user interface interactions

### Protocol-Specific Error Handling

```python
# A2A Error Response Format
{
    "correlation_id": "request-id",
    "status": "failed",
    "error": {
        "code": "INSUFFICIENT_DATA|TIMEOUT|INVALID_PROJECT|TOOL_UNAVAILABLE",
        "message": "Human-readable error description",
        "details": {"project_id": 123, "available_data_points": 45},
        "retry_after": 60,  # seconds
        "suggested_action": "Provide additional project context"
    }
}

# MCP Error Response Format
{
    "error": {
        "code": -32602,  # JSON-RPC error codes
        "message": "Invalid parameters",
        "data": {
            "parameter": "iterations",
            "provided": 100000,
            "maximum": 50000
        }
    }
}
```

## Configuration Extensions

### Protocol Configuration

```python
class Settings(BaseSettings):
    # Core workflow settings (existing)
    gemini_model: str = "gemini-2.0-flash-exp"
    max_response_tokens: int = 4096
    
    # A2A Protocol settings
    a2a_enabled: bool = True
    a2a_authentication_required: bool = True
    a2a_max_timeout: int = 300
    a2a_callback_retry_attempts: int = 3
    
    # MCP Protocol settings
    mcp_server_enabled: bool = True
    mcp_server_name: str = "risk-assistant"
    mcp_max_tool_execution_time: int = 60
    mcp_enable_tool_introspection: bool = True
```

## Testing Extensions

### A2A Integration Testing

```python
async def test_a2a_workflow():
    """Test A2A request follows core workflow pattern"""
    a2a_request = A2AMessage(
        agent_id="test-agent",
        task={"type": "monte_carlo_simulation", "context": {"project_id": 123}}
    )
    
    # Should follow: interpret → execute → respond
    response = await risk_agent.process_a2a_request(a2a_request)
    
    assert response["correlation_id"] == a2a_request.correlation_id
    assert "executive_summary" in response["data"]
    assert response["status"] == "completed"
```

### MCP Tool Testing

```python
async def test_mcp_tool_compatibility():
    """Test MCP tools work with core workflow"""
    plan = {
        "tools": [
            {
                "tool": "run_monte_carlo_simulation",
                "parameters": {"project_id": 123, "iterations": 10000},
                "order": 1
            }
        ]
    }
    
    # Should execute via MCP but follow core workflow
    result = await risk_executor.execute_plan(plan)
    
    assert result["success"] == True
    assert "simulation_results" in result
```

## Migration from Core Workflow

### Phase 1: Add Protocol Layers
1. Implement A2A and MCP interfaces as **extensions** to existing classes
2. Maintain backward compatibility with existing HTTP endpoints
3. Test protocols independently before integration

### Phase 2: Unified Tool Registry
1. Convert existing tools to MCP format while maintaining functionality
2. Update tools registry to support both traditional and MCP schemas
3. Validate all tools work via both access methods

### Phase 3: Protocol Optimization
1. Optimize A2A message handling for performance
2. Add advanced MCP features (streaming, batching)
3. Implement comprehensive monitoring and observability

## Summary

This guide extends the core assistant workflow with protocol-specific patterns while maintaining the proven three-stage architecture. The key principle is **additive enhancement** - A2A and MCP capabilities are added as extensions, not replacements, to the established workflow patterns.

**Key Compatibility Points:**
- A2A requests are converted to internal queries and processed via core workflow
- MCP tools are implemented as extensions to the core executor pattern  
- All anti-patterns from the core workflow guide still apply
- Error handling and response generation follow established patterns
- Tool registry design principles are extended, not replaced
