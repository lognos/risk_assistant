import os
import logging
from typing import Optional, Dict, Any, List
from supabase import create_client, Client
from dotenv import load_dotenv

# Ensure environment variables from .env are loaded if present
load_dotenv()

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for project database operations using Supabase"""

    def __init__(self):
        self.client: Optional[Client] = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Supabase client"""
        try:
            # Get credentials from environment or secrets
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")

            if not supabase_url or not supabase_key:
                logger.warning("Supabase credentials not found. Database operations will be disabled.")
                return

            self.client = create_client(supabase_url, supabase_key)
            logger.info("Supabase client initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            self.client = None

    # --- Phase 2: Project data loaders ---
    def _fetch_table_flexible(self, table: str, project_id: int) -> List[Dict[str, Any]]:
        """
        Fetch rows for a project. If the table is missing a project_id column,
        fall back to fetching all rows. Use this only for legacy CAPEX tables.
        """
        if not self.client:
            raise RuntimeError("Supabase client not initialized")
        try:
            try:
                resp = self.client.table(table).select("*").eq("project_id", str(project_id)).execute()
                return resp.data or []
            except Exception as e:
                msg = str(e)
                if "column" in msg and "does not exist" in msg:
                    logger.warning(
                        "Table '%s' missing project_id column; falling back to unfiltered fetch (legacy mode)",
                        table,
                    )
                    resp = self.client.table(table).select("*").execute()
                    return resp.data or []
                raise
        except Exception as e:
            logger.error(f"Error fetching from {table}: {e}")
            raise

    def _fetch_table_strict(self, table: str, project_id: int) -> List[Dict[str, Any]]:
        """
        Strictly fetch rows filtered by project_id. If the project_id column is
        missing or the query fails, raise an error. Use for risk-related tables.
        """
        if not self.client:
            raise RuntimeError("Supabase client not initialized")
        try:
            # Project IDs may be stored as varchar; compare using string value
            resp = self.client.table(table).select("*").eq("project_id", str(project_id)).execute()
            return resp.data or []
        except Exception as e:
            logger.error(
                "Strict fetch failed for table '%s' with project_id=%s. Ensure a project_id column exists. Error: %s",
                table,
                project_id,
                e,
            )
            raise

    def get_capex_items(self, project_id: int) -> List[Dict[str, Any]]:
        # CAPEX tables now include a project_id column; enforce strict filtering
        return self._fetch_table_strict("capex_items", project_id)

    def get_capex_actions(self, project_id: int) -> List[Dict[str, Any]]:
        # CAPEX tables now include a project_id column; enforce strict filtering
        return self._fetch_table_strict("capex_actions", project_id)

    def get_risks(self, project_id: int) -> List[Dict[str, Any]]:
        # Risk tables must include a project_id column; do not fallback
        return self._fetch_table_strict("risks", project_id)

    def get_risk_actions(self, project_id: int) -> List[Dict[str, Any]]:
        # Risk tables must include a project_id column; do not fallback
        return self._fetch_table_strict("risk_actions", project_id)