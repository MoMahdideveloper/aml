# n8n Workflow Plan for Full CRM Control

## Overview
Use n8n to orchestrate automation across all CRM modules:
- **Database** (Postgres) – direct reads/writes or via CRM API
- **Customers** – create, update, segment, enrich
- **Sellers / Property Owners** – sync with property listings
- **Agents** – assignment, performance tracking, notifications
- **CRM Core** – trigger existing endpoints (properties, deals, tasks, etc.)
- **Chat** – send/receive messages via webhook or custom integration
- **Recommended Files** – update recommendation engine, generate reports
- **SMS** – send via Twilio, AWS SNS, or custom gateway
- **Other** – email, Slack, webhooks, file system, AI services

All automations built from reusable sub-workflows triggered by:
1. **CRM Webhooks** (if CRM emits them)
2. **Polling** (CRON) – query tables for changes (timestamps/flags)
3. **Manual Triggers** – n8n UI or external HTTP
4. **Event Triggers** – file upload, inbound SMS, inbound email, chat messages

## Core Building Blocks

### 1. HTTP Request Node (CRM API)
- Base URL: `http://host.docker.internal:5000` (from n8n container)
- Auth: none needed for internal calls; add API key header if CRM requires it
- Endpoints (examples):
  - `POST /api/analysis/trigger` – start analysis
  - `GET /api/customers` / `POST /api/customers` – customer CRUD
  - `GET /api/properties` / `POST /api/properties` – property CRUD
  - `GET /api/deals` / `POST /api/deals` – deal CRUD
  - `GET /api/tasks` / `POST /api/tasks` – task CRUD
  - `GET /api/agents` / `POST /api/agents` – agent CRUD
  - `GET /api/sms/history` / `POST /api/sms/send` – SMS
  - `GET /api/v1/chat/copilot` – chat
  - `GET /api/recommendations` / `POST /api/recommendations` – recommended files

### 2. Database Node (Direct Postgres Access)
- Host: `host.docker.internal` (or `localhost` if tunneling)
- Port: `5432`
- Database: `real_estate_crm` (from `.env`)
- User: `gptvli`
- Password: `gptvli`
- Use for:
  - Complex joins not exposed via API
  - Bulk updates
  - Reading change-tracking columns (e.g., `updated_at`, `_version`)
  - Writing audit logs

### 3. Function / Set Nodes
- Data transformation
- Conditional logic
- Error handling
- Preparing payloads for API calls

### 4. Trigger Nodes
- **Webhook**: Listen for incoming HTTP (e.g., from CRM webhooks, forms, chat widgets)
- **Cron**: Schedule periodic checks (e.g., every 5 min for new leads)
- **Manual**: Trigger from n8n UI for testing or ad-hoc runs
- **Email**: Parse inbound emails (e.g., leads from website forms)
- **SMS**: Inbound SMS via Twilio, AWS SNS, etc.
- **File**: Watch for uploads (e.g., document scanning for KYC)

### 5. Action Nodes
- **Email Send**: SendGrid, SMTP, etc.
- **Slack**: Post to channels or send direct messages
- **Telegram**: For agent notifications
- **Twilio / AWS SNS**: Send SMS
- **PDF Generator**: Create reports from templates
- **Google Sheets**: Export reports, lead sheets
- **Notion / Airtable**: Sync to external tools

## Example Workflows

### 1. New Lead Capture → Enrich → Assign → Notify
**Trigger**: Webhook (from website contact form)  
**Steps**:
1. Parse incoming JSON (name, email, phone, property interest)
2. HTTP Request: `GET /api/customers?email={{email}}` to check existence
3. If not exists: `POST /api/customers` to create new lead
4. Function: Enrich with lead score based on property value, location
5. HTTP Request: `GET /api/agents?availability=true&specialty={{property_type}}` to find agent
6. HTTP Request: `POST /api/tasks` to assign follow-up task to agent
7. Slack: Notify agent channel with lead details
8. Email: Send auto-response to lead with next steps

### 2. Property Update → Sync Recommendations → Notify Interested Buyers
**Trigger**: Cron (every 15 min) polling `properties` table for updated_at > last_run  
**Steps**:
1. SQL: `SELECT * FROM properties WHERE updated_at > $last_run`
2. For each property:
   a. Function: Extract features (price, beds, baths, location)
   b. HTTP Request: `POST /api/recommendations/generate` with property features
   c. HTTP Request: `GET /api/customers?property_interest matches` to find interested buyers
   d. For each matched customer:
      - Email: Send property update alert
      - SMS: If phone opt-in, send brief SMS alert
