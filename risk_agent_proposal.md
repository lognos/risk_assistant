
# Risk Agent Architecture Proposal

## Overview
Multi-language risk assistant agent following the proven three-stage workflow pattern: **Query Interpretation → Tool Execution → Response Generation**. Integrates A2A protocol for main agent communication and MCP for internal tool orchestration. Leverages Gemini 2.5's native multilingual capabilities.

## Architecture

### Communication Interfaces

```
┌─────────────────┐    A2A       ┌──────────────────┐    MCP      ┌─────────────────┐
│ MAIN Agent      │◄────────────►│ RISK Assistant   │◄───────────►│ External Tools  │
│ (Project Mgmt)  │              │                  │             │ (Claude, VS Code)│
└─────────────────┘              └──────────────────┘             └─────────────────┘
         │                                │                              
         │ HTTP/Chat                      │ Internal MCP Tools          
         ▼                                ▼                              
┌─────────────────┐                ┌──────────────────┐                 
│ User Interface  │                │ Monte Carlo      │                 
│ (Web/Mobile)    │                │ Risk Analysis    │                 
└─────────────────┘                │ Mitigation Tools │                 
                                   └──────────────────┘                 
```

### Core Components

```
app/
├── risk_agent.py          # Query interpreter & tool planner
├── risk_executor.py       # MCP-based tool orchestrator
├── risk_manager.py        # Domain business logic
├── risk_api.py           # Multi-interface API (A2A + HTTP)
├── a2a/
│   ├── __init__.py
│   ├── protocol.py        # A2A message handling
│   ├── handlers.py        # Request type handlers
│   └── models.py          # A2A message models
├── mcp_tools/
│   ├── __init__.py
│   ├── monte_carlo.py     # Monte Carlo MCP tool
│   ├── risk_evaluation.py   # Future risk analysis tool
│   └── tool_registry.py   # MCP tool definitions
├── prompts/
│   ├── prompt_loader.py   # XML prompt processing
│   ├── query_interpretation.xml
│   ├── tool_planning.xml
│   └── response_generation.xml
├── audit/
│   ├── __init__.py
│   └── logger.py          # Simple audit logging
├── config/
│   └── settings.py        # Configuration management
├── i18n/
│   └── locales.py         # System messages only
└── models/
    ├── request_models.py   # API models
    ├── agent_models.py     # Internal models
    └── a2a_models.py       # A2A protocol models
```

### Three-Stage Workflow with Protocol Integration

#### 1. Query Interpretation (RiskAgent)
- **Input**: Natural language query (EN/ES/FR) or A2A structured request
- **Process**: XML prompt → Gemini 2.5 → JSON plan
- **Output**: MCP tool execution plan with parameters
- **Language**: Auto-detected and maintained by Gemini

#### 2. Tool Execution (RiskExecutor with MCP)
- **Input**: Tool execution plan
- **Process**: Internal MCP tool calls → parameter resolution → result caching
- **Output**: Structured execution results
- **Tools**: MCP-based Monte Carlo simulation (extensible architecture)

#### 3. Response Generation
- **Input**: Execution results + context (A2A or conversational)
- **Process**: Result aggregation → Gemini summary → protocol-specific formatting
- **Output**: A2A structured response or conversational response

## Protocol Integration

### A2A (Agent-to-Agent) Interface
**Purpose**: Structured communication with MAIN project management agent

```python
# A2A Message Types
{
    "analysis_request": {
        "agent_id": "main-project-agent",
        "target_agent": "risk-assistant",
        "task": {
            "type": "monte_carlo_simulation",
            "context": {"project_id": 123, "trigger": "scope_change"},
            "parameters": {"duration_months": 18, "confidence_level": 0.95}
        },
        "callback": {"endpoint": "/risk-analysis-complete"},
        "correlation_id": "proj123-risk-001"
    }
}
```

### MCP (Model Context Protocol) Tools
**Purpose**: Internal tool orchestration and external tool access

```python
# MCP Tool Registry
{
    "run_monte_carlo_simulation": {
        "description": "Execute Monte Carlo cost evolution simulation",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer"},
                "duration_months": {"type": "integer", "default": 12},
                "iterations": {"type": "integer", "default": 10000},
                "enable_correlation": {"type": "boolean", "default": true}
            }
        }
    }
}
```

## Multi-Language Strategy

### Simplified Approach
- **Single prompt set** with multilingual instructions
- **Gemini 2.5 handles** language detection and response matching
- **Technical consistency** (parameter names in English)
- **Minimal localization** (system errors only)

### Example Prompt Structure
```xml
<context>
  <role>Multilingual risk management expert</role>
  <language_support>Detect user language, respond in same language</language_support>
</context>

<query_classification>
  <patterns_en>run simulation, monte carlo, cost evolution</patterns_en>
  <patterns_es>ejecutar simulación, monte carlo, evolución costos</patterns_es>
  <patterns_fr>exécuter simulation, monte carlo, évolution coûts</patterns_fr>
</query_classification>

<instructions>
  <rule>Respond in user's language</rule>
  <rule>Keep technical parameters in English</rule>
</instructions>
```

## Initial Tool Registry

