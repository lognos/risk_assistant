"""
Correlation modeling for Monte Carlo simulations.
Updated for normalized database structure with lookup tables.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Union, Tuple
from scipy.stats import multivariate_normal
import logging
import os

logger = logging.getLogger(__name__)


def get_database_client():
    """Get Supabase client if available."""
    try:
        from supabase import create_client
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if supabase_url and supabase_key:
            return create_client(supabase_url, supabase_key)
    except ImportError:
        pass
    return None


class CorrelationManager:
    """Manages correlation modeling between entities."""
    
    def __init__(self):
        # Try to get database connection, but don't fail if not available
        self.supabase = get_database_client()
    
    def build_correlation_matrix(self, 
                                entities: List[Union[Any]], 
                                method: str = "category") -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Build correlation matrix using normalized lookup table relationships.
        
        Args:
            entities: List of entity objects (CapexItem, Risk, etc.)
            method: Correlation method ('none', 'category')
            
        Returns:
            Tuple of (correlation_matrix, correlation_info)
        """
        n_entities = len(entities)
        
        if method == "none" or n_entities <= 1:
            return np.eye(n_entities), {"method": method, "correlations": 0}
        
        if method == "category":
            return self._build_category_correlation_matrix(entities)
        
        # Default to identity matrix
        logger.warning(f"Unknown correlation method: {method}. Using identity matrix.")
        return np.eye(n_entities), {"method": "identity", "correlations": 0}
    
    def _build_category_correlation_matrix(self, entities: List[Any]) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Build correlation matrix based on normalized category relationships."""
        n_entities = len(entities)
        correlation_matrix = np.eye(n_entities)
        correlation_info = {
            "method": "category",
            "total_pairs": 0,
            "correlation_details": []
        }
        
        # Get lookup table data for efficient correlation calculation
        lookup_data = self._fetch_lookup_data()
        
        for i in range(n_entities):
            for j in range(i + 1, n_entities):
                correlation = self._calculate_pairwise_correlation(
                    entities[i], entities[j], lookup_data
                )
                
                if correlation > 0:
                    correlation_matrix[i, j] = correlation
                    correlation_matrix[j, i] = correlation
                    correlation_info["total_pairs"] += 1
                    correlation_info["correlation_details"].append({
                        "entity_i": i,
                        "entity_j": j, 
                        "correlation": correlation,
                        "reason": self._get_correlation_reason(entities[i], entities[j], lookup_data)
                    })
        
        # Ensure positive definiteness
        correlation_matrix = self._ensure_positive_definite(correlation_matrix)
        
        correlation_info["avg_correlation"] = (
            np.sum(correlation_matrix) - n_entities) / (n_entities * (n_entities - 1))
        
        logger.info(f"Built correlation matrix: {n_entities}x{n_entities}, "
                   f"{correlation_info['total_pairs']} correlated pairs, "
                   f"avg correlation: {correlation_info['avg_correlation']:.3f}")
        
        return correlation_matrix, correlation_info
    
    def _fetch_lookup_data(self) -> Dict[str, pd.DataFrame]:
        """Fetch lookup table data for efficient correlation calculations."""
        lookup_data = {}
        
        try:
            # Fetch disciplines
            disciplines = self.supabase.table('disciplines').select('*').execute()
            lookup_data['disciplines'] = pd.DataFrame(disciplines.data)
            
            # Fetch phases  
            phases = self.supabase.table('project_phases').select('*').execute()
            lookup_data['phases'] = pd.DataFrame(phases.data)
            
            # Fetch locations
            locations = self.supabase.table('locations').select('*').execute()
            lookup_data['locations'] = pd.DataFrame(locations.data)
            
            # Fetch risk categories
            risk_categories = self.supabase.table('risk_categories').select('*').execute()
            lookup_data['risk_categories'] = pd.DataFrame(risk_categories.data)
            
            # Fetch risk logs
            risk_logs = self.supabase.table('risk_logs').select('*').execute()  
            lookup_data['risk_logs'] = pd.DataFrame(risk_logs.data)
            
        except Exception as e:
            logger.warning(f"Error fetching lookup data: {e}")
            # Return empty DataFrames as fallback
            lookup_data = {key: pd.DataFrame() for key in ['disciplines', 'phases', 'locations', 'risk_categories', 'risk_logs']}
        
        return lookup_data
    
    def _calculate_pairwise_correlation(self, 
                                      entity1: Any, 
                                      entity2: Any, 
                                      lookup_data: Dict[str, pd.DataFrame]) -> float:
        """Calculate correlation between two entities based on their attributes."""
        correlation = 0.0
        
        # Owner correlation (highest priority)
        if hasattr(entity1, 'owner') and hasattr(entity2, 'owner'):
            if entity1.owner == entity2.owner:
                correlation = max(correlation, 0.5)
        
        # Discipline correlation
        if (hasattr(entity1, 'discipline_id') and hasattr(entity2, 'discipline_id') and
            entity1.discipline_id and entity2.discipline_id):
            if entity1.discipline_id == entity2.discipline_id:
                correlation = max(correlation, 0.4)
        
        # Phase correlation
        if (hasattr(entity1, 'phase_id') and hasattr(entity2, 'phase_id') and
            entity1.phase_id and entity2.phase_id):
            if entity1.phase_id == entity2.phase_id:
                correlation = max(correlation, 0.3)
            else:
                # Adjacent phases get moderate correlation
                phase_correlation = self._get_phase_proximity_correlation(
                    entity1.phase_id, entity2.phase_id, lookup_data['phases']
                )
                correlation = max(correlation, phase_correlation)
        
        # Location correlation  
        if (hasattr(entity1, 'location_id') and hasattr(entity2, 'location_id') and
            entity1.location_id and entity2.location_id):
            if entity1.location_id == entity2.location_id:
                correlation = max(correlation, 0.3)
            else:
                # Hierarchical location correlation
                location_correlation = self._get_location_hierarchy_correlation(
                    entity1.location_id, entity2.location_id, lookup_data['locations']
                )
                correlation = max(correlation, location_correlation)
        
        # Risk-specific correlations
        if (hasattr(entity1, 'risk_category_id') and hasattr(entity2, 'risk_category_id') and
            entity1.risk_category_id and entity2.risk_category_id):
            if entity1.risk_category_id == entity2.risk_category_id:
                correlation = max(correlation, 0.4)
        
        if (hasattr(entity1, 'risk_log_id') and hasattr(entity2, 'risk_log_id') and
            entity1.risk_log_id and entity2.risk_log_id):
            if entity1.risk_log_id == entity2.risk_log_id:
                correlation = max(correlation, 0.2)
        
        return min(correlation, 0.8)  # Cap at 0.8 to avoid perfect correlation
    
    def _get_phase_proximity_correlation(self, 
                                        phase1_id: int, 
                                        phase2_id: int, 
                                        phases_df: pd.DataFrame) -> float:
        """Get correlation based on phase proximity."""
        if phases_df.empty:
            return 0.0
        
        try:
            phase1_order = phases_df[phases_df['phase_id'] == phase1_id]['phase_order'].iloc[0]
            phase2_order = phases_df[phases_df['phase_id'] == phase2_id]['phase_order'].iloc[0]
            
            if pd.isna(phase1_order) or pd.isna(phase2_order):
                return 0.0
            
            distance = abs(phase1_order - phase2_order)
            
            # Adjacent phases: 0.2, phases within 2 steps: 0.1
            if distance == 1:
                return 0.2
            elif distance == 2:
                return 0.1
            else:
                return 0.0
                
        except (IndexError, KeyError):
            return 0.0
    
    def _get_location_hierarchy_correlation(self, 
                                          location1_id: int, 
                                          location2_id: int, 
                                          locations_df: pd.DataFrame) -> float:
        """Get correlation based on location hierarchy."""
        if locations_df.empty:
            return 0.0
        
        try:
            loc1 = locations_df[locations_df['location_id'] == location1_id].iloc[0]
            loc2 = locations_df[locations_df['location_id'] == location2_id].iloc[0]
            
            # Check if one is parent of another
            if loc1['parent_location_id'] == location2_id or loc2['parent_location_id'] == location1_id:
                return 0.2
            
            # Check if they share the same parent
            if (not pd.isna(loc1['parent_location_id']) and 
                not pd.isna(loc2['parent_location_id']) and
                loc1['parent_location_id'] == loc2['parent_location_id']):
                return 0.15
            
            return 0.0
            
        except (IndexError, KeyError):
            return 0.0
    
    def _get_correlation_reason(self, 
                              entity1: Any, 
                              entity2: Any, 
                              lookup_data: Dict[str, pd.DataFrame]) -> str:
        """Get human-readable reason for correlation."""
        reasons = []
        
        # Check owner
        if hasattr(entity1, 'owner') and hasattr(entity2, 'owner'):
            if entity1.owner == entity2.owner:
                reasons.append(f"same_owner: {entity1.owner}")
        
        # Check discipline
        if (hasattr(entity1, 'discipline_id') and hasattr(entity2, 'discipline_id') and
            entity1.discipline_id == entity2.discipline_id and entity1.discipline_id):
            try:
                discipline_name = lookup_data['disciplines'][
                    lookup_data['disciplines']['discipline_id'] == entity1.discipline_id
                ]['discipline_name'].iloc[0]
                reasons.append(f"same_discipline: {discipline_name}")
            except (IndexError, KeyError):
                reasons.append(f"same_discipline: {entity1.discipline_id}")
        
        # Check phase
        if (hasattr(entity1, 'phase_id') and hasattr(entity2, 'phase_id') and
            entity1.phase_id == entity2.phase_id and entity1.phase_id):
            try:
                phase_name = lookup_data['phases'][
                    lookup_data['phases']['phase_id'] == entity1.phase_id
                ]['phase_name'].iloc[0]
                reasons.append(f"same_phase: {phase_name}")
            except (IndexError, KeyError):
                reasons.append(f"same_phase: {entity1.phase_id}")
        
        return "; ".join(reasons) if reasons else "other_factors"
    
    def _ensure_positive_definite(self, matrix: np.ndarray) -> np.ndarray:
        """Ensure correlation matrix is positive definite."""
        try:
            # Check if already positive definite
            np.linalg.cholesky(matrix)
            return matrix
        except np.linalg.LinAlgError:
            # Make positive definite using eigenvalue adjustment
            eigenvals, eigenvects = np.linalg.eigh(matrix)
            eigenvals = np.maximum(eigenvals, 1e-6)  # Ensure positive eigenvalues
            return eigenvects @ np.diag(eigenvals) @ eigenvects.T
    
    def apply_correlation_to_samples(self, 
                                   independent_samples: np.ndarray,
                                   correlation_matrix: np.ndarray) -> np.ndarray:
        """Apply correlation structure to independent samples."""
        if correlation_matrix.shape[0] != independent_samples.shape[1]:
            raise ValueError("Correlation matrix size must match number of entities")
        
        try:
            # Use Cholesky decomposition for correlation
            L = np.linalg.cholesky(correlation_matrix)
            
            # Transform independent samples to correlated samples
            correlated_samples = independent_samples @ L.T
            
            logger.debug(f"Applied correlation to {independent_samples.shape[0]} samples "
                        f"across {independent_samples.shape[1]} entities")
            
            return correlated_samples
            
        except np.linalg.LinAlgError:
            logger.warning("Cholesky decomposition failed, using independent samples")
            return independent_samples

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from scipy.linalg import cholesky, LinAlgError
import logging

logger = logging.getLogger(__name__)


class CorrelationEngine:
    """Handles correlation identification and matrix generation."""
    
    # Category-based correlation coefficients
    CORRELATION_RULES = {
        # Same attribute correlations
        "same_owner": 0.3,          # Items managed by same person
        "same_discipline": 0.4,     # E.g., all electrical items
        "same_phase": 0.2,          # Items in same project phase
        "same_location": 0.5,       # Items in same physical location
        
        # Risk category correlations
        "same_risk_category": {
            "regulatory": 0.6,      # Regulatory risks often trigger together
            "weather": 0.7,         # Weather impacts multiple items
            "supply_chain": 0.5,    # Supply issues affect related items
            "technical": 0.4,       # Technical risks may cascade
            "financial": 0.5,       # Financial risks often correlated
        }
    }
    
    def __init__(self, method: str = "none"):
        """
        Initialize correlation engine.
        
        Args:
            method: Correlation method ('none' for Phase 1, 'category' for Phase 2)
        """
        self.method = method
        self._correlation_cache = {}
    
    def build_correlation_matrix(self, 
                               capex_items_df: pd.DataFrame,
                               risks_df: pd.DataFrame,
                               dependencies: Optional[List[Dict]] = None) -> np.ndarray:
        """
        Build correlation matrix based on method and data attributes.
        
        Args:
            capex_items_df: DataFrame with CAPEX items
            risks_df: DataFrame with risks
            dependencies: Optional explicit dependencies (for future phases)
            
        Returns:
            Correlation matrix (identity matrix for Phase 1)
        """
        n_capex = len(capex_items_df)
        n_risks = len(risks_df)
        n_total = n_capex + n_risks
        
        if self.method == "none" or n_total == 0:
            # Phase 1: Independent sampling
            return np.eye(n_total)
        
        if self.method == "category":
            # Phase 2: Category-based correlation
            return self._build_category_correlation_matrix(capex_items_df, risks_df)
        
        # Default to identity matrix
        return np.eye(n_total)
    
    def _build_category_correlation_matrix(self,
                                         capex_items_df: pd.DataFrame,
                                         risks_df: pd.DataFrame) -> np.ndarray:
        """
        Build correlation matrix based on category rules.
        
        Args:
            capex_items_df: DataFrame with CAPEX items
            risks_df: DataFrame with risks
            
        Returns:
            Correlation matrix
        """
        n_capex = len(capex_items_df)
        n_risks = len(risks_df)
        n_total = n_capex + n_risks
        
        # Initialize with identity matrix
        corr_matrix = np.eye(n_total)
        
        # Apply CAPEX correlations
        for i in range(n_capex):
            for j in range(i + 1, n_capex):
                correlation = self._calculate_capex_correlation(
                    capex_items_df.iloc[i],
                    capex_items_df.iloc[j]
                )
                corr_matrix[i, j] = corr_matrix[j, i] = correlation
        
        # Apply risk correlations
        for i in range(n_risks):
            for j in range(i + 1, n_risks):
                correlation = self._calculate_risk_correlation(
                    risks_df.iloc[i],
                    risks_df.iloc[j]
                )
                idx_i = n_capex + i
                idx_j = n_capex + j
                corr_matrix[idx_i, idx_j] = corr_matrix[idx_j, idx_i] = correlation
        
        # Apply CAPEX-Risk correlations (if same owner)
        for i in range(n_capex):
            for j in range(n_risks):
                if (pd.notna(capex_items_df.iloc[i].get('item_owner')) and 
                    pd.notna(risks_df.iloc[j].get('risk_owner')) and
                    capex_items_df.iloc[i]['item_owner'] == risks_df.iloc[j]['risk_owner']):
                    idx_j = n_capex + j
                    corr_matrix[i, idx_j] = corr_matrix[idx_j, i] = 0.2
        
        # Ensure positive semi-definite
        return self._nearest_positive_semi_definite(corr_matrix)
    
    def _calculate_capex_correlation(self, item1: pd.Series, item2: pd.Series) -> float:
        """Calculate correlation between two CAPEX items based on attributes."""
        correlation = 0.0
        
        # Check each attribute
        if pd.notna(item1.get('item_owner')) and item1.get('item_owner') == item2.get('item_owner'):
            correlation = max(correlation, self.CORRELATION_RULES['same_owner'])
        
        if pd.notna(item1.get('discipline')) and item1.get('discipline') == item2.get('discipline'):
            correlation = max(correlation, self.CORRELATION_RULES['same_discipline'])
        
        if pd.notna(item1.get('phase')) and item1.get('phase') == item2.get('phase'):
            correlation = max(correlation, self.CORRELATION_RULES['same_phase'])
        
        if pd.notna(item1.get('location')) and item1.get('location') == item2.get('location'):
            correlation = max(correlation, self.CORRELATION_RULES['same_location'])
        
        # Cap maximum correlation
        return min(correlation, 0.8)
    
    def _calculate_risk_correlation(self, risk1: pd.Series, risk2: pd.Series) -> float:
        """Calculate correlation between two risks based on attributes."""
        correlation = 0.0
        
        # Check owner
        if pd.notna(risk1.get('risk_owner')) and risk1.get('risk_owner') == risk2.get('risk_owner'):
            correlation = max(correlation, self.CORRELATION_RULES['same_owner'])
        
        # Check category
        if pd.notna(risk1.get('risk_category')) and risk1.get('risk_category') == risk2.get('risk_category'):
            category = risk1['risk_category'].lower()
            if category in self.CORRELATION_RULES['same_risk_category']:
                correlation = max(correlation, self.CORRELATION_RULES['same_risk_category'][category])
        
        # Cap maximum correlation
        return min(correlation, 0.8)
    
    def _nearest_positive_semi_definite(self, matrix: np.ndarray) -> np.ndarray:
        """
        Find the nearest positive semi-definite matrix.
        
        Args:
            matrix: Input correlation matrix
            
        Returns:
            Nearest positive semi-definite matrix
        """
        try:
            # Try Cholesky decomposition to check if already PSD
            _ = cholesky(matrix, lower=True)
            return matrix
        except LinAlgError:
            # If not PSD, find nearest PSD matrix
            logger.warning("Correlation matrix not positive semi-definite, adjusting...")
            
            # Eigenvalue decomposition
            eigvals, eigvecs = np.linalg.eigh(matrix)
            
            # Set negative eigenvalues to small positive value
            eigvals[eigvals < 0] = 1e-8
            
            # Reconstruct matrix
            matrix_psd = eigvecs @ np.diag(eigvals) @ eigvecs.T
            
            # Ensure diagonal is 1
            d = np.sqrt(np.diag(matrix_psd))
            matrix_psd = matrix_psd / np.outer(d, d)
            
            return matrix_psd
    
    def generate_correlated_samples(self, 
                                  n_variables: int,
                                  n_samples: int,
                                  correlation_matrix: np.ndarray,
                                  random_state: Optional[np.random.RandomState] = None) -> np.ndarray:
        """
        Generate correlated uniform samples using the correlation matrix.
        
        Args:
            n_variables: Number of variables
            n_samples: Number of samples to generate
            correlation_matrix: Correlation matrix
            random_state: Random state for reproducibility
            
        Returns:
            Array of correlated uniform samples (n_samples x n_variables)
        """
        if random_state is None:
            random_state = np.random.RandomState()
        
        # Generate independent standard normal samples
        independent_samples = random_state.standard_normal((n_samples, n_variables))
        
        # Apply correlation using Cholesky decomposition
        try:
            L = cholesky(correlation_matrix, lower=True)
            correlated_normal = independent_samples @ L.T
        except LinAlgError:
            logger.warning("Failed to apply correlation, using independent samples")
            correlated_normal = independent_samples
        
        # Transform to uniform using normal CDF
        from scipy.stats import norm
        correlated_uniform = norm.cdf(correlated_normal)
        
        return correlated_uniform
    
    def get_correlation_summary(self, correlation_matrix: np.ndarray) -> Dict[str, Any]:
        """
        Generate summary statistics for the correlation matrix.
        
        Args:
            correlation_matrix: Correlation matrix
            
        Returns:
            Dictionary with correlation summary
        """
        # Extract off-diagonal elements
        n = correlation_matrix.shape[0]
        off_diagonal = correlation_matrix[np.triu_indices(n, k=1)]
        
        return {
            "method": self.method,
            "matrix_size": n,
            "max_correlation": float(np.max(off_diagonal)) if len(off_diagonal) > 0 else 0.0,
            "mean_correlation": float(np.mean(off_diagonal)) if len(off_diagonal) > 0 else 0.0,
            "correlation_pairs": int(np.sum(off_diagonal > 0.1)),  # Count significant correlations
            "is_positive_semi_definite": self._is_positive_semi_definite(correlation_matrix)
        }
    
    def _is_positive_semi_definite(self, matrix: np.ndarray) -> bool:
        """Check if matrix is positive semi-definite."""
        try:
            _ = cholesky(matrix, lower=True)
            return True
        except LinAlgError:
            return False
