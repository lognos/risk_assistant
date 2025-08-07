"""
Utility functions for Monte Carlo simulations.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def ensure_datetime(date_value: Any) -> datetime:
    """
    Convert various date formats to datetime.
    
    Args:
        date_value: Date in various formats
        
    Returns:
        datetime object
    """
    if isinstance(date_value, datetime):
        return date_value
    elif isinstance(date_value, str):
        return pd.to_datetime(date_value)
    elif isinstance(date_value, pd.Timestamp):
        return date_value.to_pydatetime()
    else:
        raise ValueError(f"Cannot convert {type(date_value)} to datetime")


def calculate_end_date(actions_df: pd.DataFrame, 
                      data_date: datetime,
                      buffer_weeks: int = 4) -> datetime:
    """
    Calculate simulation end date based on last action due date.
    
    Args:
        actions_df: DataFrame with action due dates
        data_date: Project start date
        buffer_weeks: Weeks to add after last action
        
    Returns:
        End date for simulation
    """
    if actions_df.empty:
        return data_date + timedelta(weeks=buffer_weeks)
    
    # Find latest due date
    date_columns = [col for col in actions_df.columns if 'due' in col.lower()]
    if not date_columns:
        return data_date + timedelta(weeks=buffer_weeks)
    
    latest_date = data_date
    for col in date_columns:
        max_date = pd.to_datetime(actions_df[col]).max()
        if pd.notna(max_date) and max_date > latest_date:
            latest_date = max_date
    
    return latest_date + timedelta(weeks=buffer_weeks)


def generate_checkpoints(start_date: datetime, 
                        end_date: datetime,
                        frequency: str = 'W') -> List[datetime]:
    """
    Generate checkpoint dates for simulation.
    
    Args:
        start_date: Start date
        end_date: End date
        frequency: Pandas frequency string (default 'W' for weekly)
        
    Returns:
        List of checkpoint dates
    """
    date_range = pd.date_range(start=start_date, end=end_date, freq=frequency)
    return date_range.to_pydatetime().tolist()


def filter_by_date(df: pd.DataFrame, 
                  date_column: str,
                  cutoff_date: datetime,
                  include_null: bool = True) -> pd.DataFrame:
    """
    Filter DataFrame by date column.
    
    Args:
        df: DataFrame to filter
        date_column: Name of date column
        cutoff_date: Cutoff date for filtering
        include_null: Whether to include rows with null dates
        
    Returns:
        Filtered DataFrame
    """
    if date_column not in df.columns:
        return df
    
    # Convert date column to datetime
    df[date_column] = pd.to_datetime(df[date_column])
    
    if include_null:
        mask = df[date_column].isna() | (df[date_column] <= cutoff_date)
    else:
        mask = df[date_column] <= cutoff_date
    
    return df[mask].copy()


def apply_latest_action(items_df: pd.DataFrame,
                       actions_df: pd.DataFrame,
                       item_col: str,
                       date_col: str,
                       checkpoint_date: datetime) -> pd.DataFrame:
    """
    Apply latest mitigation action for each item up to checkpoint date.
    
    Args:
        items_df: DataFrame with items (CAPEX or risks)
        actions_df: DataFrame with actions
        item_col: Column name for item ID
        date_col: Column name for action due date
        checkpoint_date: Current checkpoint date
        
    Returns:
        Updated items DataFrame with mitigation values
    """
    if actions_df.empty:
        return items_df
    
    # Filter actions up to checkpoint date
    valid_actions = filter_by_date(actions_df, date_col, checkpoint_date, include_null=False)
    
    if valid_actions.empty:
        return items_df
    
    # Sort by date to get latest action per item
    valid_actions = valid_actions.sort_values(date_col)
    
    # Get latest action per item
    latest_actions = valid_actions.groupby(item_col).last()
    
    # Merge with items
    result = items_df.merge(
        latest_actions,
        left_on=item_col,
        right_index=True,
        how='left',
        suffixes=('', '_action')
    )
    
    return result


def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """
    Calculate percentage change between values.
    
    Args:
        old_value: Previous value
        new_value: New value
        
    Returns:
        Percentage change
    """
    if old_value == 0:
        return 0.0 if new_value == 0 else float('inf')
    return ((new_value - old_value) / abs(old_value)) * 100


def format_impact_tracking(checkpoint_date: datetime,
                          p50_value: float,
                          previous_p50: float,
                          items: List[Dict[str, Any]],
                          impact_type: str) -> Dict[str, Any]:
    """
    Format impact tracking information for output.
    
    Args:
        checkpoint_date: Current checkpoint date
        p50_value: Current P50 value
        previous_p50: Previous P50 value
        items: List of items causing impact
        impact_type: Type of impact ('mitigation' or 'risk')
        
    Returns:
        Formatted impact dictionary
    """
    change = calculate_percentage_change(previous_p50, p50_value)
    
    return {
        'date': checkpoint_date,
        'p50': p50_value,
        'change': change,
        impact_type: items
    }


def validate_distribution_values(df: pd.DataFrame, 
                               value_columns: List[str],
                               name_column: str) -> List[str]:
    """
    Validate distribution values in DataFrame.
    
    Args:
        df: DataFrame to validate
        value_columns: Columns containing distribution values
        name_column: Column with item names for error messages
        
    Returns:
        List of validation errors
    """
    errors = []
    
    for idx, row in df.iterrows():
        values = []
        for col in value_columns:
            if col in df.columns and pd.notna(row[col]):
                values.append(row[col])
        
        if len(values) >= 3:  # min, ml, max
            if not (values[0] <= values[1] <= values[2]):
                name = row.get(name_column, f"Row {idx}")
                errors.append(f"{name}: Values not properly ordered: {values}")
            
            if any(v <= 0 for v in values):
                name = row.get(name_column, f"Row {idx}")
                errors.append(f"{name}: All values must be positive for lognormal distribution")
    
    return errors


def aggregate_simulation_results(simulations: np.ndarray, 
                               percentiles: List[int] = [20, 50, 80]) -> Dict[str, float]:
    """
    Calculate percentiles from simulation results.
    
    Args:
        simulations: Array of simulation results
        percentiles: List of percentiles to calculate
        
    Returns:
        Dictionary with percentile values
    """
    result = {}
    for p in percentiles:
        result[f'p{p}'] = float(np.percentile(simulations, p))
    return result
