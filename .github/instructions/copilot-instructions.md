---
applyTo: '**'
---
# Copilot Instructions

    This project is a risk assistant/manager application that performs qualitative and quantitative risk analysis using Monte Carlo simulations, and based on the results, it generates risk mitigation plans. The Agent responds to risk-related queries and provides insights based on the data and the Monte Carlo simulations. This agent responds to a MAIN agent that manaages the overall project management and communication with the user. The MAINT agent communicates with the RISK agent through a (to be implemented) API agent/chat endpoint. The RISK agent is responsible for managing risk data, performing simulations, and consolidating results. It is powered by Gemini AI 2.5 llm models.

## Coding Guidelines


    IMPORTANT:When asked to perform database reviews or operations, use MCP for supabase project id kxwradnyjqobvdheklsn.
    When testing an app or part of it, prioritize activating venv and uploading the environment variables file.

    When asked to do a review of a codebase, focus on doing the review only: DO NOT IMPLEMENT CHANGES UNLESS EXPLICITLY REQUESTED.

    When asked to propose solutions to an issue, provide a detailed explanation of the solution, including code snippets if necessary, but DO NOT IMPLEMENT THE SOLUTION UNLESS EXPLICITLY REQUESTED.

    When asked to explain concepts or technologies, provide clear and concise explanations with examples where applicable.

    Do not include emojis or icons in the codebase for any reason.




# Libraries:
## Core dependencies for SharePoint Graph API access
python-dotenv==1.0.0
requests==2.31.0
msal==1.24.1

## Microsoft Graph SDK (recommended approach)
msgraph-sdk==1.0.0
azure-identity==1.15.0

## Communication Assistant API dependencies
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
email-validator==2.1.0

## Database integration
supabase==1.0.4

# HTML processing and email formatting
jinja2==3.1.2
markdown==3.5.1
bleach==6.1.0

## Configuration
toml==0.10.2

## AI/ML dependencies
google-generativeai==0.8.5