"""
Input validation utilities for Monte Carlo engine.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DataValidator:
    """Validates input data for Monte Carlo simulation."""
    
    @staticmethod
    def validate_capex_items(df: pd.DataFrame) -> List[str]:
        """
        Validate CAPEX items DataFrame.
        
        Args:
            df: CAPEX items DataFrame
            
        Returns:
            List of validation errors
        """
        errors = []
        required_columns = ['item_id', 'item_name', 'min_cost', 'ml_cost', 'max_cost']
        
        # Check required columns
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            errors.append(f"Missing required columns: {missing_cols}")
            return errors
        
        # Check for duplicates
        if df['item_id'].duplicated().any():
            duplicates = df[df['item_id'].duplicated()]['item_id'].tolist()
            errors.append(f"Duplicate item IDs found: {duplicates}")
        
        # Validate cost values
        for idx, row in df.iterrows():
            if pd.notna(row['min_cost']) and pd.notna(row['ml_cost']) and pd.notna(row['max_cost']):
                if not (row['min_cost'] <= row['ml_cost'] <= row['max_cost']):
                    errors.append(f"Item {row['item_id']}: Costs not ordered (min <= ml <= max)")
                if row['min_cost'] <= 0:
                    errors.append(f"Item {row['item_id']}: Costs must be positive")
        
        return errors
    
    @staticmethod
    def validate_capex_actions(df: pd.DataFrame, capex_items_df: pd.DataFrame) -> List[str]:
        """
        Validate CAPEX actions DataFrame.
        
        Args:
            df: CAPEX actions DataFrame
            capex_items_df: CAPEX items DataFrame for reference validation
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Allow empty DataFrame
        if df.empty:
            return errors
        
        required_columns = ['cost_action_id', 'item_id', 'cost_action_name', 
                          'cost_action_due', 'pm_min_cost', 'pm_ml_cost', 'pm_max_cost']
        
        # Check required columns
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            errors.append(f"Missing required columns: {missing_cols}")
            return errors
        
        # Check for duplicates
        if df['cost_action_id'].duplicated().any():
            duplicates = df[df['cost_action_id'].duplicated()]['cost_action_id'].tolist()
            errors.append(f"Duplicate action IDs found: {duplicates}")
        
        # Validate references
        invalid_refs = df[~df['item_id'].isin(capex_items_df['item_id'])]['item_id'].unique()
        if len(invalid_refs) > 0:
            errors.append(f"Actions reference non-existent items: {invalid_refs.tolist()}")
        
        # Validate post-mitigation values
        for idx, row in df.iterrows():
            if pd.notna(row['pm_min_cost']) and pd.notna(row['pm_ml_cost']) and pd.notna(row['pm_max_cost']):
                if not (row['pm_min_cost'] <= row['pm_ml_cost'] <= row['pm_max_cost']):
                    errors.append(f"Action {row['cost_action_id']}: PM costs not ordered")
                if row['pm_min_cost'] <= 0:
                    errors.append(f"Action {row['cost_action_id']}: PM costs must be positive")
        
        return errors
    
    @staticmethod
    def validate_risks(df: pd.DataFrame) -> List[str]:
        """
        Validate risks DataFrame.
        
        Args:
            df: Risks DataFrame
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Allow empty DataFrame
        if df.empty:
            return errors
        
        required_columns = ['risk_id', 'risk_name', 'min_impact', 'ml_impact', 
                          'max_impact', 'risk_probability']
        
        # Check required columns
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            errors.append(f"Missing required columns: {missing_cols}")
            return errors
        
        # Check for duplicates
        if df['risk_id'].duplicated().any():
            duplicates = df[df['risk_id'].duplicated()]['risk_id'].tolist()
            errors.append(f"Duplicate risk IDs found: {duplicates}")
        
        # Validate impact values and probabilities
        for idx, row in df.iterrows():
            # Check impacts
            if pd.notna(row['min_impact']) and pd.notna(row['ml_impact']) and pd.notna(row['max_impact']):
                if not (row['min_impact'] <= row['ml_impact'] <= row['max_impact']):
                    errors.append(f"Risk {row['risk_id']}: Impacts not ordered (min <= ml <= max)")
                if row['min_impact'] < 0:
                    errors.append(f"Risk {row['risk_id']}: Impacts must be non-negative")
            
            # Check probability
            if pd.notna(row['risk_probability']):
                if not (0 <= row['risk_probability'] <= 1):
                    errors.append(f"Risk {row['risk_id']}: Probability must be between 0 and 1")
        
        return errors
    
    @staticmethod
    def validate_risk_actions(df: pd.DataFrame, risks_df: pd.DataFrame) -> List[str]:
        """
        Validate risk actions DataFrame.
        
        Args:
            df: Risk actions DataFrame
            risks_df: Risks DataFrame for reference validation
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Allow empty DataFrame
        if df.empty:
            return errors
        
        # If risk actions exist but no risks, that's an error
        if not df.empty and risks_df.empty:
            errors.append("Risk actions provided but no risks exist to reference")
            return errors
        
        required_columns = ['risk_action_id', 'risk_id', 'risk_action_name', 
                          'risk_action_due', 'pm_min_impact', 'pm_ml_impact', 
                          'pm_max_impact', 'pm_risk_probability']
        
        # Check required columns
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            errors.append(f"Missing required columns: {missing_cols}")
            return errors
        
        # Check for duplicates
        if df['risk_action_id'].duplicated().any():
            duplicates = df[df['risk_action_id'].duplicated()]['risk_action_id'].tolist()
            errors.append(f"Duplicate action IDs found: {duplicates}")
        
        # Validate references
        invalid_refs = df[~df['risk_id'].isin(risks_df['risk_id'])]['risk_id'].unique()
        if len(invalid_refs) > 0:
            errors.append(f"Actions reference non-existent risks: {invalid_refs.tolist()}")
        
        # Validate post-mitigation values
        for idx, row in df.iterrows():
            # Check impacts
            if pd.notna(row['pm_min_impact']) and pd.notna(row['pm_ml_impact']) and pd.notna(row['pm_max_impact']):
                if not (row['pm_min_impact'] <= row['pm_ml_impact'] <= row['pm_max_impact']):
                    errors.append(f"Action {row['risk_action_id']}: PM impacts not ordered")
                if row['pm_min_impact'] < 0:
                    errors.append(f"Action {row['risk_action_id']}: PM impacts must be non-negative")
            
            # Check probability
            if pd.notna(row['pm_risk_probability']):
                if not (0 <= row['pm_risk_probability'] <= 1):
                    errors.append(f"Action {row['risk_action_id']}: PM probability must be between 0 and 1")
        
        return errors
    
    @staticmethod
    def validate_all_inputs(capex_items_df: pd.DataFrame,
                          capex_actions_df: pd.DataFrame,
                          risks_df: pd.DataFrame,
                          risk_actions_df: pd.DataFrame) -> Dict[str, List[str]]:
        """
        Validate all input DataFrames.
        Flexible validation: allows empty DataFrames for actions and risks.
        
        Args:
            capex_items_df: CAPEX items DataFrame
            capex_actions_df: CAPEX actions DataFrame (can be empty)
            risks_df: Risks DataFrame (can be empty)
            risk_actions_df: Risk actions DataFrame (can be empty)
            
        Returns:
            Dictionary with validation errors by category
        """
        validation_results = {
            'capex_items': [],
            'capex_actions': [],
            'risks': [],
            'risk_actions': []
        }
        
        # Always validate CAPEX items (required)
        validation_results['capex_items'] = DataValidator.validate_capex_items(capex_items_df)
        
        # Only validate CAPEX actions if data exists
        if not capex_actions_df.empty:
            validation_results['capex_actions'] = DataValidator.validate_capex_actions(capex_actions_df, capex_items_df)
        else:
            logger.info("No CAPEX actions provided - skipping validation")
        
        # Only validate risks if data exists
        if not risks_df.empty:
            validation_results['risks'] = DataValidator.validate_risks(risks_df)
        else:
            logger.info("No risks provided - skipping validation")
        
        # Only validate risk actions if data exists
        if not risk_actions_df.empty:
            validation_results['risk_actions'] = DataValidator.validate_risk_actions(risk_actions_df, risks_df)
        else:
            logger.info("No risk actions provided - skipping validation")
        
        # Log validation results
        total_errors = sum(len(errors) for errors in validation_results.values())
        if total_errors > 0:
            logger.warning(f"Found {total_errors} validation errors in input data")
            for category, errors in validation_results.items():
                if errors:
                    logger.warning(f"{category}: {len(errors)} errors")
                    for error in errors[:5]:  # Log first 5 errors
                        logger.warning(f"  - {error}")
        else:
            logger.info("All input data validation passed")
        
        return validation_results
    
    @staticmethod
    def has_errors(validation_results: Dict[str, List[str]]) -> bool:
        """Check if validation results contain any errors."""
        return any(len(errors) > 0 for errors in validation_results.values())
