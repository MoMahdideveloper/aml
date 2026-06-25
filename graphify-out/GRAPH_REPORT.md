# Graph Report - gptvli  (2026-06-10)

## Corpus Check
- 44 files · ~40,695 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 714 nodes · 1445 edges · 46 communities (30 shown, 16 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 111 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9230f744`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]

## God Nodes (most connected - your core abstractions)
1. `CRUDUtils` - 43 edges
2. `Property` - 38 edges
3. `Customer` - 34 edges
4. `BackgroundMatcher` - 24 edges
5. `AccessibilityEnhancements` - 24 edges
6. `EventHandlers` - 23 edges
7. `PropertyEditModal` - 23 edges
8. `DualViewHandler` - 22 edges
9. `RecommendationsManager` - 21 edges
10. `create_app()` - 20 edges

## Surprising Connections (you probably didn't know these)
- `Property` --uses--> `Property`  [INFERRED]
  vector_init.py → sqlalchemy_models.py
- `BackgroundMatcher` --uses--> `AgentNotification`  [INFERRED]
  background_matcher.py → sqlalchemy_models.py
- `BackgroundMatcher` --uses--> `Customer`  [INFERRED]
  background_matcher.py → sqlalchemy_models.py
- `BackgroundMatcher` --uses--> `Property`  [INFERRED]
  background_matcher.py → sqlalchemy_models.py
- `BackgroundMatcher` --uses--> `PropertyMatch`  [INFERRED]
  background_matcher.py → sqlalchemy_models.py

## Import Cycles
- 1-file cycle: `app.py -> app.py`
- 1-file cycle: `migrate_environment_vars.py -> migrate_environment_vars.py`
- 1-file cycle: `sqlalchemy_models.py -> sqlalchemy_models.py`
- 1-file cycle: `environment_loader.py -> environment_loader.py`

## Communities (46 total, 16 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.18
Nodes (13): Base, datetime, DeclarativeBase, EnvironmentVariableForm, Form for creating and editing environment variables with enhanced validation, any, Flask, EnvironmentVariable (+5 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (22): create_app(), _env_bool(), Flask, Application factory that configures Flask, DB, routes, and security headers., Global default-deny session auth middleware., register_auth_middleware(), FlaskContextTask, _ensure_sqlite_schema_compatibility() (+14 more)

### Community 3 - "Community 3"
Cohesion: 0.07
Nodes (15): Animate, API, bindCopilotPitchButtons(), copilotPitchBindings, currentDate, debounce(), initializeApp(), initializeFormValidation() (+7 more)

### Community 4 - "Community 4"
Cohesion: 0.08
Nodes (24): database_savepoint(), database_transaction(), DatabaseTransactionManager, Any, Database Transaction Manager Provides transaction management with rollback capa, Rollback to a specific savepoint                  Args:             name: Sav, Release a savepoint                  Args:             name: Savepoint name, Context manager for savepoint operations                  Args:             n (+16 more)

### Community 5 - "Community 5"
Cohesion: 0.25
Nodes (9): AgentNotification, BackgroundMatcher, Customer, Property, Background matching engine for property-customer recommendations., PropertyForm, PropertyMatch, MatchingJobRun (+1 more)

### Community 6 - "Community 6"
Cohesion: 0.14
Nodes (15): EventHandlers, Any, Customer, Property, Database event handlers that enqueue lightweight rematch requests.     Heavy mat, Manual trigger now enqueues rematch requests for worker processing., MatchingJobRun, Session (+7 more)

### Community 7 - "Community 7"
Cohesion: 0.09
Nodes (23): BusinessLogicError, create_error_response(), flash_and_redirect(), handle_database_error(), handle_form_errors(), log_error(), Comprehensive error handling for Flask application Provides consistent error re, Register error handlers for a specific blueprint (+15 more)

### Community 8 - "Community 8"
Cohesion: 0.16
Nodes (11): EnvironmentMigrator, Detect sensitive variables based on key patterns and values, Filter environment variables to include only migration candidates, Generate description for environment variable based on key and value, Migrate environment variables to database, Handles migration of system environment variables to database storage, Test migration with current application environment variables, Print detailed migration report (+3 more)

### Community 9 - "Community 9"
Cohesion: 0.17
Nodes (20): announceToScreenReader(), escapeHtml(), formatCurrency(), formatListingType(), formatPropertyCategory(), formatPropertyCondition(), formatPropertyType(), formatTomanCurrency() (+12 more)

### Community 10 - "Community 10"
Cohesion: 0.15
Nodes (21): FlaskForm, AgentEditForm, AgentForm, BaseNoCSRFForm, CustomerEditForm, CustomerForm, DealForm, Meta (+13 more)

### Community 16 - "Community 16"
Cohesion: 0.18
Nodes (12): EnvironmentLoader, load_environment_at_startup(), Flask, Environment Loader for loading stored environment variables at application start, Get dictionary of variables loaded from database, Check if fallback to system environment was used, Get summary of environment loading status, Loads environment variables from database at application startup (+4 more)

### Community 17 - "Community 17"
Cohesion: 0.11
Nodes (9): Property, Calculate property age, Get property features as a list, Calculate price per square foot, Calculate rahn (deposit) per square meter for rentals, Calculate ejare (monthly rent) per square meter for rentals, Calculate sale price per square meter for sales, Get the total number of times this property has been favorited (+1 more)

### Community 18 - "Community 18"
Cohesion: 0.08
Nodes (34): get_property_with_fallback_data(), get_property_with_related_data(), handle_database_connection_error(), _handle_property_error(), handle_property_errors(), log_property_operation(), PropertyError, PropertyNotFoundError (+26 more)

### Community 19 - "Community 19"
Cohesion: 0.15
Nodes (9): ensure_vector_database_ready(), Property, Initialize and manage the vector database with property data, Get statistics about the vector database, Ensure the vector database is ready for use, Initialize the vector database with all current properties, Refresh the property index with new or updated properties, Test the vector search functionality with sample data (+1 more)

### Community 20 - "Community 20"
Cohesion: 0.30
Nodes (8): populatePropertyViewModal(), getManager(), isDomAvailable(), notify(), populatePropertyViewModalFallback(), PropertyModalManager, setText(), viewPropertyModal()

### Community 21 - "Community 21"
Cohesion: 0.20
Nodes (8): bindPropertyEditForm(), editProperty(), hideLoadingIndicator(), initializePropertyActionDelegation(), populatePropertyShareModal(), PropertyModalManager, shareProperty(), showLoadingIndicator()

### Community 23 - "Community 23"
Cohesion: 0.11
Nodes (11): AutomationAuditLog, AutomationRule, PropertyEmbedding, Any, Tracks sync run history for the Maskan scraper integration., Stores property embeddings for vector search (pgvector-ready, JSON-compatible)., Rule definition for workflow automations., Audit records for automation executions. (+3 more)

### Community 24 - "Community 24"
Cohesion: 0.29
Nodes (7): addToFavorites(), copyFromInput(), copyPropertyUrl(), fallbackCopyText(), scheduleViewing(), setPropertyViewPreference(), showNotification()

### Community 25 - "Community 25"
Cohesion: 0.38
Nodes (6): get_all_constants(), get_english_key(), get_persian_label(), Return all constant field values for use in templates and APIs., Get the Persian label for a field type and key.          Example: get_persian_, Get the English key for a field type and Persian value.          Example: get_

### Community 26 - "Community 26"
Cohesion: 0.40
Nodes (3): BaseModel, CustomerAI, PropertyAI

### Community 27 - "Community 27"
Cohesion: 0.33
Nodes (6): getOptimalViewMode(), initializePropertyModalHistorySync(), updatePropertyModalUrl(), viewProperty(), viewPropertyAdaptive(), viewPropertyModal()

### Community 28 - "Community 28"
Cohesion: 0.12
Nodes (10): EnvironmentChangeLog, PropertyAIHistory, PropertyFavorite, PropertyImage, PublicPropertySubmission, Stores multiple images per property for gallery support, Convert to dictionary with optional sensitive value masking, Convert to dictionary with optional sensitive value masking (+2 more)

### Community 29 - "Community 29"
Cohesion: 0.50
Nodes (4): appendChatMessage(), generateCopilotPitch(), resolveCopilotCsrfToken(), sendCopilotMessage()

### Community 30 - "Community 30"
Cohesion: 0.25
Nodes (9): create_tables(), init_database(), Database initialization script with sample data seeding, Create all database tables, Initialize database with tables and sample data, Seed the database with sample data, seed_data(), Deal (+1 more)

### Community 40 - "Community 40"
Cohesion: 0.50
Nodes (3): Answer, Q: use graphify to find create best prompts for createing front end using stitch mcp for all pages needed, Source Nodes

## Knowledge Gaps
- **9 isolated node(s):** `Any`, `AnalysisDashboard`, `currentDate`, `Storage`, `API` (+4 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **16 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Property` connect `Community 17` to `Community 0`, `Community 1`, `Community 5`, `Community 6`, `Community 18`, `Community 19`, `Community 28`, `Community 30`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Why does `Customer` connect `Community 10` to `Community 0`, `Community 1`, `Community 5`, `Community 6`, `Community 28`, `Community 30`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **Why does `create_app()` connect `Community 1` to `Community 16`, `Community 0`, `Community 8`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Are the 20 inferred relationships involving `Property` (e.g. with `AgentNotification` and `background_matcher.py`) actually correct?**
  _`Property` has 20 INFERRED edges - model-reasoned connections that need verification._
- **Are the 25 inferred relationships involving `Customer` (e.g. with `AgentNotification` and `background_matcher.py`) actually correct?**
  _`Customer` has 25 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `BackgroundMatcher` (e.g. with `AgentNotification` and `Customer`) actually correct?**
  _`BackgroundMatcher` has 5 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Global default-deny session auth middleware.`, `Application factory that configures Flask, DB, routes, and security headers.`, `Patch known SQLite schema drifts for local/dev databases.      Some environments` to the rest of the system?**
  _129 weakly-connected nodes found - possible documentation gaps or missing edges._