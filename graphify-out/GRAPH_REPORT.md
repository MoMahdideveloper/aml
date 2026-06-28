# Graph Report - .  (2026-06-28)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 902 nodes · 1460 edges · 113 communities (40 shown, 73 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 182 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `84438eac`
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
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 74|Community 74]]
- [[_COMMUNITY_Community 75|Community 75]]
- [[_COMMUNITY_Community 76|Community 76]]
- [[_COMMUNITY_Community 77|Community 77]]
- [[_COMMUNITY_Community 78|Community 78]]
- [[_COMMUNITY_Community 79|Community 79]]
- [[_COMMUNITY_Community 80|Community 80]]
- [[_COMMUNITY_Community 81|Community 81]]
- [[_COMMUNITY_Community 82|Community 82]]
- [[_COMMUNITY_Community 83|Community 83]]
- [[_COMMUNITY_Community 84|Community 84]]
- [[_COMMUNITY_Community 85|Community 85]]
- [[_COMMUNITY_Community 86|Community 86]]
- [[_COMMUNITY_Community 87|Community 87]]
- [[_COMMUNITY_Community 88|Community 88]]
- [[_COMMUNITY_Community 89|Community 89]]
- [[_COMMUNITY_Community 90|Community 90]]
- [[_COMMUNITY_Community 91|Community 91]]
- [[_COMMUNITY_Community 92|Community 92]]
- [[_COMMUNITY_Community 93|Community 93]]
- [[_COMMUNITY_Community 94|Community 94]]
- [[_COMMUNITY_Community 95|Community 95]]
- [[_COMMUNITY_Community 96|Community 96]]
- [[_COMMUNITY_Community 97|Community 97]]
- [[_COMMUNITY_Community 98|Community 98]]
- [[_COMMUNITY_Community 99|Community 99]]
- [[_COMMUNITY_Community 100|Community 100]]
- [[_COMMUNITY_Community 101|Community 101]]
- [[_COMMUNITY_Community 102|Community 102]]

## God Nodes (most connected - your core abstractions)
1. `Property` - 50 edges
2. `CRUDUtils` - 43 edges
3. `Customer` - 34 edges
4. `EventHandlers` - 31 edges
5. `DatabaseService` - 30 edges
6. `DataManager` - 27 edges
7. `BackgroundMatcher` - 24 edges
8. `AccessibilityEnhancements` - 24 edges
9. `PropertyEditModal` - 23 edges
10. `Property` - 22 edges

## Surprising Connections (you probably didn't know these)
- `Property` --uses--> `Property`  [INFERRED]
  vector_init.py → sqlalchemy_models.py
- `BackgroundMatcher` --uses--> `AgentNotification`  [INFERRED]
  background_matcher.py → sqlalchemy_models.py
- `BackgroundMatcher` --uses--> `Customer`  [INFERRED]
  background_matcher.py → sqlalchemy_models.py
- `BackgroundMatcher` --uses--> `MatchingJobRun`  [INFERRED]
  background_matcher.py → sqlalchemy_models.py
- `BackgroundMatcher` --uses--> `Property`  [INFERRED]
  background_matcher.py → sqlalchemy_models.py

## Import Cycles
- 1-file cycle: `migrate_environment_vars.py -> migrate_environment_vars.py`
- 1-file cycle: `sqlalchemy_models.py -> sqlalchemy_models.py`
- 1-file cycle: `data_manager.py -> data_manager.py`
- 1-file cycle: `models.py -> models.py`
- 1-file cycle: `database_service.py -> database_service.py`
- 1-file cycle: `environment_loader.py -> environment_loader.py`

## Communities (113 total, 73 thin omitted)

### Community 58 - "Community 58"
Cohesion: 0.07
Nodes (24): DatabaseService, Agent, Customer, datetime, Deal, Property, Task, Database service to replace the in-memory DataManager with SQLAlchemy operations (+16 more)

### Community 59 - "Community 59"
Cohesion: 0.06
Nodes (37): BusinessLogicError, create_error_response(), flash_and_redirect(), handle_database_error(), handle_form_errors(), log_error(), Comprehensive error handling for Flask application Provides consistent error re, Register global error handlers for the Flask application (+29 more)

