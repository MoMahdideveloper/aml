# Data Model: UI Review Feature

## Entities

### UI Review Report
- id: UUID (primary key)
- created_at: Timestamp
- updated_at: Timestamp
- reviewer_name: String
- review_date: Date
- status: Enum (pending, in_progress, completed)
- total_issues: Integer
- critical_issues: Integer
- high_issues: Integer
- medium_issues: Integer
- low_issues: Integer

### Non-Functional Element
- id: UUID (primary key)
- report_id: Foreign key to UI Review Report
- page: String (e.g., Dashboard, Properties)
- section: String (e.g., navigation, content area)
- element_type: String (e.g., button, link, form field)
- element_description: String
- expected_behavior: String
- actual_behavior: String
- severity: Enum (critical, high, medium, low)
- error_message: String (optional)
- steps_to_reproduce: String (optional)
- screenshot: String (URL or path, optional)
- created_at: Timestamp

### Page Section
- id: UUID (primary key)
- report_id: Foreign key to UI Review Report
- page: String
- section_name: String
- description: String

### Error Log Entry
- id: UUID (primary key)
- report_id: Foreign key to UI Review Report
- element_id: Foreign key to Non-Functional Element (optional)
- log_level: String (error, warn, info)
- message: String
- timestamp: Timestamp
- source: String (e.g., console, network)

### Severity Classification
- id: UUID (primary key)
- level: String (critical, high, medium, low)
- description: String
- criteria: String

## Relationships
- One UI Review Report has many Non-Functional Elements.
- One UI Review Report has many Page Sections.
- One Non-Functional Element can have many Error Log Entries.
- Severity Classification is a lookup table.