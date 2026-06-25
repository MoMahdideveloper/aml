"""
Database Transaction Manager
Provides transaction management with rollback capabilities for database operations
"""

import logging
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Optional

from database import db


class DatabaseTransactionManager:
    """Manages database transactions with automatic rollback on errors"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    @contextmanager
    def transaction(self, rollback_on_error=True):
        """
        Context manager for database transactions
        
        Args:
            rollback_on_error: Whether to rollback on exceptions
        """
        try:
            yield db.session
            db.session.commit()
            self.logger.debug("Transaction committed successfully")
            
        except Exception as e:
            if rollback_on_error:
                db.session.rollback()
                self.logger.error(f"Transaction rolled back due to error: {str(e)}")
            else:
                self.logger.error(f"Transaction error (no rollback): {str(e)}")
            raise
    
    def with_transaction(self, rollback_on_error=True):
        """
        Decorator for methods that need transaction management
        
        Args:
            rollback_on_error: Whether to rollback on exceptions
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    result = func(*args, **kwargs)
                    db.session.commit()
                    self.logger.debug(f"Transaction committed for {func.__name__}")
                    return result
                    
                except Exception as e:
                    if rollback_on_error:
                        db.session.rollback()
                        self.logger.error(f"Transaction rolled back in {func.__name__}: {str(e)}")
                    else:
                        self.logger.error(f"Transaction error in {func.__name__} (no rollback): {str(e)}")
                    raise
            
            return wrapper
        return decorator
    
    def safe_execute(self, operation: Callable, *args, **kwargs) -> Any:
        """
        Safely execute a database operation with automatic rollback
        
        Args:
            operation: Function to execute
            *args: Arguments for the operation
            **kwargs: Keyword arguments for the operation
            
        Returns:
            Result of the operation
            
        Raises:
            Exception: If the operation fails
        """
        try:
            result = operation(*args, **kwargs)
            db.session.commit()
            self.logger.debug(f"Safe execution of {operation.__name__} completed")
            return result
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Safe execution of {operation.__name__} failed: {str(e)}")
            raise
    
    def create_savepoint(self, name: Optional[str] = None) -> str:
        """
        Create a database savepoint
        
        Args:
            name: Optional name for the savepoint
            
        Returns:
            Savepoint name
        """
        if not name:
            import time
            name = f"savepoint_{int(time.time() * 1000)}"
        
        try:
            db.session.execute(f"SAVEPOINT {name}")
            self.logger.debug(f"Created savepoint: {name}")
            return name
            
        except Exception as e:
            self.logger.error(f"Failed to create savepoint {name}: {str(e)}")
            raise
    
    def rollback_to_savepoint(self, name: str):
        """
        Rollback to a specific savepoint
        
        Args:
            name: Savepoint name
        """
        try:
            db.session.execute(f"ROLLBACK TO SAVEPOINT {name}")
            self.logger.debug(f"Rolled back to savepoint: {name}")
            
        except Exception as e:
            self.logger.error(f"Failed to rollback to savepoint {name}: {str(e)}")
            raise
    
    def release_savepoint(self, name: str):
        """
        Release a savepoint
        
        Args:
            name: Savepoint name
        """
        try:
            db.session.execute(f"RELEASE SAVEPOINT {name}")
            self.logger.debug(f"Released savepoint: {name}")
            
        except Exception as e:
            self.logger.error(f"Failed to release savepoint {name}: {str(e)}")
            raise
    
    @contextmanager
    def savepoint_context(self, name: Optional[str] = None):
        """
        Context manager for savepoint operations
        
        Args:
            name: Optional savepoint name
        """
        savepoint_name = self.create_savepoint(name)
        
        try:
            yield savepoint_name
            self.release_savepoint(savepoint_name)
            
        except Exception as e:
            self.rollback_to_savepoint(savepoint_name)
            self.logger.error(f"Rolled back to savepoint {savepoint_name}: {str(e)}")
            raise
    
    def batch_operation(self, operations: list, rollback_all_on_error=True):
        """
        Execute multiple operations in a single transaction
        
        Args:
            operations: List of (function, args, kwargs) tuples
            rollback_all_on_error: Whether to rollback all operations on any error
            
        Returns:
            List of results from each operation
        """
        results = []
        
        with self.transaction(rollback_on_error=rollback_all_on_error):
            for operation, args, kwargs in operations:
                try:
                    result = operation(*args, **kwargs)
                    results.append(result)
                    
                except Exception as e:
                    self.logger.error(f"Batch operation failed at {operation.__name__}: {str(e)}")
                    raise
        
        return results
    
    def get_session_info(self) -> dict:
        """
        Get information about the current database session
        
        Returns:
            Dictionary with session information
        """
        try:
            return {
                'is_active': db.session.is_active,
                'dirty': len(db.session.dirty),
                'new': len(db.session.new),
                'deleted': len(db.session.deleted),
                'identity_map_size': len(db.session.identity_map),
                'autocommit': db.session.autocommit,
                'autoflush': db.session.autoflush
            }
        except Exception as e:
            self.logger.error(f"Failed to get session info: {str(e)}")
            return {}
    
    def flush_session(self):
        """
        Flush the current session without committing
        """
        try:
            db.session.flush()
            self.logger.debug("Session flushed successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to flush session: {str(e)}")
            raise
    
    def refresh_object(self, obj):
        """
        Refresh an object from the database
        
        Args:
            obj: SQLAlchemy model instance
        """
        try:
            db.session.refresh(obj)
            self.logger.debug(f"Refreshed object: {obj}")
            
        except Exception as e:
            self.logger.error(f"Failed to refresh object {obj}: {str(e)}")
            raise
    
    def expunge_object(self, obj):
        """
        Remove an object from the session
        
        Args:
            obj: SQLAlchemy model instance
        """
        try:
            db.session.expunge(obj)
            self.logger.debug(f"Expunged object: {obj}")
            
        except Exception as e:
            self.logger.error(f"Failed to expunge object {obj}: {str(e)}")
            raise


# Global transaction manager instance
transaction_manager = DatabaseTransactionManager()


# Convenience decorators
def with_transaction(rollback_on_error=True):
    """Decorator for transaction management"""
    return transaction_manager.with_transaction(rollback_on_error)


def safe_database_operation(func):
    """Decorator for safe database operations with automatic rollback"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        return transaction_manager.safe_execute(func, *args, **kwargs)
    return wrapper


# Context managers
def database_transaction(rollback_on_error=True):
    """Context manager for database transactions"""
    return transaction_manager.transaction(rollback_on_error)


def database_savepoint(name=None):
    """Context manager for database savepoints"""
    return transaction_manager.savepoint_context(name)