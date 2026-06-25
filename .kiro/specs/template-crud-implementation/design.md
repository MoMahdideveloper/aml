# Design Document

## Overview

This design implements comprehensive CRUD functionality to replace placeholder JavaScript alert functions across all templates in the Real Estate CRM application. The solution will extend existing Flask blueprints with new routes, create reusable modal components, implement proper form handling, and provide consistent user feedback patterns.

The implementation follows the existing application architecture using Flask blueprints, SQLAlchemy models, WTForms for validation, and Bootstrap modals for user interactions. All operations will maintain data integrity, provide proper error handling, and ensure responsive design.

## Architecture

### Backend Architecture

The solution extends the existing Flask blueprint architecture:

```
views/
├── agents.py (extended with edit/delete routes)
├── customers.py (extended with view/edit/delete routes)  
├── deals.py (extended with view/delete/email/meeting routes)
├── tasks.py (extended with edit/delete/view routes)
└── main.py (extended with export functionality)
```

Each blueprint will be enhanced with:
- GET routes for viewing detailed records
- PUT/POST routes for editing records
- DELETE routes for removing records
- Specialized routes for business logic (email, meetings, exports)

### Frontend Architecture

The frontend will use a consistent modal-based approach:

```
templates/
├── modals/
│   ├── agent_edit_modal.html
│   ├── customer_view_modal.html
│   ├── customer_edit_modal.html
│   ├── deal_view_modal.html
│   ├── task_edit_modal.html
│   └── task_view_modal.html
├── partials/
│   ├── success_toast.html
│   └── error_toast.html
└── [existing templates updated with modal includes]
```

### Data Flow

1. **User Interaction**: User clicks action button (Edit, Delete, View, etc.)
2. **JavaScript Handler**: Captures click, extracts record ID, makes AJAX request or opens modal
3. **Backend Processing**: Flask route processes request, validates data, updates database
4. **Response Handling**: Returns JSON response or renders modal content
5. **UI Update**: JavaScript updates DOM, shows feedback, refreshes data if needed

## Components and Interfaces

### 1. Enhanced Database Service

Extend `database_service.py` with missing CRUD operations:

```python
class DatabaseService:
    # Agent operations
    def update_agent(self, agent_id: int, **kwargs) -> Optional[Agent]
    def delete_agent(self, agent_id: int) -> bool
    
    # Customer operations  
    def update_customer(self, customer_id: int, **kwargs) -> Optional[Customer]
    def delete_customer(self, customer_id: int) -> bool
    
    # Deal operations
    def delete_deal(self, deal_id: int) -> bool
    def get_deal_with_relations(self, deal_id: int) -> Optional[Deal]
    
    # Task operations
    def update_task(self, task_id: int, **kwargs) -> Optional[Task]
    def delete_task(self, task_id: int) -> bool
    
    # Export operations
    def export_recommendations_data(self, customer_id: Optional[int] = None) -> Dict
    def export_deals_report(self) -> Dict
```

### 2. Enhanced Forms

Extend `forms.py` with edit forms for each entity:

```python
class AgentEditForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=255)])
    email = EmailField('Email', validators=[DataRequired(), Email(), Length(max=255)])
    phone = StringField('Phone', validators=[DataRequired(), Length(max=20)])
    specialization = StringField('Specialization', validators=[Length(max=255)])
    bio = TextAreaField('Bio')

class CustomerEditForm(FlaskForm):
    # Similar structure for customer fields
    
class TaskEditForm(FlaskForm):
    # Similar structure for task fields
```

### 3. Modal Components

Create reusable modal templates with consistent structure:

```html
<!-- templates/modals/base_modal.html -->
<div class="modal fade" id="{{ modal_id }}" tabindex="-1">
    <div class="modal-dialog {{ modal_size|default('modal-lg') }}">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">{{ title }}</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                {{ content }}
            </div>
            <div class="modal-footer">
                {{ footer }}
            </div>
        </div>
    </div>
</div>
```

### 4. JavaScript Utilities

Create a shared JavaScript module for common operations:

```javascript
// static/js/crud-utils.js
class CRUDUtils {
    static showModal(modalId) { /* ... */ }
    static hideModal(modalId) { /* ... */ }
    static showToast(message, type) { /* ... */ }
    static confirmDelete(entityName, callback) { /* ... */ }
    static submitForm(formId, successCallback) { /* ... */ }
    static loadModalContent(url, modalId) { /* ... */ }
}
```

## Data Models

