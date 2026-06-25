# Comprehensive Product Requirements Document (PRD)
# Real Estate CRM — Flask Web Application
## For Deep-Think Code Review & Architecture Analysis

---

## 1. Executive Summary

**Project Name:** Real Estate CRM (gptvli)  
**Tech Stack:** Python 3.11+ / Flask / SQLAlchemy / Google Gemini AI / ChromaDB / PostgreSQL  
**Target Market:** Iranian real estate agencies (with support for rahn/ejare pricing, Farsi localization, Maskan.ir integration)  
**Deployment:** Gunicorn + PostgreSQL (production), SQLite (development)  
**Codebase Size:** ~1,008 lines ORM models, ~1,216 lines database service, ~1,756 lines properties view, ~877 lines main view, 48 test files, 33+ templates, 14 modal templates, 13 service modules

---

## 2. Complete Data Model (22 ORM Models)

### 2.1 Core Business Entities

#### Property (primary entity, ~200 lines)
```
Fields:
  id, title, address, price, property_type, bedrooms, bathrooms, square_feet,
  description, status (active/sold/pending/withdrawn),
  year_built, parking_spaces, floors, units, property_condition,
  heating_type, cooling_type, rental_price, property_features,
  neighborhood, property_category,
  listing_type (sale/rent), rahn (deposit), ejare (monthly rent),
  latitude, longitude, image_filename,
  wall_covering, cabinet, flooring, document_type, facade, direction,
  file_code (auto-generated 6-digit Maskan-style code),
  source, source_code, is_ai_extracted,
  agent_id (FK → agents), created_at, updated_at

Computed properties:
  age, features_list, price_per_sqft, rahn_per_meter, ejare_per_meter,
  sale_price_per_meter, favorites_count, is_favorited_by_user(user_id)

Relationships:
  → Agent (many-to-one)
  → PropertyImage (one-to-many)
  → PropertyActivityLog (one-to-many)
  → ContactReveal (one-to-many)
  → PropertyFavorite (one-to-many)
  → PropertyEmbedding (one-to-one)
  → PropertyAIHistory (one-to-many)
  → Deal (one-to-many)
  → PropertyMatch (one-to-many)
```

#### Agent
```
Fields: id, name, email (unique), phone, license_number, commission_rate,
        specialization, hire_date, status, bio
Relationships: → Property[], Deal[], Task[], PropertyMatch[], AgentNotification[]
```

#### Customer
```
Fields: id, name, email, phone, budget_min, budget_max,
        preferred_bedrooms, preferred_bathrooms, preferred_type,
        location_preference, status (prospect/active/closed/lost),
        preferences (text), group_id (FK → customer_groups)
Relationships: → Deal[], CustomerGroup
```

#### Deal
```
Fields: id, status (prospecting/active/closed/cancelled),
        offer_amount, commission, deal_type, notes,
        property_id (FK), customer_id (FK), agent_id (FK),
        created_at, updated_at, closed_at
Relationships: → Property, Customer, Agent
```

#### Task
```
Fields: id, title, description, priority (low/medium/high/urgent),
        status (pending/in_progress/completed/cancelled),
        due_date, completed_at, agent_id (FK)
Relationships: → Agent
```

### 2.2 Supporting/Feature Models

| Model | Purpose | Key Fields |
|-------|---------|------------|
| `PropertyImage` | Multi-image gallery per property | property_id, image_url, is_primary |
| `PropertyActivityLog` | Lifecycle event tracking | property_id, action, details, user_id |
| `ContactReveal` | Tracks contact info reveals | property_id, viewer_user_id |
| `CustomerGroup` | Customer segmentation (VIP, Investor) | name, description |
| `Builder` | Construction company database | name, contact_person, phone, email, specialization, website, portfolio_count, notes, status |
| `User` | Authentication & profiles | username, email, password_hash, full_name, phone, role (admin/agent/viewer), is_active, last_login |
| `PublicPropertySubmission` | No-login property submission form | submitter_name, phone, email, property data fields, status (pending/approved/rejected), admin_notes |

### 2.3 AI & Matching Models

