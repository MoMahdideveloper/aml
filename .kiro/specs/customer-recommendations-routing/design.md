# Design Document

## Overview

This design addresses the Flask routing error in the Real Estate CRM where the recommendations template references a non-existent `get_customer_recommendations` endpoint. The solution involves creating a new route handler that can display both general recommendations (all customers) and customer-specific recommendations with AI-powered property matching.

## Architecture

### Current State
- `/recommendations` route exists in `views/main.py` but only shows customer selection
- Template references `get_customer_recommendations` endpoint that doesn't exist
- `gemini_service.py` has recommendation logic but no route to trigger it
- `database_service.py` provides data access methods

### Target State
- `/recommendations` - General recommendations page (existing)
- `/recommendations/<int:customer_id>` - Customer-specific recommendations (new)
- Enhanced route handler with AI recommendation generation
- Proper error handling and fallback mechanisms
- Background task system for proactive property matching and notifications

## Components and Interfaces

### 1. Route Handler Enhancement

**File:** `views/main.py`

**New Route:**
```python
@bp.route("/recommendations/<int:customer_id>")
def get_customer_recommendations(customer_id: int):
    # Validate customer exists (404 if not found)
    # Get customer preferences (budget, bedrooms, type, location)
    # Get available properties from database
    # Filter properties based on customer criteria
    # Calculate match scores for each property
    # Generate AI recommendations with detailed analysis
    # Sort recommendations by match score (descending)
    # Handle AI service failures with fallback logic
    # Render template with customer-specific data and error handling
```

**Enhanced Existing Route:**
```python
@bp.route("/recommendations")
def recommendations():
    # Keep existing functionality
    # Add support for selected_customer parameter
```

### 2. Recommendation Engine Integration

**Service Integration:**
- Use existing `gemini_service.get_property_recommendations()`
- Leverage `database_service` for data retrieval
- Implement fallback logic when AI service unavailable

**Data Flow:**
1. Route receives customer_id
2. Fetch customer from database and validate existence
3. Fetch available properties from database
4. Filter properties based on customer preferences (budget, bedrooms, type, location)
5. Calculate match scores for filtered properties
6. Generate AI recommendations via Gemini service with detailed analysis
7. Sort recommendations by match score (descending order)
8. Format results for template rendering with proper error handling

### 3. Template Enhancement

**File:** `templates/recommendations.html`

**Current Issues:**
- References non-existent `get_customer_recommendations` endpoint
- Template expects `selected_customer` and `recommendations` variables

**Solution:**
- Route will provide these variables when customer_id is specified
- Template logic already handles both states (customer selection vs. recommendations display)
- Customer selection area will highlight the selected customer when viewing recommendations
- Template will display customer preferences and match scores for each recommendation

### 4. Background Matching System

**Architecture:**
- Background task scheduler (using APScheduler or Celery)
- Property change event handlers
- Customer preference update triggers
- Notification/task creation system

**Components:**
```python
class BackgroundMatcher:
    def run_property_matching(self, property_id: int = None, customer_id: int = None)
    def handle_new_property(self, property_id: int)
    def handle_customer_update(self, customer_id: int)
    def create_agent_notifications(self, matches: List[PropertyMatch])
```

**Trigger Events:**
- New property added to database
- Customer preferences updated
- Scheduled periodic matching (daily/weekly)

**Notification System:**
- Create tasks/notifications for agents when match score > 70
- Store notifications in database for agent dashboard
- Optional email notifications for high-priority matches

## Data Models

### Recommendation Data Structure

```python
class PropertyRecommendation:
    property: Property          # Property object from database
    analysis: str              # AI-generated analysis text
    match_score: int           # Score 0-100 based on customer preferences
```

### Customer Preference Matching

**Customer Preference Fields:**
- `budget_min`: Minimum budget for property search
- `budget_max`: Maximum budget for property search  
- `preferred_bedrooms`: Desired number of bedrooms
- `preferred_type`: Property type preference (house, apartment, condo, etc.)
- `location_preference`: Preferred location or area

**Scoring Algorithm (0-100 scale):**
- Budget compatibility (40 points max)
  - Perfect match (within budget): 40 points
  - Slightly over budget (up to 10%): 30 points
  - Moderately over budget (10-20%): 20 points
  - Significantly over budget (>20%): 0 points
- Bedroom count match (20 points max)
  - Exact match: 20 points
  - ±1 bedroom: 15 points
  - ±2 bedrooms: 10 points
  - >2 bedrooms difference: 0 points
- Property type match (20 points max)
  - Exact match: 20 points
  - No match: 0 points
- Location preference match (20 points max)
  - Exact location match: 20 points
  - Similar area/neighborhood: 15 points
  - Same city/region: 10 points
  - Different location: 0 points

