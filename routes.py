from flask import render_template, request, redirect, url_for, flash, jsonify
from app import app
from database_service import database_service
from gemini_service import gemini_service
from vector_init import ensure_vector_database_ready, vector_initializer
from datetime import datetime
import logging

@app.route('/')
def dashboard():
    """Main dashboard with key metrics and recent activities"""
    stats = database_service.get_dashboard_stats()
    recent_properties = stats['recent_properties']
    recent_deals = stats['recent_deals']
    pending_tasks = database_service.get_tasks(status="pending")[:5]
    
    # Get property and customer names for deals (SQLAlchemy relationships handle this)
    for deal in recent_deals:
        deal.property_name = deal.property.title if deal.property else "Unknown Property"
        deal.customer_name = deal.customer.name if deal.customer else "Unknown Customer"
        deal.agent_name = deal.agent.name if deal.agent else "Unknown Agent"
    
    # Get agent names for tasks (SQLAlchemy relationships handle this)
    for task in pending_tasks:
        task.agent_name = task.agent.name if task.agent else "Unknown Agent"
    
    return render_template('dashboard.html', 
                         stats=stats, 
                         recent_properties=recent_properties,
                         recent_deals=recent_deals,
                         pending_tasks=pending_tasks)

@app.route('/properties')
def properties():
    """Properties listing page with advanced search and filtering"""
    # Get all search parameters
    search_query = request.args.get('search', '')
    property_type = request.args.get('type', '')
    property_category = request.args.get('category', '')
    property_condition = request.args.get('condition', '')
    neighborhood = request.args.get('neighborhood', '')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    bedrooms = request.args.get('bedrooms', type=int)
    bathrooms = request.args.get('bathrooms', type=int)
    min_sqft = request.args.get('min_sqft', type=int)
    max_sqft = request.args.get('max_sqft', type=int)
    year_built_min = request.args.get('year_built_min', type=int)
    year_built_max = request.args.get('year_built_max', type=int)
    agent_id = request.args.get('agent_id', type=int)
    
    # Get filtered properties
    properties = database_service.get_properties(
        search=search_query,
        property_type=property_type,
        property_category=property_category,
        property_condition=property_condition,
        neighborhood=neighborhood,
        min_price=min_price,
        max_price=max_price,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        min_sqft=min_sqft,
        max_sqft=max_sqft,
        year_built_min=year_built_min,
        year_built_max=year_built_max,
        agent_id=agent_id
    )
    
    # Get agents for dropdown
    agents = database_service.get_agents()
    
    # Get unique values for filter dropdowns
    all_properties = database_service.get_properties()
    property_types = sorted(set(p.property_type for p in all_properties))
    neighborhoods = sorted(set(p.neighborhood for p in all_properties if p.neighborhood))
    property_conditions = ['excellent', 'good', 'fair', 'needs_renovation']
    property_categories = ['residential', 'commercial', 'industrial']
    
    # Add agent names to properties (SQLAlchemy relationships handle this)
    for prop in properties:
        prop.agent_name = prop.agent.name if prop.agent else "Unassigned"
    
    return render_template('properties.html', 
                         properties=properties, 
                         agents=agents,
                         property_types=property_types,
                         neighborhoods=neighborhoods,
                         property_conditions=property_conditions,
                         property_categories=property_categories,
                         # Current filter values
                         search_query=search_query,
                         property_type=property_type,
                         property_category=property_category,
                         property_condition=property_condition,
                         neighborhood=neighborhood,
                         min_price=min_price,
                         max_price=max_price,
                         bedrooms=bedrooms,
                         bathrooms=bathrooms,
                         min_sqft=min_sqft,
                         max_sqft=max_sqft,
                         year_built_min=year_built_min,
                         year_built_max=year_built_max,
                         agent_id=agent_id)

@app.route('/properties/add', methods=['POST'])
def add_property():
    """Add a new property with Iranian pricing system support"""
    try:
        title = request.form.get('title')
        address = request.form.get('address')
        property_type = request.form.get('property_type')
        bedrooms = int(request.form.get('bedrooms', 0))
        bathrooms = int(request.form.get('bathrooms', 0))
        square_feet = int(request.form.get('square_feet', 0))
        description = request.form.get('description', '')
        agent_id = request.form.get('agent_id')
        agent_id = int(agent_id) if agent_id else None
        
        # Enhanced fields
        year_built = request.form.get('year_built')
        year_built = int(year_built) if year_built else None
        parking_spaces = int(request.form.get('parking_spaces', 0))
        floors = int(request.form.get('floors', 1))
        units = int(request.form.get('units', 1))
        property_condition = request.form.get('property_condition', 'good')
        property_features = request.form.get('property_features', '')
        neighborhood = request.form.get('neighborhood', '')
        property_category = request.form.get('property_category', 'residential')
        
        # Iranian pricing system
        listing_type = request.form.get('listing_type', 'sale')
        
        if listing_type == 'sale':
            price = float(request.form.get('sale_price', 0))
            rahn = None
            ejare = None
        else:  # rental
            price = 0
            rahn = float(request.form.get('rahn', 0)) if request.form.get('rahn') else None
            ejare = float(request.form.get('ejare', 0)) if request.form.get('ejare') else None
        
        property_obj = database_service.add_property(
            title, address, price, property_type, bedrooms, bathrooms, square_feet, 
            description, "active", agent_id, year_built, parking_spaces, floors, units,
            property_condition, "", "", None, property_features, neighborhood, 
            property_category, listing_type, rahn, ejare
        )
        
        flash(f'Property "{title}" added successfully!', 'success')
    except Exception as e:
        flash(f'Error adding property: {str(e)}', 'error')
    
    return redirect(url_for('properties'))