```python
{
    "run_monte_carlo_simulation": {
        "description": "Execute Monte Carlo cost evolution simulation with correlation analysis",
        "parameters": {
            "project_id": "int - Project identifier",
            "data_date": "str - Analysis date (YYYY-MM-DD, default: current)",
            "duration_months": "int - Simulation duration (default: 12)",
            "iterations": "int - Monte Carlo iterations (default: 10000)",
            "enable_correlation": "bool - Enable correlation analysis (default: true)"
        },
        "returns": "Cost evolution, risk impacts, statistical analysis",
        "triggers": ["simulation", "monte carlo", "cost evolution", "risk impact"]
    },
    
    # Future placeholders
    "analyze_risk_trends": {"status": "placeholder"},
    "generate_mitigation_plan": {"status": "placeholder"},
    "compare_scenarios": {"status": "placeholder"}
}
```

## API Design

### Multi-Interface Architecture

#### A2A Interface (Primary for Main Agent)
```python
POST /a2a/analyze
{
    "agent_id": "main-project-agent",
    "task": {
        "type": "risk_analysis",
        "context": {"project_id": 123, "trigger": "scope_change"},
        "parameters": {"analysis_depth": "comprehensive"}
    },
    "callback": {"endpoint": "/main-agent/risk-complete"},
    "correlation_id": "proj123-risk-001"
}

Response:
{
    "status": "accepted|processing|completed",
    "correlation_id": "proj123-risk-001",
    "estimated_completion": "2025-08-08T14:30:00Z",
    "results": {
        "risk_score": 7.2,
        "critical_risks": [...],
        "executive_summary": "AI-generated summary for main agent",
        "detailed_report_url": "/reports/proj123-risk-001"
    }
}
```

#### Conversational Interface (For Direct User Access)
```python
POST /agent/chat
{
    "query": "Run Monte Carlo simulation for project 123",
    "context": {"project_id": 123},
    "conversation_id": "user-session-456"
}

Response:
{
    "success": true,
    "data": {
        "simulation_results": {...},
        "risk_insights": {...}
    },
    "summary": "Natural language summary in user's language",
    "conversation_context": {...}
}
```

#### MCP Interface (For External Tools)
```python
# Available via MCP protocol for Claude Desktop, VS Code, etc.
await mcp.call_tool("run_monte_carlo_simulation", {
    "project_id": 123,
    "iterations": 15000
})
```

## Implementation Architecture

### Core Executor with MCP Integration
```python
class RiskExecutor:
    def __init__(self):
        self._mcp_server = Server("risk-tools")
        self._register_mcp_tools()
    
    async def execute_plan(self, plan: Dict) -> Dict:
        """Execute using internal MCP tools"""
        results = {}
        for tool_step in plan["tools"]:
            # Call internal MCP tool
            result = await self._call_mcp_tool(
                tool_step["tool"], 
                tool_step["parameters"]
            )
            results[f"step_{tool_step['order']}"] = result
        return results
    
    def get_external_mcp_server(self) -> Server:
        """Expose MCP tools externally"""
        return self._mcp_server
```

### Unified Response Handling
```python
class ResponseFormatter:
    def format_for_a2a(self, results: Dict, request: A2ARequest) -> Dict:
        """Format results for main agent consumption"""
        return {
            "correlation_id": request.correlation_id,
            "executive_summary": self._generate_executive_summary(results),
            "risk_score": self._calculate_risk_score(results),
            "recommended_actions": self._extract_actions(results),
            "structured_data": results
        }
    
    def format_for_chat(self, results: Dict, query: str) -> Dict:
        """Format results for conversational interface"""
        return {
            "summary": self._generate_natural_language_summary(results, query),
            "data": results,
            "follow_up_suggestions": self._suggest_follow_ups(results)
        }
```
```

## Implementation Priorities

### Phase 1: Core Infrastructure with Protocol Integration
1. **MCP Tool Foundation**
   - Implement `run_monte_carlo_simulation` as MCP tool
   - Create internal MCP server for tool orchestration
   - Integrate with existing Monte Carlo engine

2. **A2A Protocol Implementation**
   - Define A2A message models and handlers
   - Implement `/a2a/analyze` endpoint
   - Create structured response formatting for main agent

3. **Basic Conversational Interface**
   - Implement `/agent/chat` endpoint using same MCP tools
   - XML prompt loading with multilingual support
   - Basic error handling and validation

### Phase 2: Enhanced Protocol Features
1. **Advanced A2A Capabilities**
   - Asynchronous processing with callbacks
   - Status updates and progress tracking
   - Error handling and retry mechanisms

2. **MCP External Access**
   - Expose MCP server for Claude Desktop/VS Code
   - Tool discovery and documentation
   - Parameter validation and error responses

3. **Enhanced Conversational Features**
   - Context management across conversations
   - Follow-up question suggestions
   - Multi-step workflow support

### Phase 3: Advanced Features & Additional Tools
1. **New MCP Tools**
   - `analyze_risk_trends` tool implementation
   - `generate_mitigation_plan` tool
   - `compare_scenarios` tool

2. **Advanced Protocol Features**
   - A2A message authentication and security
   - Rate limiting and throttling
   - Comprehensive audit logging

3. **Performance & Scalability**
   - Result caching and optimization
   - Concurrent request handling
   - Load balancing across instances

## Additional Recommendations

### 1. Configuration Management
```python
# config/settings.py
class Settings(BaseSettings):
    # A2A Configuration
    a2a_enabled: bool = True
    main_agent_endpoint: str = "http://main-agent:8000"
    callback_timeout: int = 300
    
    # MCP Configuration  
    mcp_external_enabled: bool = True
    mcp_server_name: str = "risk-assistant"
    
    # Tool Configuration
    monte_carlo_max_iterations: int = 50000
    default_simulation_duration: int = 12
    
    # AI Configuration
    gemini_model: str = "gemini-2.0-flash-exp"
    max_response_tokens: int = 4096