| Model | Purpose | Key Fields |
|-------|---------|------------|
| `PropertyMatch` | Property↔Customer match records | property_id, customer_id, agent_id, match_score, match_reasons (JSON), status, source |
| `PropertyFavorite` | User favorites | property_id, user_id, category, notes, created_at |
| `AgentNotification` | Agent alert system | agent_id, title, message, notification_type, priority, related_property_id, related_customer_id, match_id, status (unread/read/dismissed) |
| `PropertyEmbedding` | Vector embeddings for semantic search | property_id, embedding_json, content_hash, model_name |
| `PropertyAIHistory` | AI extraction audit trail | property_id, raw_data, created_at, user_note |

### 2.4 Infrastructure Models

| Model | Purpose | Key Fields |
|-------|---------|------------|
| `EnvironmentVariable` | Dynamic config stored in DB | key, value, description, is_sensitive, is_active, updated_at |
| `EnvironmentChangeLog` | Config change audit trail | variable_key, old_value, new_value, changed_by, change_type |
| `MatchingJobRun` | Matching cycle idempotency & observability | idempotency_key, trigger_source, status, property_ids, customer_ids, result_json, started_at, finished_at |
| `RematchQueue` | Queue of rematch requests from model change events | entity_type, entity_id, reason, status, priority |
| `AutomationRule` | Workflow automation rule definitions | name, description, trigger_type, conditions (JSON), actions (JSON), is_active |
| `AutomationAuditLog` | Automation execution records | rule_id, trigger_event, status, details (JSON) |
| `SmsOutboundMessage` | Async SMS delivery queue | recipient, message, provider, status, attempts, max_attempts, sent_at, error_message, provider_message_id, created_by_user_id (FK → users) |

---

## 3. Service Layer Architecture (13 Services)

### 3.1 DatabaseService (`services/database_service.py` — 1,216 lines)
- Central data access layer for all CRUD operations
- 47 public methods covering all entities
- Transaction management via `database_transaction_manager.py` decorators (`@with_transaction`, `@safe_database_operation`)
- Advanced property search with filtering, sorting, pagination
- Bulk update operations
- Dashboard statistics aggregation
- Export functionality (recommendations, deals reports)
- Property statistics and history tracking
- AI history CRUD operations

**Critical observation:** This is a God-class pattern — a single service handling ALL entity operations with 1,200+ lines.

### 3.2 GeminiService (`services/gemini_service.py` — 296 lines)
- Google Gemini AI integration via `google-genai` SDK
- Property recommendations with confidence scoring
- Reasoning generation with caching (SHA256-keyed)
- Fallback recommendations when AI unavailable
- Text extraction: property and customer data from free text
- Image extraction: property details from flyers/screenshots
- Market analysis generation
- Property description generation

**Architecture:** Uses an abstracted LLM provider layer (`services/llm/`) allowing provider swapability.

### 3.3 VectorService (`services/vector_service.py` — 450 lines)
- DB-backed embeddings (not ChromaDB despite original design)
- pgvector support for PostgreSQL nearest-neighbor queries
- Hybrid scoring: semantic similarity + rule-based matching
- Property indexing with content-hash deduplication
- Cosine similarity computation for SQLite fallback
- Match reason generation
- Abstracted embedding provider (`services/embeddings/`)

### 3.4 FavoritesService (`services/favorites_service.py` — 543 lines)
- Full CRUD for property favorites
- Category-based organization
- Bulk removal operations
- Popular properties ranking
- User favorite statistics and category listing

### 3.5 NotificationService (`services/notification_service.py` — 499 lines)
- Agent notification creation and management
- Property match notifications with email alerts
- System notifications
- SMTP email delivery
- Daily digest emails
- Read/dismiss workflow
- Notification summary/counts

### 3.6 MonitoringService (`services/monitoring_service.py` — 577 lines)
- In-memory metrics collection (deque-based)
- Background matching job tracking (start/completion/error)
- System health checks (database, resources)
- Performance metrics with percentile calculations
- Error rate alerting
- Metrics export API
- Notification activity logging

### 3.7 SchedulerService (`services/scheduler_service.py` — 397 lines)
- APScheduler `BackgroundScheduler` with thread pool
- Scheduled jobs:
  - **Property matching** (every 2 hours)
  - **Rematch queue processing** (every 30 minutes)
  - **Old match cleanup** (daily at 3 AM)
  - **Notification digests** (daily at 8 AM)
  - **Overdue task processing** (every 6 hours)
  - **SMS queue processing** (every 60 seconds)
- Job execution/error event listeners
- Immediate trigger API for on-demand matching

