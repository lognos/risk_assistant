"""
Database migration utilities for Monte Carlo correlation features.
Provides functions to populate and manage lookup tables for normalized correlation attributes.
"""

import logging
from typing import Dict, List, Optional, Union
from app.database import get_supabase_client

logger = logging.getLogger(__name__)


class DatabaseMigrationManager:
    """Manages database migrations and lookup table population."""
    
    def __init__(self):
        self.supabase = get_supabase_client()
    
    def populate_discipline_from_existing_data(self) -> Dict[str, int]:
        """
        Analyze existing owner data and suggest discipline mappings.
        Returns a mapping of unique disciplines to discipline_ids.
        """
        try:
            # Get unique owners from all tables to infer disciplines
            owners_data = []
            
            # Collect owners from capex_items
            capex_owners = self.supabase.table('capex_items').select('item_owner').execute()
            owners_data.extend([row['item_owner'] for row in capex_owners.data if row['item_owner']])
            
            # Collect owners from capex_actions  
            action_owners = self.supabase.table('capex_actions').select('cost_action_owner').execute()
            owners_data.extend([row['cost_action_owner'] for row in action_owners.data if row['cost_action_owner']])
            
            # Collect owners from risks
            risk_owners = self.supabase.table('risks').select('risk_owner').execute()
            owners_data.extend([row['risk_owner'] for row in risk_owners.data if row['risk_owner']])
            
            # Collect owners from risk_actions
            risk_action_owners = self.supabase.table('risk_actions').select('risk_action_owner').execute()
            owners_data.extend([row['risk_action_owner'] for row in risk_action_owners.data if row['risk_action_owner']])
            
            # Get unique owners
            unique_owners = list(set(owners_data))
            
            # Create discipline mapping based on owner names (heuristic approach)
            discipline_mapping = {}
            
            for owner in unique_owners:
                owner_lower = owner.lower()
                
                # Heuristic mapping based on common keywords in owner names
                if any(keyword in owner_lower for keyword in ['civil', 'structural', 'concrete']):
                    discipline_mapping[owner] = 'Civil Engineering'
                elif any(keyword in owner_lower for keyword in ['mechanical', 'equipment', 'rotating']):
                    discipline_mapping[owner] = 'Mechanical Engineering'
                elif any(keyword in owner_lower for keyword in ['electrical', 'power', 'lighting']):
                    discipline_mapping[owner] = 'Electrical Engineering'
                elif any(keyword in owner_lower for keyword in ['instrument', 'control', 'automation', 'i&c']):
                    discipline_mapping[owner] = 'Instrumentation & Control'
                elif any(keyword in owner_lower for keyword in ['process', 'chemical']):
                    discipline_mapping[owner] = 'Process Engineering'
                elif any(keyword in owner_lower for keyword in ['piping', 'pipe']):
                    discipline_mapping[owner] = 'Piping'
                elif any(keyword in owner_lower for keyword in ['hvac', 'ventilation', 'heating']):
                    discipline_mapping[owner] = 'HVAC'
                elif any(keyword in owner_lower for keyword in ['safety', 'hse', 'environmental']):
                    discipline_mapping[owner] = 'Safety & Environmental'
                else:
                    discipline_mapping[owner] = 'General'
            
            # Get discipline_ids
            disciplines = self.supabase.table('disciplines').select('discipline_id, discipline_name').execute()
            discipline_name_to_id = {d['discipline_name']: d['discipline_id'] for d in disciplines.data}
            
            # Create final mapping with discipline_ids
            owner_to_discipline_id = {
                owner: discipline_name_to_id[discipline_name] 
                for owner, discipline_name in discipline_mapping.items()
            }
            
            logger.info(f"Created discipline mapping for {len(owner_to_discipline_id)} unique owners")
            return owner_to_discipline_id
            
        except Exception as e:
            logger.error(f"Error in populate_discipline_from_existing_data: {e}")
            return {}
    
    def populate_phase_from_existing_data(self) -> Dict[str, int]:
        """
        Analyze existing data and suggest phase mappings.
        Returns a mapping of entities to phase_ids.
        """
        try:
            # For now, assign default phases based on entity type
            # This can be enhanced with more sophisticated logic
            
            phases = self.supabase.table('project_phases').select('phase_id, phase_name').execute()
            phase_name_to_id = {p['phase_name']: p['phase_id'] for p in phases.data}
            
            # Default phase assignments (can be customized)
            default_phases = {
                'capex_items': phase_name_to_id.get('Detailed Design', 1),
                'capex_actions': phase_name_to_id.get('Construction', 1), 
                'risks': phase_name_to_id.get('Front End Engineering Design', 1),
                'risk_actions': phase_name_to_id.get('Construction', 1)
            }
            
            logger.info(f"Created default phase mappings: {default_phases}")
            return default_phases
            
        except Exception as e:
            logger.error(f"Error in populate_phase_from_existing_data: {e}")
            return {}
    
    def populate_location_from_existing_data(self) -> Dict[str, int]:
        """
        Analyze existing data and suggest location mappings.
        Returns a mapping of entities to location_ids.
        """
        try:
            locations = self.supabase.table('locations').select('location_id, location_name').execute()
            location_name_to_id = {l['location_name']: l['location_id'] for l in locations.data}
            
            # Default location (can be enhanced with more sophisticated logic)
            default_location_id = location_name_to_id.get('Site General', 1)
            
            logger.info(f"Using default location: Site General (ID: {default_location_id})")
            return {'default': default_location_id}
            
        except Exception as e:
            logger.error(f"Error in populate_location_from_existing_data: {e}")
            return {}
    
    def update_capex_items_with_correlation_data(self, 
                                               discipline_mapping: Dict[str, int],
                                               phase_mapping: Dict[str, int],
                                               location_mapping: Dict[str, int]) -> bool:
        """Update capex_items table with correlation foreign keys."""
        try:
            # Get all capex items
            items = self.supabase.table('capex_items').select('item_id, item_owner').execute()
            
            default_phase_id = phase_mapping.get('capex_items', 1)
            default_location_id = location_mapping.get('default', 1)
            
            for item in items.data:
                discipline_id = discipline_mapping.get(item['item_owner'])
                
                if discipline_id:
                    update_data = {
                        'discipline_id': discipline_id,
                        'phase_id': default_phase_id,
                        'location_id': default_location_id
                    }
                    
                    self.supabase.table('capex_items').update(update_data).eq('item_id', item['item_id']).execute()
            
            logger.info(f"Updated {len(items.data)} capex items with correlation data")
            return True
            
        except Exception as e:
            logger.error(f"Error updating capex_items: {e}")
            return False
    
    def update_capex_actions_with_correlation_data(self,
                                                 discipline_mapping: Dict[str, int],
                                                 phase_mapping: Dict[str, int], 
                                                 location_mapping: Dict[str, int]) -> bool:
        """Update capex_actions table with correlation foreign keys."""
        try:
            # Get all capex actions
            actions = self.supabase.table('capex_actions').select('cost_action_id, cost_action_owner').execute()
            
            default_phase_id = phase_mapping.get('capex_actions', 1)
            default_location_id = location_mapping.get('default', 1)
            
            for action in actions.data:
                discipline_id = discipline_mapping.get(action['cost_action_owner'])
                
                if discipline_id:
                    update_data = {
                        'discipline_id': discipline_id,
                        'phase_id': default_phase_id,
                        'location_id': default_location_id
                    }
                    
                    self.supabase.table('capex_actions').update(update_data).eq('cost_action_id', action['cost_action_id']).execute()
            
            logger.info(f"Updated {len(actions.data)} capex actions with correlation data")
            return True
            
        except Exception as e:
            logger.error(f"Error updating capex_actions: {e}")
            return False
    
    def update_risks_with_correlation_data(self,
                                         discipline_mapping: Dict[str, int],
                                         phase_mapping: Dict[str, int],
                                         location_mapping: Dict[str, int]) -> bool:
        """Update risks table with correlation foreign keys."""
        try:
            # Get all risks
            risks = self.supabase.table('risks').select('risk_id, risk_owner').execute()
            
            # Get default IDs
            default_phase_id = phase_mapping.get('risks', 1)
            default_location_id = location_mapping.get('default', 1)
            
            # Get risk categories and logs for defaults
            risk_categories = self.supabase.table('risk_categories').select('risk_category_id, category_name').execute()
            risk_logs = self.supabase.table('risk_logs').select('risk_log_id, log_name').execute()
            
            default_category_id = next((rc['risk_category_id'] for rc in risk_categories.data if rc['category_name'] == 'Technical Risk'), 1)
            default_log_id = next((rl['risk_log_id'] for rl in risk_logs.data if rl['log_name'] == 'Project Risk Register'), 1)
            
            for risk in risks.data:
                discipline_id = discipline_mapping.get(risk['risk_owner'])
                
                if discipline_id:
                    update_data = {
                        'discipline_id': discipline_id,
                        'phase_id': default_phase_id,
                        'location_id': default_location_id,
                        'risk_category_id': default_category_id,
                        'risk_log_id': default_log_id
                    }
                    
                    self.supabase.table('risks').update(update_data).eq('risk_id', risk['risk_id']).execute()
            
            logger.info(f"Updated {len(risks.data)} risks with correlation data")
            return True
            
        except Exception as e:
            logger.error(f"Error updating risks: {e}")
            return False
    
    def update_risk_actions_with_correlation_data(self,
                                                discipline_mapping: Dict[str, int],
                                                phase_mapping: Dict[str, int],
                                                location_mapping: Dict[str, int]) -> bool:
        """Update risk_actions table with correlation foreign keys."""
        try:
            # Get all risk actions
            risk_actions = self.supabase.table('risk_actions').select('risk_action_id, risk_action_owner').execute()
            
            default_phase_id = phase_mapping.get('risk_actions', 1)
            default_location_id = location_mapping.get('default', 1)
            
            for action in risk_actions.data:
                discipline_id = discipline_mapping.get(action['risk_action_owner'])
                
                if discipline_id:
                    update_data = {
                        'discipline_id': discipline_id,
                        'phase_id': default_phase_id,
                        'location_id': default_location_id
                    }
                    
                    self.supabase.table('risk_actions').update(update_data).eq('risk_action_id', action['risk_action_id']).execute()
            
            logger.info(f"Updated {len(risk_actions.data)} risk actions with correlation data")
            return True
            
        except Exception as e:
            logger.error(f"Error updating risk_actions: {e}")
            return False
    
    def run_full_migration(self) -> bool:
        """Run the complete migration to populate all correlation data."""
        try:
            logger.info("Starting full correlation data migration...")
            
            # Step 1: Generate mappings from existing data
            logger.info("Step 1: Analyzing existing data for discipline mapping...")
            discipline_mapping = self.populate_discipline_from_existing_data()
            
            logger.info("Step 2: Creating phase mappings...")
            phase_mapping = self.populate_phase_from_existing_data()
            
            logger.info("Step 3: Creating location mappings...")
            location_mapping = self.populate_location_from_existing_data()
            
            # Step 2: Update all tables
            logger.info("Step 4: Updating capex_items...")
            success1 = self.update_capex_items_with_correlation_data(
                discipline_mapping, phase_mapping, location_mapping
            )
            
            logger.info("Step 5: Updating capex_actions...")
            success2 = self.update_capex_actions_with_correlation_data(
                discipline_mapping, phase_mapping, location_mapping
            )
            
            logger.info("Step 6: Updating risks...")
            success3 = self.update_risks_with_correlation_data(
                discipline_mapping, phase_mapping, location_mapping
            )
            
            logger.info("Step 7: Updating risk_actions...")
            success4 = self.update_risk_actions_with_correlation_data(
                discipline_mapping, phase_mapping, location_mapping
            )
            
            overall_success = all([success1, success2, success3, success4])
            
            if overall_success:
                logger.info("Full correlation data migration completed successfully!")
            else:
                logger.error("Migration completed with some errors. Check logs for details.")
            
            return overall_success
            
        except Exception as e:
            logger.error(f"Error in run_full_migration: {e}")
            return False


def main():
    """Main function to run the migration."""
    logging.basicConfig(level=logging.INFO)
    
    migration_manager = DatabaseMigrationManager()
    success = migration_manager.run_full_migration()
    
    if success:
        print("✅ Database migration completed successfully!")
        print("The Monte Carlo correlation features are now fully operational.")
    else:
        print("❌ Database migration failed. Check logs for details.")


if __name__ == "__main__":
    main()