```

### 2. Error Handling Strategy
```python
# Define protocol-specific error responses
A2A_ERROR_CODES = {
    "INVALID_PROJECT": "Project ID not found or inaccessible",
    "INSUFFICIENT_DATA": "Insufficient data for requested analysis",
    "ANALYSIS_TIMEOUT": "Analysis exceeded maximum processing time",
    "TOOL_UNAVAILABLE": "Requested analysis tool is temporarily unavailable"
}

CONVERSATIONAL_ERRORS = {
    "UNCLEAR_REQUEST": "I need more information to help with your request",
    "TECHNICAL_ERROR": "I encountered a technical issue while processing your request"
}
```

### 3. Monitoring & Observability
```python
# Key metrics to track
METRICS = {
    "a2a_requests_total": "Total A2A requests received",
    "a2a_response_time": "A2A response time distribution", 
    "mcp_tool_calls": "MCP tool execution counts",
    "simulation_success_rate": "Monte Carlo simulation success rate",
    "language_distribution": "Query language distribution"
}
```

### 4. Essential Audit Trail
```python
# Simple audit for high-value tracking
class AuditLog(BaseModel):
    timestamp: datetime
    correlation_id: str
    event_type: str  # "a2a_request", "simulation_complete", "error"
    source: str      # "main-agent", "user", "mcp-tool"
    project_id: Optional[int]
    success: bool
    processing_time_ms: int
    error_message: Optional[str]

class SimpleAuditLogger:
    async def log_interaction(self, correlation_id: str, event_type: str, 
                            source: str, success: bool, processing_time: int,
                            project_id: int = None, error: str = None):
        """Log only essential audit information"""
        log_entry = AuditLog(
            timestamp=datetime.now(),
            correlation_id=correlation_id,
            event_type=event_type,
            source=source,
            project_id=project_id,
            success=success,
            processing_time_ms=processing_time,
            error_message=error
        )
        # Store in database for analytics and debugging
        await self.db.store_audit_log(log_entry)

# Usage in main components
class RiskExecutor:
    def __init__(self):
        self.audit = SimpleAuditLogger()
    
    async def execute_plan(self, plan: Dict, correlation_id: str) -> Dict:
        start_time = time.time()
        try:
            result = await self._execute_tools(plan)
            
            # Log success
            await self.audit.log_interaction(
                correlation_id=correlation_id,
                event_type="simulation_complete",
                source="risk-assistant",
                success=True,
                processing_time=int((time.time() - start_time) * 1000),
                project_id=plan.get("project_id")
            )
            return result
            
        except Exception as e:
            # Log failure
            await self.audit.log_interaction(
                correlation_id=correlation_id,
                event_type="simulation_error", 
                source="risk-assistant",
                success=False,
                processing_time=int((time.time() - start_time) * 1000),
                error=str(e)
            )
            raise
```
```

### 5. Security Considerations
- **A2A Authentication**: Implement API keys or JWT tokens for agent authentication
- **Input Validation**: Strict validation of all inputs, especially project IDs
- **Rate Limiting**: Prevent abuse of computational resources
- **Data Privacy**: Ensure project data isolation and access controls
- **Audit Retention**: Secure storage and retention policies for audit logs

### 6. Testing Strategy
- **A2A Integration Tests**: Mock main agent interactions
- **MCP Tool Tests**: Validate tool schemas and execution
- **Protocol Compatibility**: Test with real Claude Desktop/VS Code
- **Load Testing**: Validate concurrent A2A and MCP requests
- **Audit Verification**: Ensure critical interactions are logged

## Key Benefits

- **Protocol Separation**: Clean interfaces for different interaction patterns
- **Unified Tool Layer**: Single MCP tool implementation serves all interfaces
- **Scalable Architecture**: Easy to add new protocols or tools
- **Language Agnostic**: Natural conversation in EN/ES/FR
- **Agent Ecosystem**: Integrates with broader AI agent infrastructure
- **Future-Proof**: Standard protocols enable easy integration with new tools

## Success Metrics

- **A2A Integration**: Successful communication with main agent
- **MCP Adoption**: Usage in Claude Desktop/VS Code environments
- **Response Quality**: Accurate tool selection and parameter extraction
- **Performance**: Sub-3s response times for standard simulations
- **Reliability**: 99%+ uptime and error handling coverage
