# CRM Event-Driven Multi-Channel Notification Workflow

## Purpose
This workflow demonstrates how to send notifications via multiple channels (email, SMS, Slack) triggered by CRM events. It shows the integration pattern between:
1. CRM event ingestion (via webhook)
2. Context gathering from CRM API 
3. Dynamic notification content generation based on event type
4. Multi-channel delivery using the messaging hub
5. Audit logging of all notifications

## How It Works

### 1. Event Reception (`Webhook: CRM Event Trigger`)
- Receives POST requests from CRM when events occur
- Expected payload: `{ eventType, entityId, entityType, timestamp?, metadata? }`
- Supported events: `lead_created`, `property_updated`, `deal_stage_changed` (plus custom)

### 2. Context Gathering (`Fetch Entity Details`)
- Calls CRM REST API to get full entity details
- Uses standard CRM endpoints: `/api/customers/{id}`, `/api/properties/{id}`, etc.
- This demonstrates the "get context" requirement

### 3. Intelligent Message Generation (`Determine Notification Content`)
- Creates contextual messages based on event type and entity data
- Examples:
  - **Lead Created**: Notifies sales team with lead details and follow-up SLA
  - **Property Updated**: Alerts interested buyers about price/feature changes  
  - **Deal Stage Changed**: Informs agent and client about pipeline movement
  - **Generic**: Admin notification for unknown event types

### 4. Multi-Channel Delivery
- Splits notifications to send individually to each recipient
- Calls the "Multi-Channel Messaging Hub" webhook (`/webhook/send-message`)
- Sends via ALL THREE channels simultaneously: Email, SMS, Slack
- Each message includes recipient-specific metadata for personalization

### 5. Audit Trail (`Log Notification`)
- Records all notification attempts in `notification_logs` table
- Tracks: event details, recipient info, channels used, delivery status

## Expected CRM Event Payloads

### Lead Created
```json
{
  "eventType": "lead_created",
  "entityType": "lead",
  "entityId": "lead_123",
  "timestamp": "2026-06-25T10:30:00Z",
  "metadata": {
    "source": "website_forms",
    "campaign": "summer_open_house"
  }
}
```

### Property Updated  
```json
{
  "eventType": "property_updated", 
  "entityType": "property",
  "entityId": "prop_456",
  "timestamp": "2026-06-25T14:15:00Z"
}
```

### Deal Stage Changed
```json
{
  "eventType": "deal_stage_changed",
  "entityType": "deal", 
  "entityId": "deal_789",
  "timestamp": "2026-06-25T09:00:00Z",
  "metadata": {
    "old_stage": "negotiation",
    "new_stage": "under_contract"
  }
}
```

## Integration Points

### With Existing Workflows:
1. **Lead Processing Workflow** → Trigger this on `lead_created` events
2. **Property Update Notification** → Trigger this on `property_updated` events  
3. **Deal Management Workflows** → Trigger this on `deal_stage_changed` events
4. **Custom CRM Webhooks** → Configure your CRM to POST to `/webhook/crm-event-notification`

### Dependencies:
1. **Multi-Channel Messaging Hub** (`multi_channel_messaging_hub.json`) - Must be deployed and active
2. **CRM API Access** - Ensure n8n can reach `http://host.docker.internal:5000/api`
3. **Database Table** - Requires `notification_logs` table (schema in N8N_ENHANCEMENT_SUMMARY.md)

## Configuration Notes

### Channel Configuration:
Currently sends to all three channels (email, SMS, Slack). To customize:
- Edit the `channels` array in "Prepare Individual Notifications" node
- Example for email-only: `['email']`
- Example for urgent alerts: `['sms', 'slack']`  

### Priority Handling:
All notifications use `normal` priority by default. To implement priority:
- Add priority logic in "Determine Notification Content" based on event type
- High priority: `lead_created`, `deal_stage_changed` to `won/lost`
- Low priority: routine updates, system notifications

### Security:
- Ensure the webhook is properly secured (n8n provides built-in auth options)
- Validate incoming event signatures if your CRM supports webhook signatures
- Consider rate limiting for high-volume event sources

## Sample n8n Execution Flow:
```
CRM Event → [Webhook] → [Parse Event] → [Fetch Entity Details] 
          → [Generate Message] → [Prepare Notifications] → [Split Batch]
          → [For each recipient:] → [Call Messaging Hub] → [Log Result]
```

This workflow provides a template that can be extended for additional event types, channels, or personalization logic while demonstrating the core pattern of event-driven, context-aware, multi-channel notifications.