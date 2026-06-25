# Product Requirements Document (PRD)
# Real Estate CRM - Flask Web Application

## Project Overview

A comprehensive Real Estate CRM system built with Flask, designed to manage properties, agents, customers, deals, and tasks. The system includes AI-powered features for property recommendations and data extraction.

## Core Features & Requirements

### 1. Entity Management

#### 1.1 Property Management
- **Properties Table**: Complete property lifecycle management
- **Fields**: ID, title, address, price, property_type, bedrooms, bathrooms, square_feet, description, status
- **Enhanced Fields**: year_built, parking_spaces, floors, units, property_condition, heating_type, cooling_type, rental_price, property_features, neighborhood, property_category
- **Iranian Real Estate Support**: listing_type (sale/rent), rahn (deposit), ejare (monthly rent)
- **CRUD Operations**: Create, read, update, delete properties
- **Status Tracking**: active, sold, pending, withdrawn

#### 1.2 Agent Management
- **Agents Table**: Real estate agent profiles
- **Fields**: ID, name, email, phone, license_number, commission_rate, specialization, hire_date, status
- **Relationships**: One-to-many with properties and deals
- **Features**: Agent performance tracking, commission calculations

#### 1.3 Customer Management
- **Customers Table**: Customer/lead management
- **Fields**: ID, name, email, phone, budget_min, budget_max, preferred_bedrooms, preferred_bathrooms, preferred_type, location_preference, status
- **Lead Status**: prospect, active, closed, lost
- **Preference Tracking**: Budget ranges, property preferences

#### 1.4 Deal Management
- **Deals Table**: Transaction tracking
- **Fields**: ID, property_id, customer_id, agent_id, deal_type, amount, commission, status, notes
- **Deal Types**: sale, purchase, rental, lease
- **Status Tracking**: pending, active, closed, cancelled
- **Commission Calculation**: Automatic based on agent commission rates

#### 1.5 Task Management
- **Tasks Table**: Activity and follow-up tracking
- **Fields**: ID, title, description, assigned_to, due_date, priority, status, task_type
- **Task Types**: call, meeting, follow_up, showing, paperwork
- **Priority Levels**: low, medium, high, urgent
- **Status Tracking**: pending, in_progress, completed, cancelled

### 2. AI-Powered Features

#### 2.1 Property Recommendations
- **Route**: `/recommendations` (general) and `/recommendations/<customer_id>` (customer-specific)
- **AI Integration**: Google Gemini API for intelligent property matching
- **Features**:
  - Customer preference analysis
  - Property matching with confidence scores
  - Fallback recommendations when AI service unavailable
  - Match reasoning explanations
- **Error Handling**: Graceful degradation with basic preference matching

#### 2.2 Data Extraction
- **Property Extraction**: AI-powered property data extraction from text
- **Customer Extraction**: Customer information extraction from descriptions
- **Form Auto-fill**: AI-assisted form completion
- **Confidence Scoring**: Extraction confidence levels

#### 2.3 Market Analysis
- **API Endpoint**: `/api/market-analysis`
- **Features**: AI-generated market insights and trends
- **Data Sources**: Property statistics, deal history, market data

### 3. Technical Architecture

#### 3.1 Backend Framework
- **Framework**: Flask with application factory pattern
- **Database**: SQLAlchemy ORM with Flask-Migrate
- **Database Support**: SQLite (development), PostgreSQL (production)
- **Architecture**: Blueprint-based modular design

#### 3.2 Database Models
- **ORM Models**: Property, Agent, Customer, Deal, Task, EnvironmentVariable
- **Relationships**: Properly defined foreign keys and relationships
- **Migrations**: Alembic-based database migrations
- **Indexing**: Optimized queries with appropriate indexes

#### 3.3 API Layer
- **Database Service**: `database_service.py` - centralized database operations
- **AI Service**: `gemini_service.py` - Google Gemini integration
- **Vector Service**: `vector_service.py` - ChromaDB for semantic search
- **Environment Service**: Dynamic environment variable management

#### 3.4 Frontend
- **Templates**: Jinja2 HTML templates
- **Styling**: Bootstrap-based responsive design
- **Forms**: Flask-WTF with CSRF protection
- **JavaScript**: Minimal vanilla JS for interactivity

### 4. Security & Configuration

#### 4.1 Environment Management
- **Dynamic Config**: Database-stored environment variables
- **Admin Interface**: Environment variable management UI
- **Security**: Sensitive data encryption and masking
- **Version Control**: Environment change history tracking

#### 4.2 Authentication & Authorization
- **Session Management**: Flask sessions with secure secret keys
- **CSRF Protection**: Optional CSRF token validation
- **Admin Access**: Protected admin routes

#### 4.3 Data Validation
- **Form Validation**: Flask-WTF forms with validation
- **Data Schemas**: Pydantic schemas for API validation
- **Input Sanitization**: XSS and injection prevention

### 5. Testing & Quality Assurance

#### 5.1 Test Suite
- **Framework**: pytest with Flask test client
- **Coverage**: Unit tests for routes, services, and models
- **Test Database**: In-memory SQLite for isolated testing
- **Mocking**: Mock external services (AI, vector store)

#### 5.2 Continuous Integration
- **CI Pipeline**: GitHub Actions for automated testing
- **Test Automation**: Run tests on push and pull requests
- **Code Quality**: Linting and formatting checks

