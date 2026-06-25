#!/usr/bin/env python3
"""
Data migration script for importing existing system environment variables
into the database-managed environment variable system.

This script:
1. Creates a backup of existing environment configuration
2. Imports current system environment variables into the database
3. Detects and marks sensitive variables during import
4. Tests migration with current application environment variables
"""

import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple

from flask import Flask

# Import application components
from app import create_app
from database import db
from services.environment_service import EnvironmentService
from sqlalchemy_models import EnvironmentVariable


class EnvironmentMigrator:
    """Handles migration of system environment variables to database storage"""
    
    def __init__(self, app: Flask):
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.env_service = EnvironmentService()
        
        # Patterns for detecting sensitive variables
        self.sensitive_patterns = [
            r'.*password.*', r'.*secret.*', r'.*key.*', r'.*token.*',
            r'.*api.*key.*', r'.*auth.*', r'.*credential.*', r'.*private.*',
            r'.*jwt.*', r'.*oauth.*', r'.*session.*', r'.*hash.*',
            r'.*salt.*', r'.*cert.*', r'.*ssl.*', r'.*tls.*',
            r'.*database.*url.*', r'.*db.*url.*', r'.*connection.*string.*'
        ]
        
        # Variables that should be marked as required
        self.required_variables = {
            'FLASK_SECRET_KEY', 'SECRET_KEY', 'DATABASE_URL', 'FLASK_ENV',
            'SQLALCHEMY_DATABASE_URI', 'FLASK_APP'
        }
        
        # System variables to exclude from migration
        self.system_exclusions = {
            'PATH', 'HOME', 'USER', 'USERNAME', 'USERPROFILE', 'TEMP', 'TMP',
            'SYSTEMROOT', 'WINDIR', 'PROGRAMFILES', 'PROGRAMDATA', 'APPDATA',
            'LOCALAPPDATA', 'COMPUTERNAME', 'PROCESSOR_ARCHITECTURE',
            'PROCESSOR_IDENTIFIER', 'NUMBER_OF_PROCESSORS', 'OS', 'PATHEXT',
            'COMSPEC', 'SYSTEMDRIVE', 'HOMEDRIVE', 'HOMEPATH', 'LOGONSERVER',
            'USERDOMAIN', 'USERDNSDOMAIN', 'SESSIONNAME', 'CLIENTNAME',
            'TERM', 'SHELL', 'PWD', 'OLDPWD', 'SHLVL', 'LC_ALL', 'LANG',
            'DISPLAY', 'XDG_SESSION_TYPE', 'XDG_RUNTIME_DIR', 'SSH_CLIENT',
            'SSH_CONNECTION', 'SSH_TTY'
        }
        
        # Backup directory
        self.backup_dir = Path('environment_backups')
        self.backup_dir.mkdir(exist_ok=True)

    def create_backup(self) -> str:
        """Create backup of existing environment configuration"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = self.backup_dir / f'environment_backup_{timestamp}.json'
            
            # Create comprehensive backup
            backup_data = {
                'timestamp': timestamp,
                'system_environment': dict(os.environ),
                'existing_db_variables': [],
                'migration_metadata': {
                    'python_version': sys.version,
                    'platform': sys.platform,
                    'cwd': os.getcwd()
                }
            }
            
            # Include existing database variables if any
            with self.app.app_context():
                try:
                    existing_vars = EnvironmentVariable.query.all()
                    backup_data['existing_db_variables'] = [
                        {
                            'key': var.key,
                            'description': var.description,
                            'is_sensitive': var.is_sensitive,
                            'is_required': var.is_required,
                            'created_by': var.created_by,
                            'created_at': var.created_at.isoformat() if var.created_at else None
                        }
                        for var in existing_vars
                    ]
                except Exception as e:
                    self.logger.warning(f"Could not backup existing database variables: {e}")
            
            # Write backup file
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Created backup at: {backup_file}")
            return str(backup_file)
            
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            raise RuntimeError(f"Backup creation failed: {str(e)}")

    def detect_sensitive_variables(self, env_vars: Dict[str, str]) -> Set[str]:
        """Detect sensitive variables based on key patterns and values"""
        sensitive_vars = set()
        
        for key, value in env_vars.items():
            key_lower = key.lower()
            
            # Check key patterns
            if any(re.match(pattern, key_lower, re.IGNORECASE) for pattern in self.sensitive_patterns):
                sensitive_vars.add(key)
                continue
            
            # Check value patterns for potential sensitive data
            if value and len(value) > 8:  # Only check non-empty, reasonably long values
                value_lower = value.lower()
                
                # Look for patterns in values that suggest sensitive data
                sensitive_value_patterns = [
                    r'.*password.*', r'.*secret.*', r'.*token.*', r'.*key.*',
                    r'^[a-f0-9]{32,}$',  # Hex strings (likely hashes/keys)
                    r'^[A-Za-z0-9+/]{20,}={0,2}$',  # Base64-like strings
                    r'.*://.*:.*@.*',  # Connection strings with credentials
                ]
                
                if any(re.match(pattern, value_lower) for pattern in sensitive_value_patterns):
                    sensitive_vars.add(key)
        
        return sensitive_vars

    def filter_migration_candidates(self, env_vars: Dict[str, str]) -> Dict[str, str]:
        """Filter environment variables to include only migration candidates"""
        candidates = {}
        
        for key, value in env_vars.items():
            # Skip system variables
            if key in self.system_exclusions:
                continue
            
            # Skip variables with system-like prefixes (but allow some important ones)
            if key.startswith(('PROCESSOR_', 'PROGRAM', 'SYSTEM', 'WINDOWS')):
                continue
            
            # Skip empty values
            if not value or value.strip() == '':
                continue
            
            # Skip very long values that are likely system paths or data
            if len(value) > 1000:
                continue
            
            # Include the variable
            candidates[key] = value
        
        return candidates

    def get_variable_description(self, key: str, value: str) -> str:
        """Generate description for environment variable based on key and value"""
        key_lower = key.lower()
        
        # Common variable descriptions
        descriptions = {
            'flask_secret_key': 'Flask application secret key for session security',
            'secret_key': 'Application secret key',
            'database_url': 'Database connection URL',
            'sqlalchemy_database_uri': 'SQLAlchemy database connection URI',
            'flask_env': 'Flask environment mode (development/production)',
            'flask_app': 'Flask application entry point',
            'debug': 'Debug mode flag',
            'port': 'Application port number',
            'host': 'Application host address',
        }
        
        # Check for exact matches
        if key_lower in descriptions:
            return descriptions[key_lower]
        
        # Pattern-based descriptions
        if 'api' in key_lower and 'key' in key_lower:
            return f'API key for {key.replace("_", " ").title()}'
        elif 'token' in key_lower:
            return f'Authentication token for {key.replace("_", " ").title()}'
        elif 'password' in key_lower:
            return f'Password for {key.replace("_", " ").title()}'
        elif 'url' in key_lower:
            return f'URL configuration for {key.replace("_", " ").title()}'
        elif 'email' in key_lower:
            return f'Email configuration for {key.replace("_", " ").title()}'
        elif key_lower.endswith('_port'):
            return f'Port number for {key[:-5].replace("_", " ").title()}'
        elif key_lower.endswith('_host'):
            return f'Host address for {key[:-5].replace("_", " ").title()}'
        
        # Default description
        return f'Environment variable: {key.replace("_", " ").title()}'

    def migrate_variables(self, dry_run: bool = False) -> Dict[str, any]:
        """Migrate environment variables to database"""
        migration_result = {
            'success': False,
            'backup_file': None,
            'migrated_count': 0,
            'skipped_count': 0,
            'error_count': 0,
            'sensitive_count': 0,
            'required_count': 0,
            'migrated_variables': [],
            'skipped_variables': [],
            'errors': [],
            'warnings': []
        }
        
        try:
            # Create backup first
            migration_result['backup_file'] = self.create_backup()
            
            # Get migration candidates
            all_env_vars = dict(os.environ)
            candidates = self.filter_migration_candidates(all_env_vars)
            
            self.logger.info(f"Found {len(candidates)} migration candidates out of {len(all_env_vars)} total environment variables")
            
            # Detect sensitive variables
            sensitive_vars = self.detect_sensitive_variables(candidates)
            migration_result['sensitive_count'] = len(sensitive_vars)
            
            if dry_run:
                self.logger.info("DRY RUN MODE - No changes will be made")
                migration_result['success'] = True
                migration_result['migrated_count'] = len(candidates)
                
                # Prepare dry run results
                for key, value in candidates.items():
                    is_sensitive = key in sensitive_vars
                    is_required = key in self.required_variables
                    description = self.get_variable_description(key, value)
                    
                    migration_result['migrated_variables'].append({
                        'key': key,
                        'is_sensitive': is_sensitive,
                        'is_required': is_required,
                        'description': description
                    })
                    
                    if is_required:
                        migration_result['required_count'] += 1
                
                return migration_result
            
            # Perform migration within app context
            with self.app.app_context():
                for key, value in candidates.items():
                    try:
                        # Check if variable already exists
                        existing = EnvironmentVariable.query.filter_by(key=key).first()
                        if existing:
                            migration_result['skipped_count'] += 1
                            migration_result['skipped_variables'].append({
                                'key': key,
                                'reason': 'Already exists in database'
                            })
                            continue
                        
                        # Determine variable properties
                        is_sensitive = key in sensitive_vars
                        is_required = key in self.required_variables
                        description = self.get_variable_description(key, value)
                        
                        # Create variable using environment service
                        try:
                            created_var = self.env_service.create_variable(
                                key=key,
                                value=value,
                                description=description,
                                is_required=is_required,
                                created_by='migration_script'
                            )
                            
                            migration_result['migrated_count'] += 1
                            if is_required:
                                migration_result['required_count'] += 1
                            
                            migration_result['migrated_variables'].append({
                                'key': key,
                                'is_sensitive': is_sensitive,
                                'is_required': is_required,
                                'description': description
                            })
                            
                            self.logger.info(f"Migrated: {key} (sensitive: {is_sensitive}, required: {is_required})")
                            
                        except Exception as create_error:
                            migration_result['error_count'] += 1
                            error_msg = f"Failed to create variable {key}: {str(create_error)}"
                            migration_result['errors'].append(error_msg)
                            self.logger.error(error_msg)
                    
                    except Exception as var_error:
                        migration_result['error_count'] += 1
                        error_msg = f"Error processing variable {key}: {str(var_error)}"
                        migration_result['errors'].append(error_msg)
                        self.logger.error(error_msg)
            
            # Migration completed
            migration_result['success'] = True
            self.logger.info(f"Migration completed: {migration_result['migrated_count']} migrated, {migration_result['skipped_count']} skipped, {migration_result['error_count']} errors")
            
        except Exception as e:
            migration_result['errors'].append(f"Migration failed: {str(e)}")
            self.logger.error(f"Migration failed: {e}")
            raise
        
        return migration_result

    def test_migration(self) -> Dict[str, any]:
        """Test migration with current application environment variables"""
        test_result = {
            'success': False,
            'total_variables': 0,
            'migration_candidates': 0,
            'sensitive_detected': 0,
            'required_detected': 0,
            'system_excluded': 0,
            'candidate_variables': [],
            'sensitive_variables': [],
            'required_variables': [],
            'warnings': []
        }
        
        try:
            all_env_vars = dict(os.environ)
            test_result['total_variables'] = len(all_env_vars)
            
            # Filter candidates
            candidates = self.filter_migration_candidates(all_env_vars)
            test_result['migration_candidates'] = len(candidates)
            test_result['system_excluded'] = len(all_env_vars) - len(candidates)
            
            # Detect sensitive and required variables
            sensitive_vars = self.detect_sensitive_variables(candidates)
            required_vars = {key for key in candidates.keys() if key in self.required_variables}
            
            test_result['sensitive_detected'] = len(sensitive_vars)
            test_result['required_detected'] = len(required_vars)
            
            # Prepare detailed results
            for key in candidates.keys():
                var_info = {
                    'key': key,
                    'is_sensitive': key in sensitive_vars,
                    'is_required': key in required_vars,
                    'description': self.get_variable_description(key, candidates[key])
                }
                test_result['candidate_variables'].append(var_info)
            
            test_result['sensitive_variables'] = list(sensitive_vars)
            test_result['required_variables'] = list(required_vars)
            
            # Check for potential issues
            if not any(key in self.required_variables for key in candidates.keys()):
                test_result['warnings'].append("No critical application variables found (FLASK_SECRET_KEY, DATABASE_URL, etc.)")
            
            if len(sensitive_vars) == 0:
                test_result['warnings'].append("No sensitive variables detected - this may indicate detection patterns need adjustment")
            
            test_result['success'] = True
            
        except Exception as e:
            self.logger.error(f"Migration test failed: {e}")
            raise
        
        return test_result

    def print_migration_report(self, result: Dict[str, any], test_mode: bool = False):
        """Print detailed migration report"""
        print("\n" + "="*60)
        if test_mode:
            print("ENVIRONMENT VARIABLE MIGRATION TEST REPORT")
        else:
            print("ENVIRONMENT VARIABLE MIGRATION REPORT")
        print("="*60)
        
        if test_mode:
            print(f"Total environment variables: {result['total_variables']}")
            print(f"Migration candidates: {result['migration_candidates']}")
            print(f"System variables excluded: {result['system_excluded']}")
            print(f"Sensitive variables detected: {result['sensitive_detected']}")
            print(f"Required variables detected: {result['required_detected']}")
            
            if result['warnings']:
                print("\nWarnings:")
                for warning in result['warnings']:
                    print(f"  - {warning}")
            
            if result['candidate_variables']:
                print(f"\nMigration candidates ({len(result['candidate_variables'])}):")
                for var in result['candidate_variables']:
                    flags = []
                    if var['is_sensitive']:
                        flags.append('SENSITIVE')
                    if var['is_required']:
                        flags.append('REQUIRED')
                    flag_str = f" [{', '.join(flags)}]" if flags else ""
                    print(f"  - {var['key']}{flag_str}")
                    print(f"    Description: {var['description']}")
        else:
            print(f"Migration status: {'SUCCESS' if result['success'] else 'FAILED'}")
            print(f"Backup file: {result['backup_file']}")
            print(f"Variables migrated: {result['migrated_count']}")
            print(f"Variables skipped: {result['skipped_count']}")
            print(f"Errors encountered: {result['error_count']}")
            print(f"Sensitive variables: {result['sensitive_count']}")
            print(f"Required variables: {result['required_count']}")
            
            if result['errors']:
                print("\nErrors:")
                for error in result['errors']:
                    print(f"  - {error}")
            
            if result['warnings']:
                print("\nWarnings:")
                for warning in result['warnings']:
                    print(f"  - {warning}")
            
            if result['migrated_variables']:
                print(f"\nMigrated variables ({len(result['migrated_variables'])}):")
                for var in result['migrated_variables']:
                    flags = []
                    if var['is_sensitive']:
                        flags.append('SENSITIVE')
                    if var['is_required']:
                        flags.append('REQUIRED')
                    flag_str = f" [{', '.join(flags)}]" if flags else ""
                    print(f"  - {var['key']}{flag_str}")
        
        print("="*60)



def validate_migration_script():
    """Validate that the migration script components work correctly"""
    print("Validating migration script components...")
    
    try:
        # Test Flask app creation
        app = create_app()
        print("✓ Flask app creation successful")
        
        # Test migrator initialization
        migrator = EnvironmentMigrator(app)
        print("✓ EnvironmentMigrator initialization successful")
        
        # Test sensitive variable detection
        test_vars = {
            'FLASK_SECRET_KEY': 'test-secret-123',
            'API_KEY': 'sk-test123',
            'DEBUG_MODE': 'true',
            'DATABASE_PASSWORD': 'mypassword',
            'NORMAL_VAR': 'normal_value'
        }
        
        sensitive = migrator.detect_sensitive_variables(test_vars)
        expected_sensitive = {'FLASK_SECRET_KEY', 'API_KEY', 'DATABASE_PASSWORD'}
        
        if sensitive == expected_sensitive:
            print("✓ Sensitive variable detection working correctly")
        else:
            print(f"✗ Sensitive detection issue: expected {expected_sensitive}, got {sensitive}")
            return False
        
        # Test variable filtering
        system_vars = {
            'PATH': '/usr/bin:/bin',
            'HOME': '/home/user',
            'FLASK_SECRET_KEY': 'secret',
            'MY_APP_CONFIG': 'config_value',
            'EMPTY_KEY': '',  # This should be filtered out
            'LONG_VAR': 'x' * 2000  # This should be filtered out
        }
        
        filtered = migrator.filter_migration_candidates(system_vars)
        expected_keys = {'FLASK_SECRET_KEY', 'MY_APP_CONFIG'}
        
        if set(filtered.keys()) == expected_keys:
            print("✓ Variable filtering working correctly")
        else:
            print(f"✗ Filtering issue: expected {expected_keys}, got {set(filtered.keys())}")
            return False
        
        # Test description generation
        desc = migrator.get_variable_description('API_KEY', 'test-key')
        if 'API key' in desc:
            print("✓ Description generation working correctly")
        else:
            print(f"✗ Description generation issue: {desc}")
            return False
        
        print("✓ All validation tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Validation failed: {e}")
        return False


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate system environment variables to database')
    parser.add_argument('--test', action='store_true', help='Test migration without making changes')
    parser.add_argument('--dry-run', action='store_true', help='Perform dry run migration')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    parser.add_argument('--validate', action='store_true', help='Validate migration script components')
    
    args = parser.parse_args()
    
    if args.validate:
        success = validate_migration_script()
        sys.exit(0 if success else 1)
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    try:
        # Create Flask app
        app = create_app()
        migrator = EnvironmentMigrator(app)
        
        if args.test:
            # Test mode - analyze current environment
            logger.info("Running migration test...")
            result = migrator.test_migration()
            migrator.print_migration_report(result, test_mode=True)
        else:
            # Migration mode
            logger.info("Starting environment variable migration...")
            result = migrator.migrate_variables(dry_run=args.dry_run)
            migrator.print_migration_report(result, test_mode=False)
            
            if result['success']:
                logger.info("Migration completed successfully!")
                if args.dry_run:
                    logger.info("This was a dry run - no changes were made")
            else:
                logger.error("Migration failed!")
                sys.exit(1)
    
    except Exception as e:
        logger.error(f"Migration script failed: {e}")
        sys.exit(1)