**AI Enhancement:**
- Gemini service provides detailed analysis
- Vector search for semantic matching (if available)
- Fallback to rule-based scoring when AI unavailable

## Background Matching System

### Architecture Overview

The background matching system proactively identifies property-customer matches when new properties are added or customer preferences change, creating notifications for agents to follow up on high-potential matches.

### Data Models

```python
class PropertyMatch:
    customer_id: int
    property_id: int
    match_score: int
    created_at: datetime
    agent_id: int
    notification_sent: bool

class AgentNotification:
    id: int
    agent_id: int
    customer_id: int
    property_id: int
    match_score: int
    message: str
    read: bool
    created_at: datetime
```

### Background Task Implementation

**Task Scheduler:**
- Use APScheduler for lightweight background tasks
- Schedule periodic full matching runs (daily)
- Immediate matching for new properties/preference updates

**Matching Logic:**
1. Identify trigger event (new property or customer update)
2. Run matching algorithm using same scoring system as interactive recommendations
3. Filter matches with score > 70 (configurable threshold)
4. Create notifications for relevant agents
5. Log matching results for audit

**Event Triggers:**
- Database model signals (post_save for Property and Customer models)
- Manual trigger via admin interface
- Scheduled periodic runs

### Notification System

**Agent Dashboard Integration:**
- Display new property matches in agent dashboard
- Show match score and brief property summary
- Link to full recommendation page for customer
- Mark notifications as read/unread

**Optional Email Notifications:**
- Send email alerts for high-score matches (>85)
- Configurable email frequency (immediate, daily digest)
- Include property details and customer preferences

### Performance Considerations

**Optimization Strategies:**
- Batch processing for multiple property additions
- Incremental matching (only new/changed data)
- Configurable matching frequency
- Database indexing on customer preferences and property attributes

**Scalability:**
- Queue-based processing for large datasets
- Async task execution to avoid blocking main application
- Monitoring and alerting for background task failures

## Error Handling

### 1. Customer Not Found (404)
```python
customer = database_service.get_customer(customer_id)
if not customer:
    abort(404, description="Customer not found")
```

### 2. AI Service Unavailable
- Use `gemini_service._create_fallback_recommendations()`
- Display warning message to user about limited AI analysis
- Provide basic preference-based matching with calculated scores
- Still show properties sorted by match score
- Include basic analysis based on preference matching logic

### 3. No Properties Available
- Display helpful message explaining why no recommendations are available
- Suggest adjusting search criteria (budget range, property type, location)
- Provide link to properties page for adding new properties
- Show customer's current preferences for reference

### 4. Database Errors
- Log error details
- Display user-friendly error message
- Graceful degradation

## Testing Strategy

### Unit Tests
- Test route handler with valid customer_id
- Test route handler with invalid customer_id
- Test recommendation generation with mock data
- Test fallback behavior when AI unavailable

### Integration Tests
- Test full recommendation flow end-to-end
- Test template rendering with recommendations
- Test error handling scenarios

### Manual Testing
- Verify URL routing works correctly
- Test recommendation quality with real data
- Verify error messages display properly
- Test performance with large property datasets

## Implementation Considerations

### Performance
- Limit property dataset size for AI processing
- Cache recommendations for repeated requests
- Implement timeout handling for AI service calls

### Security
- Validate customer_id parameter
- Ensure proper error handling doesn't expose sensitive data
- Use Flask's built-in parameter validation

### Scalability
- Design for future enhancement (filters, sorting)
- Consider pagination for large recommendation sets
- Modular design for easy testing and maintenance

### Backward Compatibility
- Maintain existing `/recommendations` route behavior
- Ensure existing template logic continues to work
- No breaking changes to current functionality

## URL Structure

```
GET /recommendations                    # Show all customers for selection
GET /recommendations/<int:customer_id>  # Show recommendations for specific customer
```

## Template Variables

**For `/recommendations`:**
- `customers`: List of all customers
- `selected_customer`: None
- `recommendations`: None

**For `/recommendations/<customer_id>`:**
- `customers`: List of all customers (for customer selection highlighting)
- `selected_customer`: Customer object with preferences
- `recommendations`: List of PropertyRecommendation objects sorted by match score
- `agents`: List of agents (for deal creation modal)
- `ai_service_available`: Boolean flag indicating if AI analysis was used
- `error_message`: Optional error message for display to user

## Dependencies

### Required Services
- `database_service`: Customer and property data access
- `gemini_service`: AI-powered recommendation generation

### Optional Services  
- `vector_service`: Enhanced semantic matching (graceful fallback if unavailable)

### Flask Components
- Blueprint routing
- Template rendering
- Error handling (abort, 404)
- URL parameter validation

### Background Task Components
- APScheduler or Celery for task scheduling
- Database event triggers or model signals
- Notification/task management system
- Logging and monitoring for background processes