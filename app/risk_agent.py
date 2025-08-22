from __future__ import annotations
from typing import Dict, Any
import logging
from pathlib import Path

from app.config.settings import settings

logger = logging.getLogger(__name__)


class RiskAgent:
    """Stage 1 (interpret) and Stage 3 (respond) scaffolding.
    For Phase 1 we use simple heuristics instead of live Gemini calls.
    """

    def __init__(self):
        self.interpret_prompt = Path(__file__).parent / "prompts" / "query_interpretation.xml"
        self.response_prompt = Path(__file__).parent / "prompts" / "response_generation.xml"

    async def interpret_query(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        qlower = query.lower()
        language = context.get("language") or self._detect_language(qlower)
        plan: Dict[str, Any] = {
            "language": language,
            "intent": "run_monte_carlo_simulation" if any(k in qlower for k in ["monte carlo", "simulation", "riesgo", "simulación", "simulation de monte carlo"]) else "unknown",
            "tools": []
        }
        if plan["intent"] == "run_monte_carlo_simulation":
            plan["tools"].append({
                "order": 1,
                "tool": "run_monte_carlo_simulation",
                "parameters": {
                    "project_id": context.get("project_id"),
                    "iterations": context.get("iterations", 10000),
                    "enable_correlation": context.get("enable_correlation", True),
                    "data_date": context.get("data_date"),
                }
            })
        return plan

    async def generate_response(self, results: Dict[str, Any], language: str) -> str:
        # Very basic multilingual summaries for Phase 1
        ok = results.get("success") or (isinstance(results.get("timeseries"), list) and len(results.get("timeseries")) > 0)
        summary = {
            "en": "Monte Carlo simulation completed successfully." if ok else "Simulation failed.",
            "es": "La simulación de Monte Carlo se completó correctamente." if ok else "La simulación falló.",
            "fr": "La simulation de Monte Carlo s'est terminée avec succès." if ok else "Échec de la simulation.",
        }
        return summary.get(language, summary["en"])

    def _detect_language(self, text: str) -> str:
        if any(w in text for w in [" el ", " la ", " simulación", "riesgo", "costos"]):
            return "es"
        if any(w in text for w in [" le ", " la ", " simulation", "risque", "coûts"]):
            return "fr"
        return "en"