@app.route('/agents')
def agents():
    """Agent management page"""
    agents = database_service.get_agents()
    
    # Calculate agent statistics using SQLAlchemy relationships
    for agent in agents:
        agent.active_listings = len([p for p in agent.properties if p.status == "active"])
        agent.total_deals = len(agent.deals)
        agent.pending_tasks = len([t for t in agent.tasks if t.status == "pending"])
    
    return render_template('agents.html', agents=agents)

@app.route('/agents/add', methods=['POST'])
def add_agent():
    """Add a new agent"""
    try:
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        specialization = request.form.get('specialization', '')
        bio = request.form.get('bio', '')
        
        agent = database_service.add_agent(name, email, phone, specialization, bio)
        flash(f'Agent "{name}" added successfully!', 'success')
    except Exception as e:
        flash(f'Error adding agent: {str(e)}', 'error')
    
    return redirect(url_for('agents'))

@app.route('/customers')
def customers():
    """Customer management page"""
    customers = database_service.get_customers()
    
    # Add deal and interaction counts using SQLAlchemy relationships
    for customer in customers:
        customer.total_deals = len(customer.deals)
        customer.active_deals = len([d for d in customer.deals if d.status not in ["closed_won", "closed_lost"]])
    
    return render_template('customers.html', customers=customers)

@app.route('/customers/add', methods=['POST'])
def add_customer():
    """Add a new customer"""
    try:
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        budget_min = float(request.form.get('budget_min', 0))
        budget_max = float(request.form.get('budget_max', 0))
        preferred_bedrooms = int(request.form.get('preferred_bedrooms', 0))
        preferred_bathrooms = int(request.form.get('preferred_bathrooms', 0))
        preferred_type = request.form.get('preferred_type', '')
        location_preference = request.form.get('location_preference', '')
        
        customer = database_service.add_customer(name, email, phone, budget_min, budget_max,
                                               preferred_bedrooms, preferred_bathrooms,
                                               preferred_type, location_preference)
        
        flash(f'Customer "{name}" added successfully!', 'success')
    except Exception as e:
        flash(f'Error adding customer: {str(e)}', 'error')
    
    return redirect(url_for('customers'))

@app.route('/deals')
def deals():
    """Deal management page"""
    deals = database_service.get_deals()
    properties = database_service.get_properties()
    customers = database_service.get_customers()
    agents = database_service.get_agents()
    
    # SQLAlchemy relationships automatically provide related objects
    # No need to manually add property_obj, customer_obj, agent_obj
    
    return render_template('deals.html', deals=deals, properties=properties, 
                         customers=customers, agents=agents)

@app.route('/deals/add', methods=['POST'])
def add_deal():
    """Add a new deal"""
    try:
        property_id = int(request.form.get('property_id'))
        customer_id = int(request.form.get('customer_id'))
        agent_id = int(request.form.get('agent_id'))
        status = request.form.get('status', 'prospecting')
        offer_amount = float(request.form.get('offer_amount', 0))
        
        deal = database_service.add_deal(property_id, customer_id, agent_id, status, offer_amount)
        flash('Deal added successfully!', 'success')
    except Exception as e:
        flash(f'Error adding deal: {str(e)}', 'error')
    
    return redirect(url_for('deals'))

@app.route('/deals/<int:deal_id>/update', methods=['POST'])
def update_deal(deal_id):
    """Update deal status"""
    try:
        status = request.form.get('status')
        offer_amount = request.form.get('offer_amount')
        
        updates = {'status': status}
        if offer_amount:
            updates['offer_amount'] = float(offer_amount)
        
        deal = database_service.update_deal(deal_id, **updates)
        if deal:
            flash('Deal updated successfully!', 'success')
        else:
            flash('Deal not found!', 'error')
    except Exception as e:
        flash(f'Error updating deal: {str(e)}', 'error')
    
    return redirect(url_for('deals'))