### 3.8 SMSService (`services/sms_service.py` — 204 lines)
- Queue-based async SMS delivery
- Provider abstraction (MelipayamakProvider, LogProvider)
- Iranian phone number normalization (98/0098 prefix handling)
- Retry logic with configurable max attempts
- Provider error classification: Configuration / Temporary / Permanent

### 3.9 AutomationService (`services/automation_service.py` — ~9KB)
- Rule-based workflow automation engine
- Trigger/condition/action pattern
- Audit logging for all executions

### 3.10 SearchService (`services/search_service.py` — ~5KB)
- Full-text search across entities
- Multi-field search with relevance scoring

### 3.11 EmbeddingService (`services/embedding_service.py` — ~3KB)
- Embedding generation abstraction
- Provider pattern for embedding models

### 3.12 EnvironmentService (`services/environment_service.py` — 42KB)
- Dynamic environment variable management
- In-database configuration storage
- Encryption for sensitive values
- Change history tracking with audit trail
- Backup/restore functionality

### 3.13 BackgroundMatcher (`background_matcher.py` — 438 lines)
- Property↔Customer matching engine
- Batch processing (configurable batch_size=50)
- Idempotency via `MatchingJobRun` records
- Configurable thresholds: min_match_score=0.5, notification_threshold=0.7
- Basic fallback matching when AI unavailable
- Match record persistence
- Agent notification creation for high-score matches

---

## 4. View Layer (12 Blueprints)

### 4.1 Properties Blueprint (`views/properties.py` — 1,756 lines, LARGEST)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/properties` | GET | Property listing with advanced filters (type, category, condition, neighborhood, price range, sqft, year, agent) |
| `/properties/add` | GET/POST | Add property form with image upload, Maskan field constants |
| `/properties/<id>` | GET | Full property detail page with related properties, activity log, AI history |
| `/properties/<id>/view` | GET | View modal JSON endpoint |
| `/properties/<id>/edit` | GET | Edit modal JSON endpoint |
| `/properties/<id>/update` | POST | Update with comprehensive validation |
| `/properties/<id>/delete` | POST | Delete with confirmation |
| `/properties/<id>/share` | GET | Share options |
| `/properties/compare` | GET | Side-by-side comparison |
| `/properties/map` | GET | Interactive map view |
| `/properties/<id>/reveal-contact` | POST | Contact reveal tracking |
| `/properties/smart-search` | POST | Semantic vector search |
| `/properties/<id>/extract-image` | POST | AI image extraction |
| `/properties/<id>/ai-history` | GET | AI extraction history |
| `/properties/<id>/ai-history/<hid>/delete` | POST | Delete AI history |
| `/properties/<id>/favorite` | POST | Add to favorites |
| `/properties/<id>/favorite` | DELETE | Remove from favorites |
| `/properties/favorites` | GET | List user favorites |

**Rate limiting:** In-memory defaultdict-based (NOT production-ready)

### 4.2 Main Blueprint (`views/main.py` — 877 lines)
| Endpoint | Purpose |
|----------|---------|
| `/` | Dashboard with stats |
| `/market-analysis` | Market analysis page |
| `/calculators` | Rahn↔Ejare, commission, mortgage calculators |
| `/sms-panel` | SMS management panel |
| `/sms/send` | Queue SMS messages |
| `/sms/history` | SMS delivery history |
| `/customer-groups` | CRUD for customer groups |
| `/settings` | App settings |
| `/recommendations` | General recommendations |
| `/recommendations/<customer_id>` | Customer-specific recommendations |
| `/api/market-analysis` | Market analysis API |
| `/api/parse-property` | AI text→property extraction |
| `/api/parse-customer` | AI text→customer extraction |
| `/export/recommendations` | PDF/Excel/JSON export |
| `/schedule-viewing/<property_id>` | Viewing scheduling |
| `/language/<lang_code>` | Language switching |

### 4.3 Auth Blueprint (`views/auth.py` — 246 lines)
- Login/Register/Logout with session-based auth
- Profile viewing/editing
- Password change
- Context processor for `current_user` injection
- **No middleware enforcement** — manual `session.get("user_id")` checks per endpoint