### 6. Deployment & Operations

#### 6.1 Development Environment
- **Local Server**: `python main.py` (http://0.0.0.0:5000)
- **Hot Reload**: Debug mode for development
- **Database**: Local SQLite database

#### 6.2 Production Deployment
- **WSGI Server**: Gunicorn for production serving
- **Database**: PostgreSQL with connection pooling
- **Environment Variables**: Production-specific configuration
- **Monitoring**: Application logging and error tracking

### 7. File Structure

```
/
├── app.py                 # Flask application factory
├── main.py               # Development entry point
├── database.py           # SQLAlchemy setup
├── database_service.py   # Database operations layer
├── sqlalchemy_models.py  # ORM models
├── gemini_service.py     # AI service integration
├── vector_service.py     # Vector search service
├── forms.py              # Flask-WTF forms
├── schemas.py            # Pydantic validation schemas
├── environment_loader.py # Environment management
├── environment_service.py # Environment API service
├── views/                # Blueprint modules
│   ├── __init__.py
│   ├── main.py          # Main routes (dashboard, recommendations)
│   ├── properties.py    # Property management
│   ├── agents.py        # Agent management
│   ├── customers.py     # Customer management
│   ├── deals.py         # Deal management
│   ├── tasks.py         # Task management
│   └── admin_environment.py # Environment admin
├── templates/            # Jinja2 templates
│   ├── base.html
│   ├── dashboard.html
│   ├── properties.html
│   ├── agents.html
│   ├── customers.html
│   ├── deals.html
│   ├── tasks.html
│   ├── recommendations.html
│   └── admin_*.html
├── static/              # CSS, JS, images
├── tests/               # Test suite
│   ├── conftest.py
│   └── test_*.py
├── migrations/          # Database migrations
├── requirements.txt     # Python dependencies
├── pyproject.toml      # Project configuration
├── README.md           # Project documentation
├── AGENTS.md           # Development guidelines
└── .github/workflows/  # CI configuration
```

### 8. Dependencies

#### 8.1 Core Dependencies
- **Flask**: Web framework
- **SQLAlchemy**: ORM and database toolkit
- **Flask-SQLAlchemy**: Flask-SQLAlchemy integration
- **Flask-Migrate**: Database migrations
- **Flask-WTF**: Form handling and CSRF protection

#### 8.2 AI & Vector Dependencies
- **google-generativeai**: Google Gemini AI integration
- **chromadb**: Vector database for semantic search
- **numpy**: Numerical computing
- **scikit-learn**: Machine learning utilities

#### 8.3 Validation & Utilities
- **pydantic**: Data validation and serialization
- **email-validator**: Email validation
- **python-dotenv**: Environment variable loading

#### 8.4 Development & Testing
- **pytest**: Testing framework
- **coverage**: Code coverage reporting
- **black**: Code formatting
- **flake8**: Code linting

### 9. API Endpoints

#### 9.1 Core Routes
- `GET /` - Dashboard with statistics
- `GET /properties` - Property listing and management
- `GET /agents` - Agent listing and management
- `GET /customers` - Customer listing and management
- `GET /deals` - Deal listing and management
- `GET /tasks` - Task listing and management

#### 9.2 AI-Powered Routes
- `GET /recommendations` - General property recommendations
- `GET /recommendations/<customer_id>` - Customer-specific recommendations
- `GET /api/market-analysis` - Market analysis API

#### 9.3 Admin Routes
- `GET /admin/environment` - Environment variable management
- `POST /admin/environment` - Update environment variables
- `GET /admin/environment/history` - Environment change history

### 10. Future Enhancements (From project-suggestions.md)

#### 10.1 Core Features
- Document management with file uploads
- Email integration for automated follow-ups
- Calendar/scheduling for property viewings
- Advanced reporting dashboard
- Mobile-responsive design improvements

#### 10.2 Advanced Features
- Enhanced AI property matching algorithms
- Virtual tour integration
- Lead scoring system
- Commission tracking automation
- Comprehensive market analysis tools

#### 10.3 Integration Opportunities
- MLS (Multiple Listing Service) integration
- Payment processing for deposits
- SMS notification system
- CRM system integrations (Salesforce, HubSpot)
- Interactive mapping with neighborhood data

## Success Criteria

1. **Functionality**: All CRUD operations work correctly for all entities
2. **AI Integration**: Property recommendations work with high accuracy
3. **Performance**: Page load times under 2 seconds
4. **Reliability**: 99.9% uptime with proper error handling
5. **Security**: All data properly validated and secured
6. **Maintainability**: Comprehensive test coverage (>90%)
7. **Scalability**: System handles growth in data and users
8. **User Experience**: Intuitive interface with clear navigation

## Technical Constraints

1. **Python Version**: 3.11+
2. **Database**: SQLite (dev), PostgreSQL (prod)
3. **Browser Support**: Modern browsers (Chrome, Firefox, Safari, Edge)
4. **Response Time**: < 2 seconds for standard operations
5. **Concurrent Users**: Support for 100+ simultaneous users
6. **Data Volume**: Handle 10,000+ properties and customers efficiently

This PRD provides complete specifications for rebuilding the Real Estate CRM system with all current features and architecture patterns.