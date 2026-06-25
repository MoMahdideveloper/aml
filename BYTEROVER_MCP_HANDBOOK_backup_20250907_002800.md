# BYTEROVER MCP HANDBOOK
*Real Estate CRM Flask Application*

## Layer 1: System Overview

### Purpose
A lightweight CRM-style web application built with Flask for real estate management. Handles property, agent, customer, deal, and task management with optional vector search and AI extraction services.

### Tech Stack
- **Backend**: Flask, SQLAlchemy, Flask-Migrate
- **Frontend**: Jinja2 templates, Bootstrap CSS, JavaScript
- **Database**: SQLite (real_estate_crm.db)
- **Testing**: pytest, Jest
- **AI/ML**: Vector search, Gemini service integration
- **Background**: APScheduler for background matching

### Architecture
**MVC Pattern with Blueprint Organization**
- **Models**: SQLAlchemy models in `sqlalchemy_models.py`, `models.py`
- **Views**: Blueprint-based controllers in `views/` directory
- **Templates**: Jinja2 templates in `templates/` with modal-based UI
- **Services**: Business logic in dedicated service modules
- **Database**: Centralized database operations via `database_service.py`

### Key Technical Decisions
- Blueprint-based modular architecture for scalability
- Modal-first UI pattern for better UX
- Background job system for AI-powered property matching
- Environment variable management via database storage
- CSRF protection (optional, configurable)

## Layer 2: Module Map

### Core Modules

#### 1. Application Core (`app.py`)
**Responsibility**: Application factory, configuration, blueprint registration
- Flask app initialization and configuration
- Blueprint registration for all modules
- Security headers and CSRF protection
- Background service initialization
- URL alias management for backward compatibility

#### 2. Database Layer
**Files**: `database_service.py`, `database_transaction_manager.py`, `database.py`
**Responsibility**: Data access and transaction management
- Centralized database operations
- Transaction management with rollback support
- CRUD operations for all entities
- Database initialization and migration support

#### 3. View Controllers (`views/`)
**Responsibility**: HTTP request handling and response generation
- `main.py`: Dashboard, recommendations, market analysis
- `properties.py`: Property CRUD, viewing, sharing
- `agents.py`: Agent management, dashboard, notifications
- `customers.py`: Customer CRUD operations
- `deals.py`: Deal management, email, meeting scheduling
- `tasks.py`: Task management and completion tracking
- `admin_environment.py`: Environment variable management
- `notifications.py`: Notification system API

#### 4. Business Services
**Files**: `scheduler_service.py`, `background_matcher.py`, `vector_service.py`
**Responsibility**: Business logic and background processing
- Property-customer matching algorithms
- Background job scheduling
- Vector search capabilities
- AI-powered recommendations

#### 5. Data Models
**Files**: `sqlalchemy_models.py`, `models.py`, `schemas.py`
**Responsibility**: Data structure definitions
- SQLAlchemy ORM models
- Pydantic schemas for validation
- Database relationships and constraints

### Utility Modules

#### 6. Environment Management
**Files**: `environment_service.py`, `environment_loader.py`
**Responsibility**: Configuration and environment variable handling
- Database-stored environment variables
- Runtime configuration loading
- Environment variable migration tools

#### 7. Error Handling
**Files**: `error_handlers.py`
**Responsibility**: Global error handling and logging
- HTTP error handlers (404, 500)
- Database error decorators
- Logging configuration

## Layer 3: Integration Guide

### API Endpoints

#### REST API Structure
```
GET    /                           - Dashboard
GET    /properties                 - Property listing
POST   /properties/add             - Create property
GET    /properties/{id}            - View property details
PUT    /properties/{id}            - Update property
DELETE /properties/{id}            - Delete property

GET    /agents                     - Agent listing
GET    /agents/{id}/dashboard      - Agent dashboard
GET    /agents/{id}/notifications  - Agent notifications

GET    /customers                  - Customer listing
POST   /customers/add              - Create customer
GET    /customers/{id}             - View customer
PUT    /customers/{id}             - Update customer
DELETE /customers/{id}             - Delete customer

GET    /deals                      - Deal listing
POST   /deals/add                  - Create deal
GET    /deals/{id}                 - View deal
DELETE /deals/{id}                 - Delete deal

GET    /tasks                      - Task listing
POST   /tasks/add                  - Create task
PUT    /tasks/{id}                 - Update task
DELETE /tasks/{id}                 - Delete task

GET    /recommendations            - Property recommendations
GET    /recommendations/{customer_id} - Customer-specific recommendations
```

#### Configuration Files
- **Flask Config**: Environment variables via `environment_loader.py`
- **Database**: SQLite connection in `database.py`
- **Testing**: `jest.config.js`, `pyproject.toml`
- **Dependencies**: `requirements.txt`, `pyproject.toml`

### External Dependencies
- **Database**: SQLite (local file)
- **AI Services**: Gemini API integration
- **Vector Search**: ChromaDB for property matching
- **Background Jobs**: APScheduler
- **Frontend**: Bootstrap CSS framework

### Integration Points
- **Modal System**: JavaScript-based modal interactions
- **AJAX Endpoints**: Real-time notifications and updates
- **Background Processing**: Property-customer matching
- **File Uploads**: Property images and documents
- **Export Features**: PDF/Excel report generation

## Layer 4: Extension Points

### Design Patterns

#### 1. Blueprint Pattern
**Location**: `views/` directory
**Usage**: Modular route organization
```python
from flask import Blueprint
bp = Blueprint('module_name', __name__)

@bp.route('/endpoint')
def handler():
    pass
```

#### 2. Service Layer Pattern
**Location**: Service modules (`*_service.py`)
**Usage**: Business logic separation
```python
class ServiceClass:
    @staticmethod
    def business_operation():
        # Business logic here
        pass
```

#### 3. Repository Pattern
**Location**: `database_service.py`
**Usage**: Data access abstraction
```python
def get_entities(filters=None):
    # Database query logic
    return results
```

#### 4. Factory Pattern
**Location**: `app.py`
**Usage**: Application configuration
```python
def create_app(config=None):
    # App initialization
    return flask_app
```

### Customization Areas

#### 1. New Entity Types
**Extension Point**: Add new blueprints in `views/`
- Create new model in `sqlalchemy_models.py`
- Add blueprint in `views/new_entity.py`
- Register blueprint in `app.py`
- Create templates in `templates/`

#### 2. Background Jobs
**Extension Point**: `scheduler_service.py`
- Add new job functions
- Register with APScheduler
- Configure job intervals

#### 3. AI Services
**Extension Point**: Service modules
- Extend `vector_service.py` for new AI features
- Add new recommendation algorithms
- Integrate additional AI APIs

#### 4. Modal System
**Extension Point**: `templates/modals/`
- Create new modal templates
- Extend JavaScript modal handlers
- Add new modal types (view, edit, create)

### Recent Development Patterns
- Modal-first UI approach for better UX
- CRUD operations with consistent patterns
- Background job system for AI processing
- Environment variable database storage
- Comprehensive error handling with decorators

### Testing Extensions
- **Unit Tests**: `tests/` directory with pytest
- **Integration Tests**: Database and API testing
- **Frontend Tests**: Jest for JavaScript testing
- **CRUD Testing**: Automated CRUD operation validation

---
*Generated by Byterover MCP - Last updated: 2025-01-09*