@app.route('/tasks')
def tasks():
    """Task management page"""
    agent_id = request.args.get('agent', type=int)
    status = request.args.get('status')
    
    tasks = database_service.get_tasks(agent_id=agent_id, status=status)
    agents = database_service.get_agents()
    
    # SQLAlchemy relationships automatically provide agent objects
    # No need to manually add agent_obj
    
    return render_template('tasks.html', tasks=tasks, agents=agents, current_date=datetime.now())

@app.route('/tasks/add', methods=['POST'])
def add_task():
    """Add a new task"""
    try:
        title = request.form.get('title')
        description = request.form.get('description')
        agent_id = int(request.form.get('agent_id'))
        priority = request.form.get('priority', 'medium')
        due_date_str = request.form.get('due_date')
        
        due_date = None
        if due_date_str:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
        
        task = database_service.add_task(title, description, agent_id, priority, due_date)
        flash('Task added successfully!', 'success')
    except Exception as e:
        flash(f'Error adding task: {str(e)}', 'error')
    
    return redirect(url_for('tasks'))

@app.route('/tasks/<int:task_id>/complete', methods=['POST'])
def complete_task(task_id):
    """Mark task as completed"""
    try:
        task = database_service.complete_task(task_id)
        if task:
            flash('Task completed successfully!', 'success')
        else:
            flash('Task not found!', 'error')
    except Exception as e:
        flash(f'Error completing task: {str(e)}', 'error')
    
    return redirect(url_for('tasks'))

@app.route('/recommendations')
def recommendations():
    """AI-powered property recommendations page"""
    customers = database_service.get_customers()
    return render_template('recommendations.html', customers=customers)

@app.route('/recommendations/<int:customer_id>')
def get_customer_recommendations(customer_id):
    """Get AI recommendations for a specific customer"""
    try:
        customer = database_service.get_customer(customer_id)
        if not customer:
            flash('Customer not found!', 'error')
            return redirect(url_for('recommendations'))
        
        # Ensure vector database is ready
        ensure_vector_database_ready()
        
        properties = database_service.get_properties()
        
        # Get AI-powered recommendations using vector search
        recommendations = gemini_service.get_property_recommendations(customer, properties)
        
        if not recommendations:
            flash('Unable to generate recommendations at this time. Please try again later.', 'warning')
        
        return render_template('recommendations.html', 
                             customers=database_service.get_customers(),
                             selected_customer=customer,
                             recommendations=recommendations)
        
    except Exception as e:
        logging.error(f"Error getting recommendations: {e}")
        flash('Error generating recommendations. Please try again.', 'error')
        return redirect(url_for('recommendations'))

@app.route('/api/market-analysis')
def market_analysis():
    """Get AI-powered market analysis"""
    try:
        properties = database_service.get_properties()
        analysis = gemini_service.analyze_market_trends(properties)
        return jsonify({'analysis': analysis})
    except Exception as e:
        logging.error(f"Error getting market analysis: {e}")
        return jsonify({'error': 'Unable to generate market analysis'}), 500

@app.route('/api/ai/parse/property', methods=['POST'])
def ai_parse_property():
    """
    Body JSON: { "text": "<free form description>" }
    Returns: { entity, data: {...}, missing: [...], confidence: float }
    """
    blob = (request.json or {}).get("text", "").strip()
    if not blob:
        return jsonify({"error": "text is required"}), 400
    result = gemini_service.extract_property_from_text(blob)
    return jsonify(result)

@app.route('/api/ai/parse/customer', methods=['POST'])
def ai_parse_customer():
    """
    Body JSON: { "text": "<free form description>" }
    Returns: { entity, data: {...}, missing: [...], confidence: float }
    """
    blob = (request.json or {}).get("text", "").strip()
    if not blob:
        return jsonify({"error": "text is required"}), 400
    result = gemini_service.extract_customer_from_text(blob)
    return jsonify(result)

@app.route('/api/vector-status')
def vector_status():
    """Get vector database status and statistics"""
    try:
        stats = vector_initializer.get_vector_database_stats()
        return jsonify(stats)
    except Exception as e:
        logging.error(f"Error getting vector status: {e}")
        return jsonify({'error': 'Unable to get vector status'}), 500

@app.route('/api/init-vector-db')
def init_vector_db():
    """Initialize vector database with current properties"""
    try:
        success = vector_initializer.initialize_vector_database()
        if success:
            return jsonify({'success': True, 'message': 'Vector database initialized successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to initialize vector database'}), 500
    except Exception as e:
        logging.error(f"Error initializing vector database: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test-vector-search')
def test_vector_search():
    """Test vector search functionality"""
    try:
        success = vector_initializer.test_vector_search()
        if success:
            return jsonify({'success': True, 'message': 'Vector search test passed'})
        else:
            return jsonify({'success': False, 'message': 'Vector search test failed'}), 500
    except Exception as e:
        logging.error(f"Error testing vector search: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500