### Community 61 - "Community 61"
Cohesion: 0.07
Nodes (34): get_property_with_fallback_data(), get_property_with_related_data(), handle_database_connection_error(), _handle_property_error(), handle_property_errors(), log_property_operation(), PropertyError, PropertyNotFoundError (+26 more)

### Community 62 - "Community 62"
Cohesion: 0.06
Nodes (24): database_savepoint(), database_transaction(), DatabaseTransactionManager, Any, Database Transaction Manager Provides transaction management with rollback capa, Rollback to a specific savepoint                  Args:             name: Sav, Release a savepoint                  Args:             name: Savepoint name, Context manager for savepoint operations                  Args:             n (+16 more)

### Community 63 - "Community 63"
Cohesion: 0.10
Nodes (19): BaseModel, GeminiService, Any, Customer, Property, Parse the AI response and create structured recommendations, Create basic recommendations when AI is unavailable, Generate a succinct market analysis.         Returns a dict with keys: analysis (+11 more)

### Community 64 - "Community 64"
Cohesion: 0.07
Nodes (20): Builder, ContactReveal, CustomerGroup, MatchingJobRun, PropertyActivityLog, PropertyAIHistory, PropertyFavorite, PropertyImage (+12 more)

### Community 65 - "Community 65"
Cohesion: 0.12
Nodes (8): DataManager, Agent, Customer, Deal, Property, Task, Initialize the system with sample data, Deal

### Community 66 - "Community 66"
Cohesion: 0.12
Nodes (17): Any, Customer, Property, Generate TF-IDF embedding for text, Vector-based recommendation service using Chroma DB and scikit-learn embeddings, Generate embeddings for multiple texts efficiently, Index all properties in the vector database, Perform semantic search for properties matching customer preferences (+9 more)

### Community 67 - "Community 67"
Cohesion: 0.07
Nodes (17): AIMetadata, AutomationAuditLog, AutomationRule, ModelPerformanceMetric, PropertyEmbedding, Any, Queued outbound SMS message for asynchronous provider delivery., Tracks AI model performance metrics for monitoring and optimization. (+9 more)

### Community 68 - "Community 68"
Cohesion: 0.10
Nodes (16): Animate, API, convertToCSV(), currentDate, debounce(), exportToCSV(), initializeAIAutofill(), initializeApp() (+8 more)

### Community 72 - "Community 72"
Cohesion: 0.18
Nodes (20): announceToScreenReader(), escapeHtml(), formatCurrency(), formatListingType(), formatPropertyCategory(), formatPropertyCondition(), formatPropertyType(), formatTomanCurrency() (+12 more)

### Community 74 - "Community 74"
Cohesion: 0.11
Nodes (11): MatchingJobRun, Customer, Property, Calculate property age, Calculate price per square foot, Calculate rahn (deposit) per square meter for rentals, Calculate ejare (monthly rent) per square meter for rentals, Calculate sale price per square meter for sales (+3 more)

### Community 75 - "Community 75"
Cohesion: 0.15
Nodes (13): EnvironmentMigrator, any, Flask, Detect sensitive variables based on key patterns and values, Filter environment variables to include only migration candidates, Generate description for environment variable based on key and value, Migrate environment variables to database, Handles migration of system environment variables to database storage (+5 more)

