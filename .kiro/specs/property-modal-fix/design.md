# Design Document

## Overview

The property view modal issue is caused by a missing JavaScript function `populatePropertyViewModal` that should populate the modal DOM elements with fetched property data. The current `viewProperty` function successfully fetches data from the backend but fails to populate the modal because this critical function is missing.

## Architecture

The fix involves implementing the missing `populatePropertyViewModal` function in the main.js file. This function will:

1. Accept property data as a parameter
2. Map property data fields to corresponding DOM elements using data attributes
3. Handle different data types (text, numbers, dates, arrays)
4. Provide fallback values for missing data
5. Update modal action buttons with correct property IDs

## Components and Interfaces

### JavaScript Function: `populatePropertyViewModal(propertyData)`

**Purpose:** Populate the property view modal with fetched property data

**Parameters:**
- `propertyData` (Object): Property data object from the backend API

**Key Responsibilities:**
1. Map data fields to DOM elements using `data-field` attributes
2. Handle pricing display based on listing type (sale vs rental)
3. Format numbers with proper comma separators
4. Display property features as badges
5. Update action button onclick handlers with correct property ID
6. Handle missing/null data with "N/A" fallbacks

### DOM Element Mapping Strategy

The modal template uses `data-field` attributes to identify elements that need population:
- `data-field="title"` → property title
- `data-field="address"` → property address  
- `data-field="price"` → pricing information
- `data-field="bedrooms"` → bedroom count
- etc.

### Data Formatting Requirements

1. **Numbers:** Format with comma separators (e.g., "1,500")
2. **Currency:** Format with appropriate currency symbols and commas
3. **Dates:** Format as readable strings (YYYY-MM-DD HH:MM:SS)
4. **Arrays:** Convert to comma-separated strings or badge elements
5. **Null/Undefined:** Display as "N/A"

## Data Models

### Property Data Structure (from backend)
```javascript
{
  id: number,
  title: string,
  address: string,
  price: number,
  property_type: string,
  bedrooms: number,
  bathrooms: number,
  square_feet: number,
  description: string,
  year_built: number,
  parking_spaces: number,
  floors: number,
  units: number,
  property_condition: string,
  neighborhood: string,
  property_category: string,
  listing_type: string, // 'sale' or 'rental'
  rahn: number, // for rental properties
  ejare: number, // for rental properties
  property_features: string, // comma-separated
  created_at: string,
  agent_name: string,
  agent_email: string,
  agent_phone: string,
  total_deals: number,
  active_deals: number
}
```

## Error Handling

1. **Missing Property Data:** If propertyData is null/undefined, log error and show notification
2. **Missing DOM Elements:** If modal elements are not found, log warnings but continue
3. **Data Type Errors:** Handle non-numeric values gracefully with fallbacks
4. **Feature Parsing:** Handle malformed property_features strings safely

## Testing Strategy

### Unit Tests
1. Test `populatePropertyViewModal` with complete property data
2. Test with missing/null property data fields
3. Test with different listing types (sale vs rental)
4. Test number formatting functions
5. Test DOM element updates

### Integration Tests
1. Test complete `viewProperty` flow from button click to modal display
2. Test modal action buttons after population
3. Test error scenarios (network failures, invalid property IDs)

### Manual Testing
1. Click "View Details" on various properties
2. Verify all data fields are populated correctly
3. Test with properties that have missing data
4. Test Edit and Share buttons work with correct property IDs

## Implementation Notes

### Existing Code Integration
- The function will be added to the existing main.js file
- It will integrate with the current `viewProperty` function
- No changes needed to backend or modal template
- Maintains compatibility with existing CRUDUtils fallback system

### Performance Considerations
- Function should be lightweight and fast
- Avoid unnecessary DOM queries by caching elements
- Use efficient string formatting methods
- Minimize DOM manipulations

### Browser Compatibility
- Use standard JavaScript features compatible with modern browsers
- Avoid ES6+ features that might not be supported in older browsers
- Test with Bootstrap 5 modal system