### 4.4 Other Blueprints
| Blueprint | File | Lines | Purpose |
|-----------|------|-------|---------|
| Agents | `views/agents.py` | 11KB | Agent CRUD + performance dashboard |
| Customers | `views/customers.py` | 10KB | Customer CRUD |
| Deals | `views/deals.py` | 12KB | Deal CRUD + commission tracking |
| Tasks | `views/tasks.py` | 10KB | Task CRUD + completion |
| Notifications | `views/notifications.py` | 11KB | Agent notification panel |
| Automations | `views/automations.py` | 2KB | Automation rule management |
| Admin Environment | `views/admin_environment.py` | 21KB | Dynamic config admin |
| Vector | `views/vector.py` | 2KB | Vector service management |

---

## 5. Frontend Architecture

### 5.1 Template Layer
- **Base template:** `base.html` (16KB) — layout, sidebar, header
- **33+ page templates** with significant size variation
- **14 modal templates** in `templates/modals/`:
  - `property_edit_modal.html` — **52KB** (extremely large for a modal)
  - `deal_view_modal.html` — 20KB
  - `email_compose_modal.html` — 18KB
  - `property_view_modal.html` — 24KB
  - Plus: agent_edit, customer_edit, customer_view, meeting_schedule, property_share, task_edit, task_view, viewing_schedule
- **4 partial templates** in `templates/partials/`
- **1 analysis template**

### 5.2 Static Assets
- **CSS:** 3 files in `static/css/`
- **JavaScript:** 13 files in `static/js/`
- **Uploads:** `static/uploads/` directory

### 5.3 Styling & Framework
- Bootstrap-based responsive design
- Jinja2 templating with Flask-WTF forms
- Vanilla JavaScript for interactivity
- Flask-Babel for i18n (Farsi/English)

---

## 6. AI/ML Pipeline

### 6.1 LLM Integration
```
services/llm/
├── __init__.py (provider registry)
├── providers/
│   └── (individual LLM provider implementations)
```
- Abstracted LLM provider pattern
- Google Gemini as primary provider
- OpenAI client for Kie.ai translation API

### 6.2 Embedding Pipeline
```
services/embeddings/
├── __init__.py
├── (embedding provider implementations)
```
- Abstracted embedding provider
- Content-hash deduplication
- DB-backed storage (PropertyEmbedding model)
- Optional pgvector acceleration on PostgreSQL

### 6.3 Semantic Search Flow
```
User Query → DummyCustomer object → VectorService.search_properties()
  → Embedding generation → Cosine similarity (SQLite) or pgvector (PG)
  → Hybrid scoring (semantic + rule-based) → Match reasons → Results
```

### 6.4 Background Matching Flow
```
Scheduler (every 2hrs) → BackgroundMatcher.run_matching_cycle()
  → Get active properties + customers
  → Batch processing (50 per batch)
  → GeminiService.get_property_recommendations() per customer
  → Save matches to DB (idempotent via MatchingJobRun)
  → Create AgentNotifications for high-score matches (>0.7)
  → Optional email alerts
```

---

## 7. External Integrations

| Integration | Library | Purpose |
|-------------|---------|---------|
| Google Gemini | `google-genai==1.62.0` | AI recommendations, extraction, analysis |
| OpenAI Client | `openai==1.12.0` | Kie.ai translation API |
| Melipayamak | `melipayamak==1.0.1` | Iranian SMS gateway |
| PostgreSQL | `psycopg==3.3.2` | Production database |
| APScheduler | `apscheduler==3.11.2` | Background job scheduling |
| ReportLab | `reportlab==4.4.9` | PDF report generation |
| OpenPyXL | `openpyxl==3.1.5` | Excel export |
| Flask-Babel | `Flask-Babel==4.0.0` | i18n / Farsi localization |
| psutil | `psutil==7.2.2` | System resource monitoring |

---

## 8. Iranian Real Estate Domain Features

### 8.1 Maskan Field Constants (`maskan_field_constants.py` — 6KB)
Predefined dropdowns for:
- Wall Covering types
- Cabinet types
- Cooling/Heating systems
- Flooring types
- Document types
- Property types
- Facade materials
- Directions
- Property features

### 8.2 Pricing Model
- **Sale:** price (total), sale_price_per_meter (computed)
- **Rental:** rahn (deposit lump sum), ejare (monthly rent)
- **Calculators:** Rahn↔Ejare conversion, commission, mortgage

### 8.3 File Code System
- Auto-generated 6-digit unique codes (Maskan-style: `file_code`)
- Generated via SQLAlchemy event listener on insert

### 8.4 Localization
- Flask-Babel with Farsi (fa) and English (en)
- AI-powered translation via Kie.ai script (`scripts/translate_ai.py`)
- Language switcher in UI

