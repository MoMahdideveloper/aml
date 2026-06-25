# Real Estate CRM API Endpoints

This document describes the new CRUD API endpoints implemented for the Real Estate CRM application.

## Agent Management

### GET /agents/{id}/edit
- **Description**: Get agent edit form data
- **Response**: JSON with agent data for editing
- **Headers**: X-Requested-With: XMLHttpRequest

### PUT/POST /agents/{id}
- **Description**: Update agent information
- **Body**: Form data with agent fields (name, email, phone, specialization, bio)
- **Response**: JSON with success message and updated agent data

### DELETE /agents/{id}
- **Description**: Delete an agent
- **Response**: JSON with success/error message

## Customer Management

### GET /customers/{id}
- **Description**: Get customer details for viewing
- **Response**: JSON with comprehensive customer data including deals

### GET /customers/{id}/edit
- **Description**: Get customer edit form data
- **Response**: HTML modal content or JSON with customer data

### PUT/POST /customers/{id}
- **Description**: Update customer information
- **Body**: Form data with customer fields
- **Response**: JSON with success message and updated customer data

### DELETE /customers/{id}
- **Description**: Delete a customer (with validation for active deals)
- **Response**: JSON with success/error message

## Deal Management

### GET /deals/{id}
- **Description**: Get deal details with property and customer info
- **Response**: JSON with comprehensive deal data

### DELETE /deals/{id}
- **Description**: Delete a deal
- **Response**: JSON with success/error message

### GET /deals/{id}/schedule-meeting
- **Description**: Get meeting scheduling interface
- **Response**: HTML modal content for meeting scheduling

### GET/POST /deals/{id}/send-email
- **Description**: Handle email composition for deals
- **GET**: Returns email composition modal
- **POST**: Sends email (currently simulated)
- **Response**: HTML modal content or JSON success message

### GET /deals/export
- **Description**: Export deals report
- **Query Parameters**: 
  - format: json|csv (default: json)
- **Response**: JSON or CSV file download

## Task Management

### GET /tasks/{id}
- **Description**: Get task details for viewing
- **Response**: JSON with task data or HTML modal content

### GET /tasks/{id}/edit
- **Description**: Get task edit form data
- **Response**: JSON with task data and agents list or HTML modal content

### PUT/POST /tasks/{id}
- **Description**: Update task information
- **Body**: Form data with task fields
- **Response**: JSON with success message and updated task data

### DELETE /tasks/{id}
- **Description**: Delete a task
- **Response**: JSON with success/error message

## Recommendations and Export

### GET /recommendations/export
- **Description**: Export recommendations report
- **Query Parameters**:
  - customer_id: Optional customer ID to filter recommendations
  - format: pdf|excel|json (default: pdf)
- **Response**: File download in requested format

### GET /properties/{id}/schedule-viewing
- **Description**: Get property viewing scheduling interface
- **Response**: JSON with property, customers, and agents data or HTML modal content

## SMS Queue

### POST /api/sms/send
- **Description**: Queue outbound SMS messages for async worker delivery
- **Body**:
  - `message` (required)
  - `provider` (optional, defaults to `SMS_PROVIDER` / `melipayamak`)
  - Recipient targeting options:
    - `recipients: []` direct list
    - `recipient_mode=all`
    - `recipient_mode=group` + `group_id`
    - `recipient_mode=custom` + `custom_numbers`
- **Response**: JSON with `success`, `queued_count`, and `messages`

### GET /api/sms/history
- **Description**: Retrieve queued/sent/failed SMS history
- **Query Parameters**:
  - `limit` (optional, default 20)
  - `status` (optional: pending|sent|failed)
- **Response**: JSON with `success`, `count`, and `messages`

## Error Handling

All endpoints implement consistent error handling:
- **404**: Resource not found
- **400**: Validation errors or bad request
- **500**: Internal server error

Error responses include:
```json
{
  "error": "Error message description",
  "errors": {} // Field-specific validation errors when applicable
}
```

Success responses include:
```json
{
  "success": true,
  "message": "Success message",
  "data": {} // Relevant data when applicable
}
```

## Authentication & Security

- CSRF protection is implemented for all POST/PUT/DELETE requests
- All endpoints validate user permissions
- Input sanitization and validation is performed on all form data
- SQL injection protection through SQLAlchemy ORM

## Content Types

- All AJAX requests should include `X-Requested-With: XMLHttpRequest` header
- Form submissions accept `application/x-www-form-urlencoded`
- JSON responses use `application/json` content type
- File downloads use appropriate MIME types (PDF, Excel, CSV)
