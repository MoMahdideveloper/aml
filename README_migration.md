# Environment Variable Migration Script

This script migrates existing system environment variables into the database-managed environment variable system.

## Features

- **Backup Creation**: Creates comprehensive backups before migration
- **Sensitive Detection**: Automatically detects and marks sensitive variables (API keys, passwords, tokens)
- **Smart Filtering**: Excludes system variables and includes only application-relevant variables
- **Validation**: Validates variable names and values according to application standards
- **Dry Run Mode**: Test migration without making changes
- **Detailed Reporting**: Provides comprehensive reports of migration results

## Usage

### Test Migration (Recommended First Step)
```bash
python migrate_environment_vars.py --test
```
This analyzes your current environment and shows what would be migrated without making any changes.

### Dry Run Migration
```bash
python migrate_environment_vars.py --dry-run
```
This performs the full migration process but doesn't actually save anything to the database.

### Actual Migration
```bash
python migrate_environment_vars.py
```
This performs the actual migration, saving variables to the database.

### Verbose Output
Add `--verbose` or `-v` to any command for detailed logging:
```bash
python migrate_environment_vars.py --test --verbose
```

## What Gets Migrated

### Included Variables
- Application-specific environment variables
- Configuration variables (URLs, ports, emails)
- API keys and authentication tokens
- Custom application settings

### Excluded Variables
- System variables (PATH, HOME, USER, etc.)
- Windows system variables (SYSTEMROOT, WINDIR, etc.)
- Process-specific variables
- Empty or very long values (>1000 characters)

### Sensitive Variable Detection
Variables are automatically marked as sensitive if their key contains:
- `password`, `secret`, `key`, `token`
- `api`, `auth`, `credential`, `private`
- `jwt`, `oauth`, `session`, `hash`
- `salt`, `cert`, `ssl`, `tls`

### Required Variable Detection
Variables are automatically marked as required if they are:
- `FLASK_SECRET_KEY`, `SECRET_KEY`
- `DATABASE_URL`, `SQLALCHEMY_DATABASE_URI`
- `FLASK_ENV`, `FLASK_APP`

## Backup System

The script automatically creates backups in the `environment_backups/` directory with:
- Timestamp-based filenames
- Complete system environment snapshot
- Existing database variables (if any)
- Migration metadata

Backup files are in JSON format and can be used for recovery if needed.

## Migration Process

1. **Backup Creation**: Creates backup of current environment
2. **Variable Analysis**: Analyzes all environment variables
3. **Filtering**: Excludes system variables, includes application variables
4. **Sensitive Detection**: Identifies sensitive variables for encryption
5. **Database Storage**: Saves variables to database with proper encryption
6. **Runtime Application**: Applies variables to current runtime environment
7. **Audit Logging**: Logs all changes for audit trail

## Safety Features

- **Backup Before Changes**: Always creates backup before migration
- **Duplicate Detection**: Skips variables that already exist in database
- **Validation**: Validates all variables before saving
- **Error Handling**: Continues migration even if individual variables fail
- **Rollback Support**: Can restore from backup if needed

## Example Output

```
============================================================
ENVIRONMENT VARIABLE MIGRATION REPORT
============================================================
Migration status: SUCCESS
Backup file: environment_backups/environment_backup_20250902_011529.json
Variables migrated: 12
Variables skipped: 3
Errors encountered: 0
Sensitive variables: 4
Required variables: 2

Migrated variables (12):
  - FLASK_SECRET_KEY [SENSITIVE, REQUIRED]
  - DATABASE_URL [SENSITIVE, REQUIRED]
  - GEMINI_API_KEY [SENSITIVE]
  - DEBUG_MODE
  - APP_PORT
  - ...
============================================================
```

## Troubleshooting

### Common Issues

1. **No Critical Variables Found**: If the script reports no critical variables, ensure your application environment variables are set.

2. **Migration Fails**: Check the error messages in the output. Common causes:
   - Database connection issues
   - Permission problems
   - Invalid variable formats

3. **Variables Not Detected as Sensitive**: The script uses pattern matching. You can manually mark variables as sensitive after migration through the admin interface.

### Recovery

If migration causes issues:
1. Use the backup file created before migration
2. Restore environment variables manually if needed
3. Check the audit log in the admin interface for detailed change history

## Integration with Application

After migration:
1. Variables are automatically loaded at application startup
2. Changes through admin interface take effect immediately
3. All changes are logged for audit purposes
4. Sensitive values are encrypted in the database

## Security Considerations

- Sensitive values are encrypted using the Flask secret key
- Backup files contain unencrypted values - secure them appropriately
- The migration script requires database access
- Consider running migration in a secure environment