# Design Document

## Overview

The dual view options feature will enhance the existing CRM interface by providing users with flexible viewing modes for entity details. The design leverages the existing modal system while adding new tab functionality, ensuring consistent user experience across all entity types (properties, customers, agents, deals, tasks).

## Architecture

### Component Structure
```
Dual View System
├── View Option Selector Component
├── Modal View Handler (existing, enhanced)
├── New Tab View Handler (new)
├── User Preference Manager (new)
└── Unified Data Loading Service (enhanced)
```

### Integration Points
- **Existing Modal System**: Enhance current modal templates and JavaScript handlers
- **Route System**: Extend existing detail routes to support both modal and full-page contexts
- **User Preferences**: Local storage for preference persistence
- **JavaScript Framework**: Extend existing CRUD utilities

## Components and Interfaces

### 1. View Option Selector Component

**Purpose**: Provides UI controls for selecting viewing mode

**Interface**:
```html
<div class="view-options-selector" data-entity-type="property" data-entity-id="123">
    <div class="btn-group" role="group" aria-label="View options">
        <button type="button" class="btn btn-outline-primary btn-sm view-modal" 
                data-bs-toggle="tooltip" title="Quick view in modal">
            <i class="fas fa-eye"></i>
            <span class="d-none d-md-inline ms-1">Quick View</span>
        </button>
        <button type="button" class="btn btn-outline-primary btn-sm view-tab"
                data-bs-toggle="tooltip" title="Open in new tab">
            <i class="fas fa-external-link-alt"></i>
            <span class="d-none d-md-inline ms-1">Full View</span>
        </button>
    </div>
</div>
```

**Responsive Behavior**:
- Desktop: Show both icon and text
- Mobile: Icon-only with tooltips
- Keyboard navigation support

### 2. Enhanced Modal View Handler

**Purpose**: Extend existing modal system with preference awareness

**Key Enhancements**:
- Preference-based default behavior
- Enhanced loading states
- Improved accessibility
- Better error handling

**JavaScript Interface**:
```javascript
class DualViewHandler {
    constructor(entityType, entityId) {
        this.entityType = entityType;
        this.entityId = entityId;
        this.userPreference = this.getUserPreference();
    }
    
    handleViewAction(forceMode = null) {
        const mode = forceMode || this.userPreference;
        if (mode === 'tab') {
            this.openInNewTab();
        } else {
            this.openInModal();
        }
    }
    
    openInModal() { /* Enhanced modal logic */ }
    openInNewTab() { /* New tab logic */ }
    getUserPreference() { /* Preference retrieval */ }
    setUserPreference(mode) { /* Preference storage */ }
}
```

### 3. New Tab View Handler

**Purpose**: Manage new tab opening and data consistency

**Features**:
- URL generation for entity detail pages
- Context preservation
- Data synchronization
- Browser compatibility

**Implementation**:
```javascript
openInNewTab() {
    const url = this.generateDetailUrl();
    const newTab = window.open(url, '_blank', 'noopener,noreferrer');
    
    // Handle popup blockers
    if (!newTab) {
        this.showPopupBlockedNotification();
        return;
    }
    
    // Track tab opening for analytics
    this.trackViewAction('new_tab');
}
```

### 4. User Preference Manager

**Purpose**: Handle preference storage and retrieval

**Storage Strategy**:
- Local Storage for persistence
- Session fallback for privacy mode
- Per-entity-type preferences
- Global default preference

**Data Structure**:
```javascript
{
    "viewPreferences": {
        "global": "modal",
        "property": "tab",
        "customer": "modal",
        "agent": "modal",
        "deal": "tab",
        "task": "modal"
    },
    "lastUpdated": "2025-01-09T10:30:00Z"
}
```

## Data Models

### View Preference Model
```javascript
interface ViewPreference {
    entityType: 'global' | 'property' | 'customer' | 'agent' | 'deal' | 'task';
    viewMode: 'modal' | 'tab';
    lastUpdated: Date;
}
```

### View Action Event
```javascript
interface ViewActionEvent {
    entityType: string;
    entityId: number;
    viewMode: 'modal' | 'tab';
    timestamp: Date;
    userAgent: string;
}
```

## Error Handling

### Error Scenarios and Responses

1. **Popup Blocked**
   - Detection: Check if `window.open()` returns null
   - Response: Show notification with manual link option
   - Fallback: Offer modal view as alternative

2. **Network Failure**
   - Detection: AJAX request timeout or error
   - Response: Show retry option with exponential backoff
   - Fallback: Cache last known data if available

3. **Invalid Entity ID**
   - Detection: 404 response from server
   - Response: Show "Entity not found" message
   - Fallback: Redirect to entity list page

4. **Permission Denied**
   - Detection: 403 response from server
   - Response: Show access denied message
   - Fallback: Hide view options for unauthorized entities

### Error Recovery Patterns
```javascript
async function handleViewError(error, entityType, entityId) {
    switch (error.type) {
        case 'POPUP_BLOCKED':
            showNotification('Popup blocked. Click here to open in new tab.', 'warning', {
                action: () => window.location.href = generateDetailUrl(entityType, entityId)
            });
            break;
        case 'NETWORK_ERROR':
            showRetryOption(() => this.handleViewAction());
            break;
        case 'NOT_FOUND':
            showNotification('Entity not found.', 'error');
            redirectToEntityList(entityType);
            break;
    }
}
```

## Testing Strategy

### Unit Tests
- View option selector component rendering
- Preference storage and retrieval
- URL generation for different entity types
- Error handling scenarios

### Integration Tests
- Modal to tab transition
- Tab to modal transition
- Preference persistence across sessions
- Cross-browser compatibility

### User Experience Tests
- Keyboard navigation
- Screen reader compatibility
- Mobile responsiveness
- Performance with large datasets

### Test Scenarios
```javascript
describe('Dual View Options', () => {
    test('should open modal by default for new users', () => {
        // Test default behavior
    });
    
    test('should remember user preference', () => {
        // Test preference persistence
    });
    
    test('should handle popup blockers gracefully', () => {
        // Test popup blocker scenario
    });
    
    test('should maintain data consistency between views', () => {
        // Test data synchronization
    });
});
```

## Implementation Phases

### Phase 1: Core Infrastructure
- Implement view option selector component
- Create user preference manager
- Enhance existing modal handlers
- Add basic new tab functionality

### Phase 2: Enhanced Features
- Add keyboard shortcuts (Ctrl+click)
- Implement preference UI in settings
- Add analytics tracking
- Enhance error handling

### Phase 3: Optimization
- Performance optimization for large datasets
- Advanced caching strategies
- Mobile-specific enhancements
- Accessibility improvements

## Technical Considerations

### Browser Compatibility
- Modern browsers: Full feature support
- Legacy browsers: Graceful degradation to modal-only
- Mobile browsers: Touch-optimized interface

### Performance Impact
- Minimal JavaScript overhead (~2KB gzipped)
- Local storage usage: <1KB per user
- No additional server requests for preference management

### Security Considerations
- `noopener,noreferrer` for new tab security
- Input validation for entity IDs
- CSRF protection for preference updates
- XSS prevention in dynamic content

### Accessibility Features
- ARIA labels for view options
- Keyboard navigation support
- Screen reader announcements
- High contrast mode compatibility

---
*This design leverages the existing Flask CRM architecture while adding minimal complexity and maximum user value.*