"""
Main Monte Carlo simulation engine for project cost evolution.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import logging
import traceback

from .mc_distributions import DistributionCalculator, DistributionFactory
from .mc_correlations import CorrelationEngine
from .mc_utils import (
    ensure_datetime, calculate_end_date, generate_checkpoints,
    filter_by_date, apply_latest_action, calculate_percentage_change,
    format_impact_tracking, aggregate_simulation_results
)
from .mc_validators import DataValidator
from .mc_models import SimulationConfig

logger = logging.getLogger(__name__)


class MonteCarloEngine:
    """
    Monte Carlo simulation engine for time-based cost evolution analysis.
    """
    
    def __init__(self, config: Optional[SimulationConfig] = None):
        """
        Initialize Monte Carlo engine.
        
        Args:
            config: Simulation configuration
        """
        self.config = config or SimulationConfig()
        self.distribution_calc = DistributionCalculator()
        self.correlation_engine = CorrelationEngine(
            method="category" if config and config.enable_correlation else "none"
        )
        self._simulation_cache = {}
    
    def simulate_cost_evolution(self,
                               capex_items: pd.DataFrame,
                               capex_actions: pd.DataFrame,
                               risks: pd.DataFrame,
                               risk_actions: pd.DataFrame,
                               data_date: datetime,
                               frequency: str = "W",
                               periods: Optional[int] = None) -> Optional[pd.DataFrame]:
        """
        Simulate project cost evolution over time using Monte Carlo analysis.
        
        Args:
            capex_items: DataFrame with CAPEX items
            capex_actions: DataFrame with CAPEX mitigation actions
            risks: DataFrame with risks
            risk_actions: DataFrame with risk mitigation actions
            data_date: Project start date
            frequency: Checkpoint frequency (fixed to 'W')
            periods: Number of periods (auto-calculated if None)
            
        Returns:
            DataFrame with simulation results or None on error
        """
        try:
            logger.info("Starting Monte Carlo cost evolution simulation")
            
            # Validate inputs
            validation_results = DataValidator.validate_all_inputs(
                capex_items, capex_actions, risks, risk_actions
            )
            if DataValidator.has_errors(validation_results):
                logger.error("Input validation failed")
                for category, errors in validation_results.items():
                    if errors:
                        logger.error(f"{category}: {errors}")
                return None
            
            # Convert dates
            data_date = ensure_datetime(data_date)
            
            # Filter risks by log date (include risks without log date)
            if 'risk_log' in risks.columns:
                risks = filter_by_date(risks, 'risk_log', data_date, include_null=True)
            
            # Calculate simulation end date
            all_actions = pd.concat([capex_actions, risk_actions], ignore_index=True)
            end_date = calculate_end_date(all_actions, data_date)
            
            # Generate checkpoints
            checkpoints = generate_checkpoints(data_date, end_date, frequency)
            logger.info(f"Generated {len(checkpoints)} checkpoints from {data_date} to {end_date}")
            
            # Initialize results
            results = []
            previous_result = None
            mitigation_impacts = []
            risk_impacts = []
            
            # Track active risks for each checkpoint
            active_risks_tracker = set()
            
            for checkpoint in checkpoints:
                logger.debug(f"Processing checkpoint: {checkpoint}")
                
                # Check for changes since last checkpoint
                changes_detected = False
                new_actions = []
                new_risks = []
                
                # Check for new mitigation actions
                if not capex_actions.empty:
                    new_capex_actions = self._get_new_actions(
                        capex_actions, 'cost_action_due', 
                        checkpoints[checkpoints.index(checkpoint) - 1] if checkpoint != checkpoints[0] else None,
                        checkpoint
                    )
                    if not new_capex_actions.empty:
                        changes_detected = True
                        new_actions.extend(new_capex_actions.to_dict('records'))
                
                if not risk_actions.empty:
                    new_risk_actions = self._get_new_actions(
                        risk_actions, 'risk_action_due',
                        checkpoints[checkpoints.index(checkpoint) - 1] if checkpoint != checkpoints[0] else None,
                        checkpoint
                    )
                    if not new_risk_actions.empty:
                        changes_detected = True
                        new_actions.extend(new_risk_actions.to_dict('records'))
                
                # Check for new risks
                if 'risk_log' in risks.columns:
                    current_risks = filter_by_date(risks, 'risk_log', checkpoint, include_null=True)
                    new_risk_ids = set(current_risks['risk_id']) - active_risks_tracker
                    if new_risk_ids:
                        changes_detected = True
                        new_risks = current_risks[current_risks['risk_id'].isin(new_risk_ids)].to_dict('records')
                        active_risks_tracker.update(new_risk_ids)
                else:
                    current_risks = risks
                
                # Run simulation if changes detected or first checkpoint
                if changes_detected or checkpoint == checkpoints[0]:
                    # Apply mitigations up to checkpoint
                    mitigated_capex = self._apply_mitigations(
                        capex_items, capex_actions, 'item_id', 'cost_action_due', checkpoint
                    )
                    mitigated_risks = self._apply_risk_mitigations(
                        current_risks, risk_actions, 'risk_id', 'risk_action_due', checkpoint
                    )
                    
                    # Run Monte Carlo simulation
                    simulation_result = self._run_monte_carlo(
                        mitigated_capex, mitigated_risks, checkpoint
                    )
                    
                    # Calculate deterministic estimate
                    deterministic = self._calculate_deterministic(mitigated_capex, mitigated_risks)
                    
                    # Track impacts
                    if previous_result and new_actions:
                        mitigation_impact = format_impact_tracking(
                            checkpoint, simulation_result['p50'],
                            previous_result['p50'], new_actions, 'actions'
                        )
                        mitigation_impacts.append(mitigation_impact)
                    
                    if previous_result and new_risks:
                        risk_impact = format_impact_tracking(
                            checkpoint, simulation_result['p50'],
                            previous_result['p50'], new_risks, 'risks'
                        )
                        risk_impacts.append(risk_impact)
                    
                    # Store result
                    result = {
                        'date': checkpoint,
                        **simulation_result,
                        'deterministic': deterministic
                    }
                    results.append(result)
                    previous_result = result
                    
                else:
                    # No changes, carry forward previous result
                    if previous_result:
                        result = {
                            'date': checkpoint,
                            **{k: v for k, v in previous_result.items() if k != 'date'}
                        }
                        results.append(result)
            
            # Create output DataFrame
            output_df = pd.DataFrame(results)
            
            # Add impact tracking
            output_df['mitigation_impacts'] = [mitigation_impacts] * len(output_df)
            output_df['risk_impacts'] = [risk_impacts] * len(output_df)
            
            logger.info("Monte Carlo simulation completed successfully")
            return output_df
            
        except Exception as e:
            logger.error(f"Error in Monte Carlo simulation: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    
    def _run_monte_carlo(self,
                        capex_items: pd.DataFrame,
                        risks: pd.DataFrame,
                        checkpoint_date: datetime) -> Dict[str, float]:
        """
        Run Monte Carlo simulation for a specific checkpoint.
        
        Args:
            capex_items: DataFrame with CAPEX items (potentially mitigated)
            risks: DataFrame with risks (potentially mitigated)
            checkpoint_date: Current checkpoint date
            
        Returns:
            Dictionary with percentile results
        """
        n_sims = self.config.n_simulations
        
        # Build correlation matrix if enabled
        if self.config.enable_correlation:
            correlation_matrix = self.correlation_engine.build_correlation_matrix(
                capex_items, risks
            )
            corr_summary = self.correlation_engine.get_correlation_summary(correlation_matrix)
            logger.debug(f"Correlation summary: {corr_summary}")
        else:
            n_total = len(capex_items) + len(risks)
            correlation_matrix = np.eye(n_total)
        
        # Generate correlated uniform samples if needed
        if self.config.enable_correlation and correlation_matrix.shape[0] > 0:
            uniform_samples = self.correlation_engine.generate_correlated_samples(
                correlation_matrix.shape[0], n_sims, correlation_matrix,
                random_state=np.random.RandomState(42)  # For reproducibility
            )
        else:
            # Independent sampling
            n_vars = len(capex_items) + len(risks)
            uniform_samples = np.random.uniform(0, 1, (n_sims, n_vars))
        
        # Initialize cost array
        total_costs = np.zeros(n_sims)
        
        # Sample CAPEX costs
        for idx, (_, item) in enumerate(capex_items.iterrows()):
            # Use post-mitigation values if available
            min_cost = item.get('pm_min_cost', item['min_cost'])
            max_cost = item.get('pm_max_cost', item['max_cost'])
            
            if pd.notna(min_cost) and pd.notna(max_cost) and min_cost > 0 and max_cost > 0:
                mu, sigma = self.distribution_calc.calculate_lognormal_params(min_cost, max_cost)
                
                # Transform uniform to lognormal using inverse CDF
                from scipy.stats import lognorm
                costs = lognorm.ppf(uniform_samples[:, idx], s=sigma, scale=np.exp(mu))
                total_costs += costs
        
        # Sample risk impacts
        risk_start_idx = len(capex_items)
        for idx, (_, risk) in enumerate(risks.iterrows()):
            # Use post-mitigation values if available
            min_impact = risk.get('pm_min_impact', risk['min_impact'])
            max_impact = risk.get('pm_max_impact', risk['max_impact'])
            probability = risk.get('pm_risk_probability', risk['risk_probability'])
            
            if pd.notna(min_impact) and pd.notna(max_impact) and pd.notna(probability):
                if min_impact > 0 and max_impact > 0:
                    mu, sigma = self.distribution_calc.calculate_lognormal_params(min_impact, max_impact)
                    
                    # Transform uniform to lognormal
                    from scipy.stats import lognorm
                    impacts = lognorm.ppf(uniform_samples[:, risk_start_idx + idx], s=sigma, scale=np.exp(mu))
                    
                    # Apply probability (independent of correlation for now)
                    risk_occurs = np.random.uniform(0, 1, n_sims) < probability
                    total_costs += impacts * risk_occurs
        
        # Calculate percentiles
        return aggregate_simulation_results(total_costs, [20, 50, 80])
    
    def _apply_mitigations(self,
                          items_df: pd.DataFrame,
                          actions_df: pd.DataFrame,
                          item_col: str,
                          date_col: str,
                          checkpoint_date: datetime) -> pd.DataFrame:
        """
        Apply CAPEX mitigations up to checkpoint date.
        
        Args:
            items_df: CAPEX items DataFrame
            actions_df: CAPEX actions DataFrame
            item_col: Column name for item ID
            date_col: Column name for action due date
            checkpoint_date: Current checkpoint
            
        Returns:
            DataFrame with mitigated values
        """
        result = items_df.copy()
        
        if actions_df.empty:
            return result
        
        # Apply latest action for each item
        result = apply_latest_action(result, actions_df, item_col, date_col, checkpoint_date)
        
        # Update cost columns with post-mitigation values where available
        pm_cols = ['pm_min_cost', 'pm_ml_cost', 'pm_max_cost']
        for col in pm_cols:
            if col in result.columns:
                # Only update where post-mitigation values exist
                mask = result[col].notna()
                if mask.any():
                    base_col = col.replace('pm_', '')
                    result.loc[mask, base_col] = result.loc[mask, col]
        
        return result
    
    def _apply_risk_mitigations(self,
                               risks_df: pd.DataFrame,
                               actions_df: pd.DataFrame,
                               risk_col: str,
                               date_col: str,
                               checkpoint_date: datetime) -> pd.DataFrame:
        """
        Apply risk mitigations up to checkpoint date.
        
        Args:
            risks_df: Risks DataFrame
            actions_df: Risk actions DataFrame
            risk_col: Column name for risk ID
            date_col: Column name for action due date
            checkpoint_date: Current checkpoint
            
        Returns:
            DataFrame with mitigated values
        """
        result = risks_df.copy()
        
        if actions_df.empty:
            return result
        
        # Apply latest action for each risk
        result = apply_latest_action(result, actions_df, risk_col, date_col, checkpoint_date)
        
        # Update impact columns and probability with post-mitigation values
        pm_cols = ['pm_min_impact', 'pm_ml_impact', 'pm_max_impact', 'pm_risk_probability']
        for col in pm_cols:
            if col in result.columns:
                mask = result[col].notna()
                if mask.any():
                    base_col = col.replace('pm_', '')
                    result.loc[mask, base_col] = result.loc[mask, col]
        
        return result
    
    def _calculate_deterministic(self,
                               capex_items: pd.DataFrame,
                               risks: pd.DataFrame) -> float:
        """
        Calculate deterministic cost estimate.
        
        Args:
            capex_items: CAPEX items DataFrame
            risks: Risks DataFrame
            
        Returns:
            Deterministic cost estimate
        """
        total = 0.0
        
        # Sum CAPEX ML costs
        if 'ml_cost' in capex_items.columns:
            total += capex_items['ml_cost'].fillna(0).sum()
        
        # Sum expected risk impacts
        if 'ml_impact' in risks.columns and 'risk_probability' in risks.columns:
            expected_impacts = risks['ml_impact'].fillna(0) * risks['risk_probability'].fillna(0)
            total += expected_impacts.sum()
        
        return total
    
    def _get_new_actions(self,
                        actions_df: pd.DataFrame,
                        date_col: str,
                        previous_checkpoint: Optional[datetime],
                        current_checkpoint: datetime) -> pd.DataFrame:
        """
        Get actions completed between checkpoints.
        
        Args:
            actions_df: Actions DataFrame
            date_col: Date column name
            previous_checkpoint: Previous checkpoint (None for first)
            current_checkpoint: Current checkpoint
            
        Returns:
            DataFrame with new actions
        """
        if actions_df.empty or date_col not in actions_df.columns:
            return pd.DataFrame()
        
        actions_df[date_col] = pd.to_datetime(actions_df[date_col])
        
        if previous_checkpoint is None:
            # First checkpoint - get all actions up to current
            mask = actions_df[date_col] <= current_checkpoint
        else:
            # Get actions between checkpoints
            mask = (actions_df[date_col] > previous_checkpoint) & (actions_df[date_col] <= current_checkpoint)
        
        return actions_df[mask]
