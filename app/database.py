import os
import logging
from typing import Optional, Dict, Any, List
from supabase import create_client, Client
from .models import User

# Import config to ensure environment variables are loaded
from . import config

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for user database operations using Supabase"""
    
    def __init__(self):
        self.client: Optional[Client] = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Supabase client"""
        try:
            # Get credentials from environment or secrets
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_ANON_KEY')
            
            if not supabase_url or not supabase_key:
                logger.warning("Supabase credentials not found. Database operations will be disabled.")
                return
            
            self.client = create_client(supabase_url, supabase_key)
            logger.info("Supabase client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            self.client = None