---

## 9. Authentication & Authorization

### 9.1 Current Implementation
- Session-based authentication (`flask.session`)
- User model with `werkzeug.security` password hashing
- Roles: `admin`, `agent`, `viewer`
- Manual session checks in each endpoint (no global middleware)
- Context processor injects `current_user` into templates
- **CSRF:** Flask-WTF CSRFProtect enabled but exemptions applied to many routes

### 9.2 Security Concerns (for review)
- No `login_required` decorator middleware — each route manually checks session
- No role-based access control enforcement
- No API token/JWT authentication for JSON endpoints
- Rate limiting is in-memory (not distributed)
- Sensitive environment variables stored in DB with masking

---

## 10. Error Handling

### 10.1 Centralized Error Handlers
- `error_handlers.py` (10KB) — Global Flask error handlers (404, 500, etc.)
- `property_error_handlers.py` (16KB) — Property-specific error handling
- Blueprint-level error handler registration via `register_blueprint_error_handlers(bp)`
- `safe_json_response` helper for API endpoints
- `handle_database_error` for DB operation failures

---

## 11. Background Jobs & Scheduling

| Job | Schedule | Service |
|-----|----------|---------|
| Property-Customer Matching | Every 2 hours | `BackgroundMatcher` |
| Rematch Queue Processing | Every 30 minutes | `process_rematch_queue_job` |
| Old Match Cleanup | Daily at 3 AM | `cleanup_old_matches_job` |
| Notification Digests | Daily at 8 AM | `send_notification_digest_job` |
| Overdue Task Processing | Every 6 hours | `process_overdue_tasks_job` |
| SMS Queue Processing | Every 60 seconds | `process_sms_queue_job` |

---

## 12. Testing Infrastructure

### 12.1 Test Files (48 total)
```
tests/
├── conftest.py          — Shared fixtures, test app factory, in-memory SQLite
├── test_crud_database_service.py (29KB) — DB service unit tests
├── test_crud_routes.py (26KB)          — Route integration tests
├── test_crud_forms.py (31KB)           — Form validation tests
├── test_crud_integration.py (21KB)     — End-to-end CRUD tests
├── test_recommendations_integration.py (27KB) — AI recommendations
├── test_favorites_service.py (23KB)    — Favorites service tests
├── test_environment_views.py (23KB)    — Admin environment tests
├── test_environment_service.py (21KB)  — Environment service tests
├── test_property_routes_enhanced.py (17KB) — Property route tests
├── test_property_error_handlers.py (15KB) — Error handler tests
├── test_background_matching_system.py (13KB) — Background matching
├── test_property_edit_modal_integration.js (20KB) — JS modal tests
├── test_property_modal_system.js (18KB) — JS property modal tests
├── test_crud_utils.js (13KB)           — JS utility tests
└── ... (33 more test files)
```

### 12.2 Test Infrastructure
- pytest with Flask test client
- In-memory SQLite for isolation
- Jest for JavaScript tests
- Mocking for external services
- GitHub Actions CI pipeline

---

## 13. File Structure (Actual, Complete)

