"""
Pydantic models for Monte Carlo simulation data validation.
Updated for normalized database structure with lookup tables.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
import pandas as pd


class CapexItem(BaseModel):
    """Capex item with cost distribution parameters."""
    item_id: int
    name: str
    owner: str
    p10_cost: float
    p90_cost: float
    base_date: datetime
    item_type: Optional[str] = None
    # Correlation attributes (normalized foreign keys)
    discipline_id: Optional[int] = None
    phase_id: Optional[int] = None
    location_id: Optional[int] = None
    
    class Config:
        from_attributes = True


class CapexAction(BaseModel):
    """Capex action with cost impact distribution."""
    action_id: int
    capex_item_id: int
    name: str
    owner: str
    p10_cost_impact: float
    p90_cost_impact: float
    probability: float = Field(default=1.0, ge=0, le=1)
    action_type: Optional[str] = None
    # Correlation attributes (normalized foreign keys)
    discipline_id: Optional[int] = None
    phase_id: Optional[int] = None
    location_id: Optional[int] = None
    
    class Config:
        from_attributes = True


class Risk(BaseModel):
    """Risk with impact distribution parameters."""
    risk_id: int
    name: str
    owner: str
    p10_impact: float
    p90_impact: float
    probability: float = Field(ge=0, le=1)
    # Correlation attributes (normalized foreign keys)
    discipline_id: Optional[int] = None
    phase_id: Optional[int] = None
    location_id: Optional[int] = None
    risk_category_id: Optional[int] = None
    risk_log_id: Optional[int] = None
    
    class Config:
        from_attributes = True


class RiskAction(BaseModel):
    """Risk action with impact reduction distribution."""
    action_id: int
    risk_id: int
    name: str
    owner: str
    p10_impact_reduction: float
    p90_impact_reduction: float
    probability_reduction: float = Field(default=0.0, ge=0, le=1)
    action_type: Optional[str] = None
    # Correlation attributes (normalized foreign keys)
    discipline_id: Optional[int] = None
    phase_id: Optional[int] = None
    location_id: Optional[int] = None
    
    class Config:
        from_attributes = True


# Lookup table models for reference
class Discipline(BaseModel):
    """Engineering discipline lookup."""
    discipline_id: int
    discipline_name: str
    discipline_code: Optional[str] = None
    description: Optional[str] = None
    
    class Config:
        from_attributes = True


class ProjectPhase(BaseModel):
    """Project phase lookup."""
    phase_id: int
    phase_name: str
    phase_code: Optional[str] = None
    phase_order: Optional[int] = None
    description: Optional[str] = None
    
    class Config:
        from_attributes = True


class Location(BaseModel):
    """Location lookup."""
    location_id: int
    location_name: str
    location_code: Optional[str] = None
    location_type: Optional[str] = None
    parent_location_id: Optional[int] = None
    description: Optional[str] = None
    
    class Config:
        from_attributes = True


class RiskCategory(BaseModel):
    """Risk category lookup."""
    risk_category_id: int
    category_name: str
    category_code: Optional[str] = None
    category_type: Optional[str] = None
    description: Optional[str] = None
    
    class Config:
        from_attributes = True


class RiskLog(BaseModel):
    """Risk log lookup."""
    risk_log_id: int
    log_name: str
    log_code: Optional[str] = None
    log_owner: Optional[str] = None
    description: Optional[str] = None
    
    class Config:
        from_attributes = True


class SimulationConfig(BaseModel):
    """Configuration for Monte Carlo simulation."""
    data_date: datetime
    frequency: str = Field(default="W", description="Time frequency for simulation")
    periods: Optional[int] = Field(default=52, description="Number of periods to simulate")
    n_simulations: int = Field(default=5000, ge=100, le=100000)
    enable_correlation: bool = Field(default=True, description="Enable correlation modeling")
    correlation_method: str = Field(default="category", description="Correlation method: 'none', 'category'")
    
    @validator('frequency')
    def validate_frequency(cls, v):
        valid_frequencies = ['D', 'W', 'M', 'Q', 'Y']
        if v not in valid_frequencies:
            raise ValueError(f'Frequency must be one of {valid_frequencies}')
        return v


class SimulationResult(BaseModel):
    """Result from Monte Carlo simulation with time evolution."""
    simulation_date: datetime
    config: SimulationConfig
    time_series: pd.DataFrame  # Time-based results with P10, P50, P90, mean columns
    summary_statistics: Dict[str, float]
    correlation_info: Optional[Dict[str, Any]] = None
    
    class Config:
        arbitrary_types_allowed = True
        
    @validator('summary_statistics')
    def validate_summary_stats(cls, v):
        required_keys = ['final_p10', 'final_p50', 'final_p90', 'final_mean', 'total_capex', 'total_risk_exposure']
        for key in required_keys:
            if key not in v:
                raise ValueError(f'Missing required summary statistic: {key}')
        return v


class CorrelationMatrix(BaseModel):
    """Correlation matrix information for transparency."""
    method: str
    entity_count: int
    correlation_pairs: List[Dict[str, Any]]
    matrix_shape: tuple
    avg_correlation: float
    
    class Config:
        from_attributes = True
