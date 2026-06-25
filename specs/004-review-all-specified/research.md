# Research: Review of Non-functional UI Elements in Real Estate CRM

## Resolved NEEDS CLARIFICATION

1. Definition of "non-functional": For the purpose of this review, we define non-functional elements as UI components that do not trigger the expected action (e.g., button click does nothing, link does not navigate) or do not respond to user input (e.g., form field does not accept input). We exclude performance issues (like slow loading) and focus on broken interactions.

2. Mobile responsiveness testing: The review will include checking for basic mobile responsiveness (e.g., elements are visible and tappable on mobile screen sizes) but not exhaustive testing across all devices.

3. Browser compatibility testing: We will test on the latest versions of Chrome, Firefox, Safari, and Edge. We will not test on older versions unless specified.

4. Severity criteria: We will use the following:
   - Critical: Element causes data loss or security issue (e.g., delete button that doesn't work but should, or submit button that doesn't validate).
   - High: Element breaks core functionality (e.g., search button on properties page doesn't work).
   - Medium: Element causes inconvenience but workaround exists (e.g., a link that doesn't work but the same information is elsewhere).
   - Low: Cosmetic issue or minor inconvenience (e.g., button alignment off by a few pixels).

5. Browser compatibility requirements: As above, we will test on the latest versions of Chrome, Firefox, Safari, and Edge.

## Technology Choices

We are implementing the CRM in n8n because:
- n8n provides a visual workflow editor for creating automation and APIs.
- It allows rapid development of CRUD operations without writing backend code.
- It supports PostgreSQL for data storage.
- It has built-in support for webhooks and REST APIs.

We will use n8n to create:
- Webhook endpoints for each CRM feature (Properties, Agents, etc.)
- Workflows that interact with the PostgreSQL database.
- Custom nodes if necessary for complex operations.

## Alternatives Considered

- Traditional Flask/Python backend: More code, slower to develop.
- Node.js/Express: More flexible but requires more boilerplate.
- Low-code platforms (like Retool): Good for internal tools but less flexibility for complex workflows.

We chose n8n for its balance of visual development and extensibility.