The implementation will use existing SQLAlchemy models without modifications:
- `Agent` - for agent CRUD operations
- `Customer` - for customer CRUD operations  
- `Deal` - for deal CRUD operations
- `Task` - for task CRUD operations
- `Property` - for property viewing in recommendations export

### Validation Rules

Each entity will maintain existing validation rules plus:
- **Agents**: Unique email validation, phone format validation
- **Customers**: Budget range validation (min <= max), email uniqueness
- **Tasks**: Due date validation (not in past), priority enum validation
- **Deals**: Status transition validation, offer amount positive validation

## Error Handling

### Backend Error Handling

```python
@bp.errorhandler(404)
def handle_not_found(e):
    if request.is_json:
        return jsonify({'error': 'Resource not found'}), 404
    flash('Resource not found', 'error')
    return redirect(request.referrer or url_for('main.dashboard'))

@bp.errorhandler(500)
def handle_server_error(e):
    db.session.rollback()
    if request.is_json:
        return jsonify({'error': 'Internal server error'}), 500
    flash('An error occurred. Please try again.', 'error')
    return redirect(request.referrer or url_for('main.dashboard'))
```

### Frontend Error Handling

```javascript
function handleAjaxError(xhr, status, error) {
    let message = 'An error occurred';
    if (xhr.responseJSON && xhr.responseJSON.error) {
        message = xhr.responseJSON.error;
    }
    CRUDUtils.showToast(message, 'error');
}
```

### Validation Error Display

Form validation errors will be displayed using Bootstrap's validation classes:
- `.is-invalid` for invalid fields
- `.invalid-feedback` for error messages
- Server-side validation errors passed to templates via flash messages

## Testing Strategy

### Unit Tests

Create comprehensive unit tests for each new route and service method:

```python
# tests/test_crud_operations.py
class TestAgentCRUD:
    def test_update_agent_success(self)
    def test_update_agent_validation_error(self)
    def test_delete_agent_success(self)
    def test_delete_agent_not_found(self)

class TestCustomerCRUD:
    # Similar test structure
    
class TestDealCRUD:
    # Similar test structure
    
class TestTaskCRUD:
    # Similar test structure
```

### Integration Tests

Test complete workflows from frontend to database:

```python
# tests/test_crud_integration.py
class TestCRUDIntegration:
    def test_agent_edit_workflow(self)
    def test_customer_delete_workflow(self)
    def test_deal_view_workflow(self)
    def test_task_update_workflow(self)
    def test_export_functionality(self)
```

### Frontend Tests

JavaScript unit tests for utility functions and modal interactions:

```javascript
// tests/js/test_crud_utils.js
describe('CRUDUtils', function() {
    describe('showModal', function() {
        it('should display modal with correct content');
    });
    
    describe('confirmDelete', function() {
        it('should show confirmation dialog');
        it('should execute callback on confirmation');
    });
});
```

### Manual Testing Checklist

- [ ] All placeholder alerts replaced with functional implementations
- [ ] Modal forms display correctly on all screen sizes
- [ ] Form validation works for all required fields
- [ ] Success/error messages display appropriately
- [ ] Delete confirmations prevent accidental deletions
- [ ] Export functionality generates correct file formats
- [ ] Email and meeting scheduling interfaces work properly
- [ ] All CRUD operations maintain data integrity
- [ ] Navigation and URL routing work correctly
- [ ] Accessibility features function properly (keyboard navigation, screen readers)

## Implementation Phases

### Phase 1: Core Infrastructure
- Extend database service with missing CRUD methods
- Create base modal templates and JavaScript utilities
- Implement error handling patterns

### Phase 2: Agent Management
- Add agent edit/delete routes and modals
- Update agent template with functional buttons
- Add comprehensive validation and error handling

### Phase 3: Customer Management  
- Add customer view/edit/delete routes and modals
- Update customer template with functional buttons
- Implement customer-specific business logic

### Phase 4: Deal Management
- Add deal view/delete routes and modals
- Implement meeting scheduling interface
- Add email composition functionality
- Create deal export functionality

### Phase 5: Task Management
- Add task edit/delete/view routes and modals
- Update task template with functional buttons
- Implement task-specific validation rules

### Phase 6: Export and Reporting
- Implement recommendations export (PDF/Excel)
- Add deal reporting functionality
- Create property viewing scheduling interface

### Phase 7: Testing and Polish
- Write comprehensive test suite
- Perform cross-browser testing
- Optimize performance and user experience
- Add accessibility improvements