3. Function: Update `last_run` timestamp in n8n workflow metadata (or use a helper table)

### 3. Incoming SMS → Log → Auto-Response → Assign Agent
**Trigger**: Twilio (incoming SMS webhook)  
**Steps**:
1. Extract `From` (phone), `Body` (message)
2. HTTP Request: `GET /api/customers?phone={{From}}` to find customer
3. If not found: create provisional customer record
4. HTTP Request: `POST /api/sms/history` to log inbound message
5. Function: Detect intent (e.g., "STOP", "INFO", "AGENT")
6. If "STOP": update customer opt-out flag via API
7. If "INFO": send auto-reply with property details or FAQ via another SMS
8. If "AGENT" or no keyword match: create task for agent to follow up
9. Slack: Notify support team of incoming SMS requiring attention

### 4. Chat Message → Sentiment Analysis → Escalate if Negative
**Trigger**: Webhook (from chat widget)  
**Steps**:
1. Extract `message`, `user_id`, `session_id`
2. HTTP Request: `POST /api/v1/chat/copilot` to get bot response (if using AI)
3. Function: Run sentiment analysis (using external API or Node.js library)
4. If negative sentiment:
   a. HTTP Request: `POST /api/tasks` to create high-priority follow-up task
   b. Email: Notify supervisor with chat transcript
   c. Slack: Post to #escalations channel
5. Else: log chat normally via API

### 5. Nightly Report Generation → Distribute
**Trigger**: Cron (0 2 * * *)  
**Steps**:
1. HTTP Request: `POST /api/analysis/trigger` with `{"project_name":"Nightly Report","analysis_type":"full"}`
2. Wait: Poll `/api/analysis/reports/latest` until status=`completed`
3. HTTP Request: `GET /api/analysis/export/{report_id}?format=pdf`
4. Save PDF to `/tmp/report.pdf`
5. Email: Send to management team with summary
6. Slack: Post to #reports channel with file attachment
7. Function: Archive report in S3 or local storage

### 6. Agent Performance Dashboard Update
**Trigger**: Cron (every hour)  
**Steps**:
1. SQL: Query agent metrics from `tasks`, `deals`, `customers` tables
2. Function: Calculate KPIs (response time, conversion rate, etc.)
3. HTTP Request: `POST /api/agents/{id}/metrics` to update agent profile
4. Google Sheets: Append row for historical tracking
5. If KPI below threshold: send Slack alert to agent and manager

## Error Handling & Monitoring
- **Error Workflows**: Use `Error Trigger` to catch failures in any workflow
- **Retry Logic**: On HTTP Request nodes, set retry attempts (e.g., 3 times with exponential backoff)
- **Dead Letter Queue**: Failed executions saved to a Postgres table for manual review
- **Health Check**: Simple workflow that pings `/api/health` every minute and alerts on failure
- **Logging**: All workflows write execution details to `n8n_execution_log` table (custom)

## Security & Best Practices
- **Secrets**: Store API keys (Twilio, SendGrid, etc.) in n8n's Encrypted Settings
- **Network**: All traffic between n8n and CRM stays within Docker network (host.docker.internal)
- **IDempotency**: Use unique keys (e.g., webhook IDs, SMS message IDs) to prevent duplicate processing
- **Rate Limiting**: Respect API rate limits (e.g., Twilio, external AI APIs) using SplitInBatches or Throttle
- **Data Privacy**: Mask PII in logs; ensure GDPR compliance for data exports
- **Version Control**: Export workflows regularly to JSON and store in Git (./n8n/workflows/)

## Getting Started
1. Ensure Docker containers are running: `docker compose up -d`
2. Verify Flask API is accessible: `curl http://localhost:5000/api/health`
3. Access n8n: `http://localhost:5678` (login with `admin` / password from `.env`)
4. Import the starter workflow (see `n8m_starter_workflow.json` in repo) or build from scratch
5. Activate workflows and monitor via Executions tab
6. Adjust cron intervals and error handling as needed

---
*This plan provides a comprehensive foundation. Start with one high-impact workflow (e.g., lead capture) and expand iteratively.*