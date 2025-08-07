"""
Production script to update cost_analysis table with Monte Carlo simulation results.
"""

import pandas as pd
from datetime import datetime
import os
from dotenv import load_dotenv
from supabase import create_client
from app.montecarlo import MonteCarloEngine, SimulationConfig

# Load environment variables
load_dotenv()


def get_database_client():
    """Initialize Supabase client for database access."""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("Supabase credentials not found in environment variables")
    
    return create_client(supabase_url, supabase_key)


def fetch_input_data():
    """Fetch input data from database for Monte Carlo simulation."""
    client = get_database_client()
    
    # Fetch CAPEX items
    capex_response = client.table('capex_items').select('*').execute()
    capex_items = pd.DataFrame(capex_response.data) if capex_response.data else pd.DataFrame()
    
    # Fetch CAPEX actions  
    capex_actions_response = client.table('capex_actions').select('*').execute()
    capex_actions = pd.DataFrame(capex_actions_response.data) if capex_actions_response.data else pd.DataFrame()
    
    # Fetch Risks
    risks_response = client.table('risks').select('*').execute()
    risks = pd.DataFrame(risks_response.data) if risks_response.data else pd.DataFrame()
    
    # Fetch Risk actions
    risk_actions_response = client.table('risk_actions').select('*').execute()
    risk_actions = pd.DataFrame(risk_actions_response.data) if risk_actions_response.data else pd.DataFrame()
    
    # Check if we have any data
    if len(capex_items) == 0 and len(risks) == 0:
        raise ValueError("No data found in database. Please ensure your database contains CAPEX items or risks.")
    
    return capex_items, capex_actions, risks, risk_actions


def run_monte_carlo_simulation(capex_items, capex_actions, risks, risk_actions, 
                             correlation=True, simulations=10000):
    """Run Monte Carlo simulation with given data."""
    config = SimulationConfig(
        data_date=datetime.now(),
        n_simulations=simulations,
        enable_correlation=correlation,
        correlation_method="category" if correlation else "none"
    )
    
    engine = MonteCarloEngine(config)
    
    results = engine.simulate_cost_evolution(
        capex_items=capex_items,
        capex_actions=capex_actions,
        risks=risks,
        risk_actions=risk_actions,
        data_date=datetime.now()
    )
    
    return results


def save_to_cost_analysis(results_df, comments=None):
    """Save Monte Carlo final results to cost_analysis table."""
    client = get_database_client()
    final_result = results_df.iloc[-1]
    
    data = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'p20': float(final_result['p20']),
        'p50': float(final_result['p50']),
        'p80': float(final_result['p80']),
        'deterministic_level': float(final_result['deterministic']),
        'contingency_level': float(final_result['p80']),
        'comments': comments or f"Monte Carlo simulation - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    }
    
    result = client.table('cost_analysis').insert(data).execute()
    return result.data[0]['id']


def update_cost_analysis(correlation=True, simulations=10000, comments=None):
    """
    Main function to update cost_analysis table with Monte Carlo results.
    
    Args:
        correlation (bool): Enable correlation in simulation
        simulations (int): Number of Monte Carlo simulations
        comments (str): Optional comments for the analysis record
    
    Returns:
        dict: Summary of the operation
    """
    try:
        # Fetch input data
        print("Fetching input data from database...")
        capex_items, capex_actions, risks, risk_actions = fetch_input_data()
        
        print(f"Data loaded: {len(capex_items)} CAPEX items, {len(capex_actions)} CAPEX actions, "
              f"{len(risks)} risks, {len(risk_actions)} risk actions")
        
        # Run Monte Carlo simulation
        print(f"Running Monte Carlo simulation ({simulations} simulations, correlation={correlation})...")
        results = run_monte_carlo_simulation(
            capex_items, capex_actions, risks, risk_actions, 
            correlation=correlation, simulations=simulations
        )
        
        if results is None:
            raise Exception("Monte Carlo simulation failed")
        
        # Save to cost_analysis table
        print("Saving results to cost_analysis table...")
        record_id = save_to_cost_analysis(results, comments)
        
        # Prepare summary
        final_result = results.iloc[-1]
        summary = {
            "status": "success",
            "record_id": record_id,
            "simulation_config": {
                "correlation_enabled": correlation,
                "n_simulations": simulations,
                "data_counts": {
                    "capex_items": len(capex_items),
                    "capex_actions": len(capex_actions),
                    "risks": len(risks),
                    "risk_actions": len(risk_actions)
                }
            },
            "results": {
                "date": final_result['date'].strftime('%Y-%m-%d'),
                "p20": float(final_result['p20']),
                "p50": float(final_result['p50']),
                "p80": float(final_result['p80']),
                "deterministic": float(final_result['deterministic']),
                "uncertainty_range": float(final_result['p80'] - final_result['p20'])
            }
        }
        
        print(f"Successfully updated cost_analysis table (Record ID: {record_id})")
        print(f"Final P50: ${final_result['p50']:.2f}")
        print(f"Uncertainty range (P80-P20): ${final_result['p80'] - final_result['p20']:.2f}")
        
        return summary
        
    except Exception as e:
        error_summary = {
            "status": "error",
            "error": str(e)
        }
        print(f"Error: {e}")
        return error_summary


if __name__ == "__main__":
    # Run with default settings
    result = update_cost_analysis(
        correlation=True,
        simulations=10000,
        comments="Automated Monte Carlo update"
    )
    
    if result["status"] == "success":
        print(f"\nCost analysis updated successfully!")
        print(f"Record ID: {result['record_id']}")
    else:
        print(f"\nUpdate failed: {result['error']}")