```
gptvli/
├── app.py                          # Flask factory (197 lines)
├── main.py                         # Dev entry point
├── database.py                     # SQLAlchemy init (5KB)
├── database_transaction_manager.py # Transaction decorators (9KB)
├── sqlalchemy_models.py            # 22 ORM models (1,008 lines)
├── forms.py                        # Flask-WTF forms (22KB)
├── schemas.py                      # Pydantic validation (2KB)
├── error_handlers.py               # Global error handlers (10KB)
├── property_error_handlers.py      # Property error handlers (16KB)
├── event_handlers.py               # SQLAlchemy event handlers (8KB)
├── environment_loader.py           # Env var loading (7KB)
├── background_matcher.py           # Matching engine (18KB)
├── maskan_field_constants.py       # Iranian field constants (6KB)
├── init_db.py                      # DB initialization (7KB)
├── worker.py                       # Background worker entry (1KB)
│
├── services/
│   ├── database_service.py         # Central data layer (49KB) ⚠️
│   ├── environment_service.py      # Dynamic config (42KB) ⚠️
│   ├── gemini_service.py           # AI service (12KB)
│   ├── vector_service.py           # Vector search (18KB)
│   ├── favorites_service.py        # Favorites (20KB)
│   ├── notification_service.py     # Notifications (20KB)
│   ├── monitoring_service.py       # Monitoring (23KB)
│   ├── scheduler_service.py        # Background scheduler (14KB)
│   ├── sms_service.py              # SMS queue (7KB)
│   ├── automation_service.py       # Automations (9KB)
│   ├── search_service.py           # Search (5KB)
│   ├── embedding_service.py        # Embeddings (3KB)
│   ├── llm/                        # LLM provider abstraction
│   │   └── providers/
│   ├── sms/                        # SMS provider abstraction
│   │   └── providers/
│   └── embeddings/                 # Embedding provider abstraction
│
├── views/
│   ├── main.py                     # Dashboard, recommendations, export (33KB)
│   ├── properties.py               # Property management (75KB) ⚠️
│   ├── auth.py                     # Authentication (8KB)
│   ├── agents.py                   # Agent management (11KB)
│   ├── customers.py                # Customer management (11KB)
│   ├── deals.py                    # Deal management (13KB)
│   ├── tasks.py                    # Task management (10KB)
│   ├── notifications.py            # Notification panel (12KB)
│   ├── automations.py              # Automation rules (2KB)
│   ├── admin_environment.py        # Config admin (21KB)
│   └── vector.py                   # Vector management (2KB)
│
├── templates/
│   ├── base.html                   # Base layout (16KB)
│   ├── dashboard.html + modern_dashboard.html
│   ├── properties.html (42KB), property_detail.html (22KB)
│   ├── agents.html, customers.html, deals.html, tasks.html
│   ├── recommendations.html, market_analysis.html
│   ├── sms_panel.html, calculators.html, map_view.html
│   ├── builders.html, compare_properties.html
│   ├── auth_login.html, auth_register.html, profile.html, settings.html
│   ├── admin_environment.html, admin_automations.html
│   ├── 404.html, 500.html
│   ├── modals/ (14 modals, property_edit_modal.html = 52KB ⚠️)
│   └── partials/ (4 partials)
│
├── static/
│   ├── css/ (3 files)
│   ├── js/ (13 files)
│   └── uploads/
│
├── tests/ (48 files — Python + JavaScript)
├── scripts/ (10 utility scripts)
├── migrations/ (Alembic)
├── translations/ (i18n)
├── .github/workflows/ (CI pipeline)
└── docs/ (5 doc files)
```

---

## 14. Key Metrics & Red Flags for Deep Analysis

### 14.1 Code Size Hotspots ⚠️
| File | Size | Concern |
|------|------|---------|
| `views/properties.py` | 75KB / 1,756 lines | Monolithic view with 18+ endpoints |
| `services/database_service.py` | 49KB / 1,216 lines | God-class, 47 methods for all entities |
| `services/environment_service.py` | 42KB | Oversized for config management |
| `templates/modals/property_edit_modal.html` | 52KB | Extremely large Jinja2 template |
| `sqlalchemy_models.py` | 46KB / 1,008 lines | 22 models in single file |
| `templates/properties.html` | 42KB | Large monolithic template |
| `forms.py` | 22KB | All forms in single file |

### 14.2 Architecture Concerns
1. **God-class `DatabaseService`** — 1,216 lines handling ALL entity CRUD; violates Single Responsibility
2. **No auth middleware** — Each route manually checks `session.get("user_id")`; missing `login_required` decorator
3. **In-memory rate limiting** — `defaultdict(list)` won't survive restarts, not distributed
4. **In-memory monitoring metrics** — `deque`-based; lost on restart
5. **Global service singletons** — `database_service = DatabaseService()` at module level; tight coupling
6. **Circular import pattern** — `views/auth.py` does `from sqlalchemy_models import User` inside functions
7. **22 models in single file** — `sqlalchemy_models.py` should be split by domain
8. **Duplicate template pattern** — `property_detail.html` AND `property_details.html` exist
9. **Mixed API/HTML endpoints** — Same blueprint serves both rendered HTML and JSON responses
10. **Test files at root** — `test_properties_route.py`, `test_recommendations.py`, `test_recommendations_fixes.py` not in `tests/` directory

### 14.3 Security Review Points
1. CSRF exemptions on multiple routes
2. No API authentication (token/JWT) for JSON endpoints
3. Session-based auth without session fixation protection
4. Raw SQL in some vector service queries (SQL injection risk potential)
5. File upload handling — `secure_filename` used but no file type validation visible
6. Password minimum length is only 6 characters
7. No account lockout after failed login attempts
8. `is_active` check only on login, not on subsequent requests

