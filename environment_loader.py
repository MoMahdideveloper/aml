"""
Environment Loader for loading stored environment variables at application startup.
Provides fallback to system environment variables if database is unavailable.
"""

import logging
import os
from typing import Dict, List, Tuple

from flask import Flask


class EnvironmentLoader:
    """Loads environment variables from database at application startup"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._loaded_variables = {}
        self._fallback_used = False
    
    def load_environment_variables(self, app: Flask) -> Tuple[int, List[str], bool]:
        """
        Load environment variables from database with fallback to system environment.
        
        Args:
            app: Flask application instance
            
        Returns:
            Tuple of (loaded_count, errors, fallback_used)
        """
        loaded_count = 0
        errors = []
        
        try:
            # Try to load from database
            with app.app_context():
                loaded_count, errors = self._load_from_database()
                
            if loaded_count > 0:
                self.logger.info(f"Successfully loaded {loaded_count} environment variables from database")
                return loaded_count, errors, False
            else:
                self.logger.warning("No environment variables found in database, using system environment")
                return 0, errors, True
                
        except Exception as e:
            # Database unavailable - use system environment variables
            self.logger.warning(f"Database unavailable for environment loading: {e}")
            self.logger.info("Falling back to system environment variables")
            self._fallback_used = True
            return 0, [f"Database unavailable: {str(e)}"], True
    
    def _load_from_database(self) -> Tuple[int, List[str]]:
        """Load environment variables from database"""
        try:
            # Import here to avoid circular imports
            from services.environment_service import environment_service
            from sqlalchemy import inspect
            from database import db
            
            # Check if table exists to avoid OperationalError on fresh DB
            inspector = inspect(db.engine)
            if "environment_variables" not in inspector.get_table_names():
                raise Exception("Table 'environment_variables' does not exist")
            
            # Get all variables and apply to runtime
            loaded_count, errors = environment_service.apply_all_to_runtime()
            
            # Store loaded variables for reference
            variables = environment_service.get_all_variables(mask_sensitive=False)
            self._loaded_variables = {
                var["key"]: var["value"]
                for var in variables
                if environment_service.is_db_managed_key_allowed(var["key"])
            }

            return loaded_count, errors
            
        except ImportError as e:
            self.logger.error(f"Failed to import environment service: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to load environment variables from database: {e}")
            raise
    
    def validate_critical_variables(self) -> Dict[str, List[str]]:
        """
        Validate that critical environment variables are present.
        
        Returns:
            Dictionary with missing variables and warnings
        """
        # SESSION_SECRET is canonical; FLASK_SECRET_KEY remains backward-compatible.
        critical_variables = [
            "SESSION_SECRET",
            "DATABASE_URL",
            "FLASK_ENV",
        ]
        
        missing_variables = []
        warnings = []
        
        for var in critical_variables:
            if var not in os.environ:
                missing_variables.append(var)
                warnings.append(f"Critical variable '{var}' is missing from environment")
        
        # Backward-compat: accept FLASK_SECRET_KEY when SESSION_SECRET is absent.
        if "SESSION_SECRET" not in os.environ and "FLASK_SECRET_KEY" in os.environ:
            warnings.append("Using deprecated FLASK_SECRET_KEY; migrate to SESSION_SECRET")

        secret_value = os.environ.get("SESSION_SECRET") or os.environ.get("FLASK_SECRET_KEY")
        if secret_value == "dev-secret-key-change-in-production":
            warnings.append("Secret key is using default development value")
        
        return {
            'missing_variables': missing_variables,
            'warnings': warnings
        }
    
    def get_loaded_variables(self) -> Dict[str, str]:
        """Get dictionary of variables loaded from database"""
        return self._loaded_variables.copy()
    
    def was_fallback_used(self) -> bool:
        """Check if fallback to system environment was used"""
        return self._fallback_used
    
    def get_environment_summary(self) -> Dict:
        """Get summary of environment loading status"""
        validation_result = self.validate_critical_variables()
        
        return {
            'loaded_from_database': len(self._loaded_variables),
            'fallback_used': self._fallback_used,
            'total_environment_variables': len(os.environ),
            'missing_critical_variables': validation_result['missing_variables'],
            'warnings': validation_result['warnings']
        }


# Global loader instance
environment_loader = EnvironmentLoader()


def load_environment_at_startup(app: Flask) -> None:
    """
    Convenience function to load environment variables at application startup.
    
    Args:
        app: Flask application instance
    """
    logger = logging.getLogger(__name__)
    
    try:
        loaded_count, errors, fallback_used = environment_loader.load_environment_variables(app)
        
        if errors:
            for error in errors:
                logger.warning(f"Environment loading error: {error}")
        
        if fallback_used:
            logger.info("Using system environment variables as fallback")
        
        # Validate critical variables
        validation_result = environment_loader.validate_critical_variables()
        if validation_result['missing_variables']:
            logger.error(f"Missing critical environment variables: {validation_result['missing_variables']}")
        
        if validation_result['warnings']:
            for warning in validation_result['warnings']:
                logger.warning(f"Environment warning: {warning}")
        
        # Log summary
        summary = environment_loader.get_environment_summary()
        logger.info(f"Environment loading complete - Database: {summary['loaded_from_database']}, "
                   f"Total: {summary['total_environment_variables']}, "
                   f"Fallback: {summary['fallback_used']}")
        
    except Exception as e:
        logger.error(f"Failed to load environment variables at startup: {e}")
        logger.info("Application will continue with system environment variables")
