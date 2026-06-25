from flask import Blueprint, jsonify, request
from services.gemini_service import gemini_service
from services.workflow_service import workflow_service
from database import db
from sqlalchemy_models import Property, Customer, Deal
from utils.execution_tracer import log_execution

bp = Blueprint("rag", __name__)

@bp.route('/query', methods=['POST'])
@log_execution
def rag_query():
    """
    Handle RAG queries: retrieve relevant context from CRM data and generate AI response.
    Expected JSON: {
        "query": "user question",
        "context_type": "property|customer|deal|task|all" (optional, default: all),
        "limit": 10 (optional, max results to consider)
    }
    """
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({"error": "Missing 'query' in request body"}), 400

        query = data['query']
        context_type = data.get('context_type', 'all')
        limit = min(int(data.get('limit', 10)), 50)  # Cap at 50

        # Gather relevant context based on type
        context = {
            "query": query,
            "properties": [],
            "customers": [],
            "deals": [],
            "tasks": []
        }

        if context_type in ['property', 'all']:
            properties = db.session.query(Property).filter(
                Property.is_deleted.is_(False),
                Property.status == 'active'
            ).limit(limit).all()
            context["properties"] = [
                {
                    "id": p.id,
                    "title": p.title,
                    "address": p.address,
                    "price": p.price,
                    "bedrooms": p.bedrooms,
                    "bathrooms": p.bathrooms,
                    "square_feet": p.square_feet,
                    "property_type": p.property_type,
                    "description": p.description
                } for p in properties
            ]

        if context_type in ['customer', 'all']:
            customers = db.session.query(Customer).filter(
                Customer.is_deleted.is_(False),
                Customer.status.in_(['prospect', 'active'])
            ).limit(limit).all()
            context["customers"] = [
                {
                    "id": c.id,
                    "name": c.name,
                    "email": c.email,
                    "phone": c.phone,
                    "budget_min": c.budget_min,
                    "budget_max": c.budget_max,
                    "location_preference": c.location_preference,
                    "preferred_type": c.preferred_type,
                    "preferred_bedrooms": c.preferred_bedrooms,
                    "preferred_bathrooms": c.preferred_bathrooms
                } for c in customers
            ]

        if context_type in ['deal', 'all']:
            deals = db.session.query(Deal).filter(
                Deal.is_deleted.is_(False)
            ).limit(limit).all()
            context["deals"] = [
                {
                    "id": d.id,
                    "property_id": d.property_id,
                    "customer_id": d.customer_id,
                    "offer_amount": d.offer_amount,
                    "status": d.status,
                    "notes": d.notes
                } for d in deals
            ]

        if context_type in ['task', 'all']:
            from sqlalchemy_models import Task
            from services.workflow_service import TaskStatus
            tasks = db.session.query(Task).filter(
                Task.status.in_([TaskStatus.PENDING.value, TaskStatus.IN_PROGRESS.value])
            ).limit(limit).all()
            context["tasks"] = [
                {
                    "id": t.id,
                    "title": t.title,
                    "description": t.description,
                    "priority": t.priority,
                    "status": t.status,
                    "due_date": t.due_date.isoformat() if t.due_date else None,
                    "property_id": t.property_id,
                    "customer_id": t.customer_id,
                    "deal_id": t.deal_id
                } for t in tasks
            ]

        # Use Gemini service to generate response based on context
        # For now, we'll use a simple approach: combine context and ask gemini
        # In a full implementation, we would use embeddings and retrieval
        context_summary = f"""
        User Query: {query}

        Available Context:
        - Properties: {len(context['properties'])} records
        - Customers: {len(context['customers'])} records
        - Deals: {len(context['deals'])} records
        - Tasks: {len(context['tasks'])} records

        Sample data (first 2 of each type if available):
        """

        # Add sample data to prompt
        if context['properties']:
            context_summary += "\n\nProperties Sample:\n"
            for prop in context['properties'][:2]:
                context_summary += f"- {prop['title']}: {prop['address']}, ${prop['price']}, {prop['bedrooms']}bd/{prop['bathrooms']}ba\n"

        if context['customers']:
            context_summary += "\n\nCustomers Sample:\n"
            for cust in context['customers'][:2]:
                context_summary += f"- {cust['name']}: {cust['location_preference']}, budget ${cust['budget_min']}-{cust['budget_max']}\n"

        if context['deals']:
            context_summary += "\n\nDeals Sample:\n"
            for deal in context['deals'][:2]:
                context_summary += f"- Deal #{deal['id']}: ${deal['offer_amount']}, status {deal['status']}\n"

        if context['tasks']:
            context_summary += "\n\nTasks Sample:\n"
            for task in context['tasks'][:2]:
                context_summary += f"- {task['title']}: {task['priority']} priority, due {task['due_date'] or 'N/A'}\n"

        # Generate response using Gemini
        try:
            # We'll use the existing gemini service for text generation
            # This is a simplified approach - in reality you'd want to use proper RAG
            response_text = gemini_service.generate_response(
                prompt=f"Based on the following CRM data, answer the user's question concisely and helpfully:\n\n{context_summary}\n\nQuestion: {query}",
                temperature=0.7
            )
        except Exception as e:
            # Fallback if Gemini fails
            response_text = f"Based on the CRM data, I found {len(context['properties'])} properties, {len(context['customers'])} customers, {len(context['deals'])} deals, and {len(context['tasks'])} tasks. However, I'm unable to generate a detailed response due to a temporary issue with the AI service. Please try again later."

        return jsonify({
            "success": True,
            "response": response_text,
            "context_used": {
                "properties_count": len(context['properties']),
                "customers_count": len(context['customers']),
                "deals_count": len(context['deals']),
                "tasks_count": len(context['tasks'])
            },
            "query": query
        })

    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500