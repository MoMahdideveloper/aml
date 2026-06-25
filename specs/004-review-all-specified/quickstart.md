# Quick Start: UI Review Feature in n8n

## Prerequisites
- n8n installed (via docker, npm, etc.)
- PostgreSQL database running
- n8n configured to use PostgreSQL

## Setup
1. Import the provided n8n workflows for the UI review feature.
2. Configure the webhook URLs in the workflows to match your n8n instance.
3. Set up the PostgreSQL credentials in n8n.
4. Activate the workflows.

## Usage
1. Start a new review by sending a POST request to `/webhook/reviews` with reviewer name and review date.
2. Add non-functional elements by sending POST requests to `/webhook/reviews/{reviewId}/elements`.
3. Optionally add error log entries to elements.
4. Generate a report by sending a GET request to `/webhook/reviews/{reviewId}/report`.

## Example
```bash
# Start a review
curl -X POST http://localhost:5678/webhook/reviews \
  -H "Content-Type: application/json" \
  -d '{"reviewer_name": "John Doe", "review_date": "2026-06-14"}'

# Add an element
curl -X POST http://localhost:5678/webhook/reviews/{reviewId}/elements \
  -H "Content-Type: application/json" \
  -d '{
    "page": "Dashboard",
    "section": "navigation",
    "element_type": "button",
    "element_description": "Refresh button",
    "expected_behavior": "Page should refresh",
    "actual_behavior": "Nothing happens",
    "severity": "high"
  }'

# Get report
curl http://localhost:5678/webhook/reports/{reviewId}/report
```

## Workflows Provided
- `Create Review Workflow`: Handles POST /reviews
- `Get Review Workflow`: Handles GET /reviews/{id}
- `Add Element Workflow`: Handles POST /reviews/{id}/elements
- `Get Element Workflow`: Handles GET /reviews/{id}/elements/{elementId}
- `Update Element Workflow`: Handles PUT /reviews/{id}/elements/{elementId}
- `Delete Element Workflow`: Handles DELETE /reviews/{id}/elements/{elementId}
- `Add Error Log Workflow`: Handles POST /reviews/{id}/elements/{elementId}/errors
- `Generate Report Workflow`: Handles GET /reviews/{id}/report

## Testing
Run the contract tests to verify the API contracts:
```bash
pytest tests/contracts/
```
Note: Tests will fail until the workflows are implemented.

## Customization
You can modify the workflows to suit your needs, such as changing the severity levels or adding additional fields.

## Troubleshooting
- If webhooks are not triggering, check the n8n logs and ensure the workflows are active.
- If database connection fails, verify the PostgreSQL credentials in n8n settings.

## Next Steps
Consider adding authentication to the webhooks, or integrating with a UI dashboard for easier interaction.