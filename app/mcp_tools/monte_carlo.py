from __future__ import annotations
from typing import Dict, Any, Optional, Union
from datetime import datetime
import pandas as pd

from app.montecarlo.mc_engine import MonteCarloEngine
from app.montecarlo.mc_models import SimulationConfig


class MonteCarloTool:
    name = "run_monte_carlo_simulation"

    def __init__(self):
        pass

    def run(self, *, project_id: Union[str, int], data_date: Optional[str] = None,
            iterations: int = 10000, enable_correlation: bool = True, db_loader=None) -> Dict[str, Any]:
        # Load data from DB via provided loader callback to avoid direct coupling here
        if db_loader is None:
            raise ValueError("db_loader is required to fetch project data")

        try:
            capex_items, capex_actions, risks, risk_actions = db_loader(project_id)
        except Exception as e:
            return {
                "success": False,
                "error": {
                    "code": "DATA_SOURCE_UNAVAILABLE",
                    "message": "Failed to load project data",
                    "details": {"project_id": project_id, "reason": str(e)},
                },
            }

        # Build config
        cfg = SimulationConfig(
            data_date=datetime.fromisoformat(data_date) if data_date else datetime.utcnow(),
            frequency="W",
            periods=None,  # Horizon determined by action due dates + buffer inside the engine
            n_simulations=min(max(iterations, 100), 50000),
            enable_correlation=enable_correlation,
        )

        engine = MonteCarloEngine(config=cfg)
        results_df = engine.simulate_cost_evolution(
            capex_items=capex_items,
            capex_actions=capex_actions,
            risks=risks,
            risk_actions=risk_actions,
            data_date=cfg.data_date,
            frequency=cfg.frequency,
            periods=cfg.periods,
        )

        if results_df is None or not isinstance(results_df, pd.DataFrame) or results_df.empty:
            return {
                "success": False,
                "error": {
                    "code": "INSUFFICIENT_DATA",
                    "message": "Simulation failed validation or returned no data",
                    "details": {
                        "capex_items": len(capex_items.index),
                        "capex_actions": len(capex_actions.index),
                        "risks": len(risks.index),
                        "risk_actions": len(risk_actions.index),
                    },
                },
            }

        # Prepare compact summary
        final_row = results_df.iloc[-1]
        summary = {
            "final_date": final_row["date"].isoformat() if hasattr(final_row["date"], "isoformat") else str(final_row["date"]),
            "p20": float(final_row.get("p20", 0.0)),
            "p50": float(final_row.get("p50", 0.0)),
            "p80": float(final_row.get("p80", 0.0)),
            "deterministic": float(final_row.get("deterministic", 0.0)),
        }

        # Convert small head of timeseries for client
        timeseries = results_df[["date", "p20", "p50", "p80", "deterministic"]].copy()
        timeseries["date"] = timeseries["date"].astype(str)

        return {
            "success": True,
            "summary": summary,
            "timeseries": timeseries.to_dict(orient="records"),
        }