### 14.4 Performance Concerns
1. No database query pagination in several listing endpoints
2. N+1 query potential in property listings with relationships
3. Background matcher processes ALL active properties × ALL active customers (quadratic)
4. No caching layer (Redis/Memcached) for frequently accessed data
5. Embedding computation happens synchronously on indexing
6. No connection pooling configuration visible for SQLite
7. SMS queue polling every 60 seconds regardless of queue emptiness

### 14.5 Data Integrity
1. No database-level constraints for many business rules (e.g., deal amounts)
2. `delete_agent` doesn't handle cascade deletion properly (orphan deals/tasks)
3. Property status transitions not enforced
4. No optimistic locking for concurrent updates
5. `datetime.utcnow` usage (deprecated in Python 3.12+, use `datetime.now(UTC)`)

---

## 15. Dependency Inventory

### Production Dependencies
```
flask==3.1.2              flask-sqlalchemy==3.1.1    flask-migrate==4.1.0
flask-wtf==1.2.2          Flask-Babel==4.0.0         sqlalchemy==2.0.46
alembic==1.18.3           google-genai==1.62.0       openai==1.12.0
melipayamak==1.0.1        apscheduler==3.11.2        pydantic==2.12.5
email-validator==2.3.0    python-dotenv==1.2.1       gunicorn==25.0.3
psycopg==3.3.2            numpy==2.4.2               openpyxl==3.1.5
reportlab==4.4.9          psutil==7.2.2              cryptography==46.0.4
```

### Development/Testing
```
pytest                    coverage                   black
flake8                    jest (JS tests)
```

---

## 16. API Endpoint Catalog (Complete)

### Core HTML Pages
```
GET  /                                Dashboard
GET  /properties                      Property list
POST /properties/add                  Add property
GET  /properties/<id>                 Property detail page
GET  /properties/map                  Map view
GET  /properties/compare              Compare properties
GET  /agents                          Agent list
GET  /customers                       Customer list
GET  /deals                           Deal list
GET  /tasks                           Task list
GET  /recommendations                 Recommendations
GET  /recommendations/<customer_id>   Customer recommendations
GET  /market-analysis                 Market analysis
GET  /calculators                     Financial calculators
GET  /sms-panel                       SMS panel
GET  /settings                        Settings
GET  /auth/login                      Login
GET  /auth/register                   Register
GET  /auth/profile                    Profile
GET  /admin/environment               Environment admin
GET  /admin/automations               Automation admin
```

### JSON/API Endpoints
```
GET    /api/market-analysis              Market analysis data
POST   /api/parse-property               AI text→property
POST   /api/parse-customer               AI text→customer
POST   /properties/<id>/favorite         Add favorite
DELETE /properties/<id>/favorite         Remove favorite
GET    /properties/favorites             List favorites
POST   /properties/<id>/reveal-contact   Track contact reveal
POST   /properties/smart-search          Semantic search
POST   /sms/send                         Queue SMS
GET    /sms/history                      SMS history
GET    /export/recommendations           Export (PDF/Excel/JSON)
GET    /customer-groups                  List groups
POST   /customer-groups                  Create group
DELETE /customer-groups/<id>             Delete group
GET    /language/<lang_code>             Set language
```

---

## 17. Questions for Deep-Think Analysis

1. **Should `DatabaseService` be split into domain-specific services** (PropertyService, AgentService, CustomerService, DealService, TaskService)?
2. **What's the best auth middleware pattern** for Flask that enforces `login_required` globally while allowing public routes?
3. **How should the background matching algorithm be optimized** to avoid O(properties × customers) complexity?
4. **Should the vector service move to a dedicated vector DB** (Qdrant, Pinecone) instead of pgvector for scalability?
5. **What caching strategy** (Redis) would best reduce database load for dashboard stats and property listings?
6. **How should the 52KB property edit modal template be refactored** into smaller components?
7. **Should the API layer be separated** from the HTML-rendering views (e.g., `/api/v1/` prefix)?
8. **What's the best approach for real-time notifications** instead of polling (WebSocket, SSE)?
9. **How should rate limiting be implemented** for production (Redis-backed, per-user)?
10. **Should the 22-model `sqlalchemy_models.py` be split** per domain, and what's the best import pattern?

---

*Generated: 2026-02-17 | Codebase snapshot for deep-think architectural review*
