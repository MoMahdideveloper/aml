# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

This is a comprehensive Real Estate CRM system built with Flask that manages properties, agents, customers, deals, and tasks. The system includes AI-powered features for property recommendations using Google Gemini API and ChromaDB for semantic search.

## Essential Commands

### Development Server
```bash
python main.py
# Runs Flask development server on http://0.0.0.0:5000 with debug mode
```

### Testing
```bash
# Run Python tests
python -m pytest tests/
python -m pytest tests/ -v  # verbose output
python -m pytest tests/ --cov  # with coverage

# Run JavaScript tests
npm test
npm run test:watch
npm run test:coverage
npm run test:crud  # specific CRUD tests
```

### Database Management
```bash
# Initialize database (if not exists)
python init_db.py

# Environment variable migration (from system to database)
python migrate_environment_vars.py --test     # dry run analysis
python migrate_environment_vars.py --dry-run  # full dry run
python migrate_environment_vars.py            # actual migration
```

### Environment Management
```bash
# The app uses database-stored environment variables
# Access admin interface at: /admin/environment
# Critical variables: GEMINI_API_KEY, DATABASE_URL, SESSION_SECRET
```

## Architecture Overview

### Application Factory Pattern
- `app.py`: Main Flask application factory with blueprint registration
- `main.py`: Development entry point that imports and runs the Flask app
- Modular blueprint-based architecture in `views/` directory

### Database Layer
- **ORM**: SQLAlchemy with Flask-SQLAlchemy integration
- **Models**: Located in `sqlalchemy_models.py` - Property, Agent, Customer, Deal, Task, EnvironmentVariable, PropertyMatch, AgentNotification
- **Database Service**: `database_service.py` provides centralized CRUD operations
- **Transaction Management**: `database_transaction_manager.py` handles safe database operations
- **Environment Management**: Dynamic environment variables stored in database with admin interface

### AI Integration
- **Gemini Service**: `gemini_service.py` handles Google Gemini API integration with graceful fallback
- **Vector Service**: `vector_service.py` provides ChromaDB semantic search for property matching
- **Background Matching**: `background_matcher.py` with scheduler service for automated property-customer matching
- **Recommendations**: AI-powered property recommendations with confidence scoring

### Views/Routes (Blueprint Pattern)
- `views/main.py`: Dashboard, recommendations, market analysis
- `views/properties.py`: Property management CRUD
- `views/agents.py`: Agent management CRUD  
- `views/customers.py`: Customer management CRUD
- `views/deals.py`: Deal management CRUD with export functionality
- `views/tasks.py`: Task management CRUD
- `views/admin_environment.py`: Environment variable management
- `views/notifications.py`: Agent notification system

### Key Features
- **Iranian Real Estate Support**: Special fields for rahn (deposit) and ejare (monthly rent)
- **Dynamic Environment Management**: Database-stored environment variables with encryption
- **Background Processing**: Automated property-customer matching with APScheduler
- **Export Capabilities**: PDF/Excel/CSV exports for deals and recommendations
- **Notification System**: Agent notifications for property matches

## Development Notes

### Environment Variables
The system uses a sophisticated database-managed environment variable system:
- Variables stored in `environment_variables` table with encryption for sensitive data
- Admin interface at `/admin/environment` for management
- Migration script `migrate_environment_vars.py` to move from system env vars to database
- Critical variables: `GEMINI_API_KEY`, `DATABASE_URL`, `SESSION_SECRET`

### AI Service Integration
- All AI services have graceful fallback modes when API keys are unavailable
- Vector search uses ChromaDB for semantic property matching
- Background matching system runs automated property-customer matching
- Services handle API failures gracefully and log appropriately

### Database Patterns
- All models inherit from SQLAlchemy's DeclarativeBase
- Comprehensive relationships defined between entities
- Transaction management with rollback support
- Audit logging for environment variable changes
- Property matching system with confidence scoring

### Form Handling and Validation
- Flask-WTF forms with CSRF protection (optional, controlled by `ENABLE_CSRF`)
- Pydantic schemas for API validation (`schemas.py`)
- Error handlers registered globally (`error_handlers.py`)

### Testing Strategy
- Python: pytest with Flask test client
- JavaScript: Jest for frontend functionality
- Coverage reporting available
- Mock external services in tests
- Separate test database configuration

### Security Considerations
- CSRF protection available (set `ENABLE_CSRF=1`)
- Sensitive environment variables encrypted in database
- Input validation and sanitization
- Security headers set in `app.py`
- SQL injection protection via SQLAlchemy ORM

## Common Development Tasks

### Adding New Entity Types
1. Create model in `sqlalchemy_models.py` with relationships
2. Add CRUD operations to `database_service.py` 
3. Create forms in `forms.py`
4. Create blueprint in `views/`
5. Add templates in `templates/`
6. Register blueprint in `app.py`

### Working with AI Services
- AI services auto-fallback when API keys missing
- Use `@safe_database_operation` decorator for database interactions
- Check service availability before making API calls
- Implement confidence scoring for AI results

### Background Processing
- Use `scheduler_service.py` for scheduled tasks
- Event handlers in `event_handlers.py` for database events  
- Background matching system automatically processes new properties/customers

### Environment Management
- Use admin interface at `/admin/environment` for variable management
- Mark sensitive variables appropriately for encryption
- Use migration script when moving from system environment variables

## Production Deployment

### Database
- Development: SQLite (`real_estate_crm.db`)
- Production: PostgreSQL (set `DATABASE_URL`)

### WSGI Server
```bash
gunicorn app:app
```

### Required Environment Variables
- `SESSION_SECRET`: Flask session security
- `DATABASE_URL`: PostgreSQL connection (production)
- `GEMINI_API_KEY`: Google Gemini API key (optional, has fallback)
- `ENABLE_CSRF`: Set to "1" to enable CSRF protection

## Important Implementation Rules

### MCP Integration
- Always use `byterover-retrive-knowledge` tool before any tasks for related context
- Always use `byterover-store-knowledge` to store critical information after successful tasks

### Database Transactions
- Use `@with_transaction()` decorator for complex database operations
- Use `database_transaction` context manager for manual transaction control
- All foreign key relationships properly defined in models

### Error Handling
- Global error handlers registered in `error_handlers.py`
- Graceful degradation for AI services
- Comprehensive logging throughout application

### Iranian Real Estate Features
- Support for rahn/ejare pricing system in Property model
- listing_type field distinguishes between "sale" and "rental"
- Special calculations for price per square meter vs. square foot