### Community 76 - "Community 76"
Cohesion: 0.19
Nodes (6): EnvironmentVariable, EventHandlers, Property, Queue vector sync tasks to run after DB commit.         Running Celery `.delay(, Database event handlers that enqueue lightweight rematch requests.     Heavy ma, Queue environment variable change tasks to run after DB commit.         Running

### Community 77 - "Community 77"
Cohesion: 0.14
Nodes (12): EnvironmentLoader, load_environment_at_startup(), Flask, Environment Loader for loading stored environment variables at application start, Get dictionary of variables loaded from database, Check if fallback to system environment was used, Get summary of environment loading status, Loads environment variables from database at application startup (+4 more)

### Community 78 - "Community 78"
Cohesion: 0.25
Nodes (4): BackgroundMatcher, Customer, Property, Background matching engine for property-customer recommendations.

### Community 79 - "Community 79"
Cohesion: 0.19
Nodes (5): create_app(), Flask application factory with device detection implementation., Application factory function., migrate_embeddings(), test_recommendations()

### Community 81 - "Community 81"
Cohesion: 0.13
Nodes (7): Property, Calculate property age, Get property features as a list, Calculate price per square foot, Calculate rahn (deposit) per square meter for rentals, Calculate ejare (monthly rent) per square meter for rentals, Calculate sale price per square meter for sales

### Community 82 - "Community 82"
Cohesion: 0.23
Nodes (5): datetime, Agent, Customer, datetime, Task

### Community 84 - "Community 84"
Cohesion: 0.31
Nodes (7): getManager(), isDomAvailable(), notify(), populatePropertyViewModalFallback(), PropertyModalManager, setText(), viewPropertyModal()

### Community 85 - "Community 85"
Cohesion: 0.15
Nodes (9): ensure_vector_database_ready(), Property, Initialize and manage the vector database with property data, Get statistics about the vector database, Ensure the vector database is ready for use, Initialize the vector database with all current properties, Refresh the property index with new or updated properties, Test the vector search functionality with sample data (+1 more)

### Community 86 - "Community 86"
Cohesion: 0.21
Nodes (6): Any, Customer, EnvironmentChangeLog, EnvironmentVariable, Convert to dictionary with optional sensitive value masking, Convert to dictionary with optional sensitive value masking

### Community 88 - "Community 88"
Cohesion: 0.27
Nodes (6): init_db(), Initialize database with Flask app, DebugTest, AnalysisReport, AnalysisTemplate, TestAnalyticsAPI

### Community 89 - "Community 89"
Cohesion: 0.22
Nodes (6): Manual trigger now enqueues rematch requests for worker processing., Session, Queue of rematch requests produced by model change events., RematchQueue, Test VoiceHistory model directly with SQLAlchemy, test_voice_history_model_direct()

### Community 90 - "Community 90"
Cohesion: 0.22
Nodes (4): Test the property parsing endpoint, Test the customer parsing endpoint, Test the endpoint with no text, TestAIAutofill

### Community 91 - "Community 91"
Cohesion: 0.36
Nodes (5): AgentNotification, Create agent notifications for saved matches.         Fixed: Added try/except a, PropertyMatch, PropertyMatch, Stores property-customer matches generated by the background matching system

### Community 93 - "Community 93"
Cohesion: 0.38
Nodes (6): get_all_constants(), get_english_key(), get_persian_label(), Return all constant field values for use in templates and APIs., Get the Persian label for a field type and key.          Example: get_persian_, Get the English key for a field type and Persian value.          Example: get_

### Community 94 - "Community 94"
Cohesion: 0.33
Nodes (3): AgentNotification, Stores notifications for agents about property matches and other events, Mark notification as read with timestamp

### Community 95 - "Community 95"
Cohesion: 0.33
Nodes (5): _generate_file_code(), Get property features as a list, Generate a unique 6-digit file code like maskan-file.ir, Auto-generate file_code for new properties if not set, _set_file_code()

### Community 97 - "Community 97"
Cohesion: 0.50
Nodes (3): Answer, Q: use graphify to find create best prompts for createing front end using stitch mcp for all pages needed, Source Nodes

## Knowledge Gaps
- **68 isolated node(s):** `Any`, `Meta`, `SuggestionItem`, `AnalysisDashboard`, `currentDate` (+63 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **73 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Property` connect `Community 74` to `Community 64`, `Community 76`, `Community 78`, `Community 79`, `Community 85`, `Community 86`, `Community 89`, `Community 58`, `Community 91`, `Community 61`, `Community 95`, `Community 63`?**
  _High betweenness centrality (0.146) - this node is a cross-community bridge._
- **Why does `PropertyError` connect `Community 61` to `Community 74`, `Community 59`?**
  _High betweenness centrality (0.057) - this node is a cross-community bridge._
- **Why does `Property` connect `Community 81` to `Community 65`, `Community 82`, `Community 66`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Are the 29 inferred relationships involving `Property` (e.g. with `AgentNotification` and `BackgroundMatcher`) actually correct?**
  _`Property` has 29 INFERRED edges - model-reasoned connections that need verification._
- **Are the 23 inferred relationships involving `Customer` (e.g. with `AgentNotification` and `BackgroundMatcher`) actually correct?**
  _`Customer` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `EventHandlers` (e.g. with `AgentNotification` and `Customer`) actually correct?**
  _`EventHandlers` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `DatabaseService` (e.g. with `Agent` and `Customer`) actually correct?**
  _`DatabaseService` has 5 INFERRED edges - model-reasoned connections that need verification._