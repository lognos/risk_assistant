"""
Statistical distribution utilities for Monte Carlo simulation.
"""

import numpy as np
from scipy import stats
from typing import Tuple, Dict, Any, Optional


class DistributionCalculator:
    """Handles statistical distribution calculations."""
    
    @staticmethod
    def calculate_lognormal_params(p10: float, p90: float) -> Tuple[float, float]:
        """
        Calculate lognormal distribution parameters (mu, sigma) from P10 and P90 values.
        
        Args:
            p10: 10th percentile value
            p90: 90th percentile value
            
        Returns:
            Tuple of (mu, sigma) for lognormal distribution
        """
        if p10 <= 0 or p90 <= 0:
            raise ValueError("P10 and P90 must be positive for lognormal distribution")
        if p10 >= p90:
            raise ValueError("P10 must be less than P90")
            
        # Standard normal percentiles
        z10 = stats.norm.ppf(0.10)  # -1.2816
        z90 = stats.norm.ppf(0.90)  # 1.2816
        
        # Calculate lognormal parameters
        sigma = (np.log(p90) - np.log(p10)) / (z90 - z10)
        mu = np.log(p10) - z10 * sigma
        
        return mu, sigma
    
    @staticmethod
    def sample_lognormal(mu: float, sigma: float, size: int, 
                        random_state: Optional[np.random.RandomState] = None) -> np.ndarray:
        """
        Generate samples from lognormal distribution.
        
        Args:
            mu: Mean of underlying normal distribution
            sigma: Standard deviation of underlying normal distribution
            size: Number of samples
            random_state: Random state for reproducibility
            
        Returns:
            Array of samples
        """
        if random_state is None:
            random_state = np.random.RandomState()
            
        return random_state.lognormal(mu, sigma, size)
    
    @staticmethod
    def validate_percentiles(p10: float, p50: float, p90: float) -> bool:
        """
        Validate that percentile values are properly ordered.
        
        Args:
            p10: 10th percentile
            p50: 50th percentile (median)
            p90: 90th percentile
            
        Returns:
            True if valid, raises ValueError otherwise
        """
        if not (p10 <= p50 <= p90):
            raise ValueError(f"Percentiles must be ordered: P10({p10}) <= P50({p50}) <= P90({p90})")
        if p10 <= 0:
            raise ValueError("All percentile values must be positive for lognormal distribution")
        return True
    
    @staticmethod
    def calculate_deterministic(values: Dict[str, float], method: str = "expected") -> float:
        """
        Calculate deterministic estimate from distribution parameters.
        
        Args:
            values: Dictionary containing min, ml, and max values
            method: Method to use ('expected', 'ml', 'pert')
            
        Returns:
            Deterministic estimate
        """
        if method == "ml":
            return values.get('ml', values.get('ml_cost', values.get('ml_impact', 0)))
        elif method == "pert":
            # PERT estimate: (min + 4*ml + max) / 6
            min_val = values.get('min', values.get('min_cost', values.get('min_impact', 0)))
            ml_val = values.get('ml', values.get('ml_cost', values.get('ml_impact', 0)))
            max_val = values.get('max', values.get('max_cost', values.get('max_impact', 0)))
            return (min_val + 4 * ml_val + max_val) / 6
        else:  # expected value from lognormal
            min_val = values.get('min', values.get('min_cost', values.get('min_impact', 0)))
            max_val = values.get('max', values.get('max_cost', values.get('max_impact', 0)))
            mu, sigma = DistributionCalculator.calculate_lognormal_params(min_val, max_val)
            return np.exp(mu + sigma**2 / 2)


class DistributionFactory:
    """
    Factory for creating different distribution types.
    Placeholder for future distribution extensions.
    """
    
    SUPPORTED_DISTRIBUTIONS = ['lognormal']  # Future: 'beta', 'triangular', 'uniform'
    
    @staticmethod
    def create_distribution(dist_type: str = 'lognormal') -> DistributionCalculator:
        """
        Create distribution calculator based on type.
        
        Args:
            dist_type: Type of distribution
            
        Returns:
            Distribution calculator instance
        """
        if dist_type not in DistributionFactory.SUPPORTED_DISTRIBUTIONS:
            raise ValueError(f"Unsupported distribution type: {dist_type}")
        
        # For now, only lognormal is implemented
        return DistributionCalculator()
    
    @staticmethod
    def get_distribution_params(dist_type: str, **kwargs) -> Dict[str, Any]:
        """
        Get distribution parameters based on type and input values.
        Placeholder for future distribution types.
        
        Args:
            dist_type: Type of distribution
            **kwargs: Distribution-specific parameters
            
        Returns:
            Dictionary of distribution parameters
        """
        if dist_type == 'lognormal':
            p10 = kwargs.get('p10') or kwargs.get('min')
            p90 = kwargs.get('p90') or kwargs.get('max')
            mu, sigma = DistributionCalculator.calculate_lognormal_params(p10, p90)
            return {'mu': mu, 'sigma': sigma, 'type': 'lognormal'}
        else:
            raise NotImplementedError(f"Distribution type {dist_type} not yet implemented")
