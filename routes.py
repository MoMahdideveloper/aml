from flask import render_template, request, redirect, url_for, flash, jsonify
from app import app
from data_manager import data_manager
from gemini_service import gemini_service
from vector_init import ensure_vector_database_ready, vector_initializer
from datetime import datetime
import logging

@app.route('/')
def dashboard():
    """Main dashboard with key metrics and recent activities"""
    stats = data_manager.get_dashboard_stats()
    recent_properties = data_manager.get_properties()[:5]
    recent_deals = data_manager.get_deals()[:5]
    pending_tasks = data_manager.get_tasks(status="pending")[:5]
    
    # Get property and customer names for deals
    for deal in recent_deals:
        deal.property_name = data_manager.get_property(deal.property_id).title if data_manager.get_property(deal.property_id) else "Unknown Property"
        deal.customer_name = data_manager.get_customer(deal.customer_id).name if data_manager.get_customer(deal.customer_id) else "Unknown Customer"
        deal.agent_name = data_manager.get_agent(deal.agent_id).name if data_manager.get_agent(deal.agent_id) else "Unknown Agent"
    
    # Get agent names for tasks
    for task in pending_tasks:
        task.agent_name = data_manager.get_agent(task.agent_id).name if data_manager.get_agent(task.agent_id) else "Unknown Agent"
    
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
    properties = data_manager.get_properties(
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
    agents = data_manager.get_agents()
    
    # Get unique values for filter dropdowns
    all_properties = data_manager.get_properties()
    property_types = sorted(set(p.property_type for p in all_properties))
    neighborhoods = sorted(set(p.neighborhood for p in all_properties if p.neighborhood))
    property_conditions = ['excellent', 'good', 'fair', 'needs_renovation']
    property_categories = ['residential', 'commercial', 'industrial']
    
    # Add agent names to properties
    for prop in properties:
        prop.agent_name = data_manager.get_agent(prop.agent_id).name if prop.agent_id and data_manager.get_agent(prop.agent_id) else "Unassigned"
    
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
        
        property_obj = data_manager.add_property(
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
    agents = data_manager.get_agents()
    
    # Calculate agent statistics
    for agent in agents:
        agent_properties = [p for p in data_manager.get_properties() if p.agent_id == agent.id]
        agent_deals = [d for d in data_manager.get_deals() if d.agent_id == agent.id]
        agent_tasks = data_manager.get_tasks(agent_id=agent.id)
        
        agent.active_listings = len([p for p in agent_properties if p.status == "active"])
        agent.total_deals = len(agent_deals)
        agent.pending_tasks = len([t for t in agent_tasks if t.status == "pending"])
    
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
        
        agent = data_manager.add_agent(name, email, phone, specialization, bio)
        flash(f'Agent "{name}" added successfully!', 'success')
    except Exception as e:
        flash(f'Error adding agent: {str(e)}', 'error')
    
    return redirect(url_for('agents'))

@app.route('/customers')
def customers():
    """Customer management page"""
    customers = data_manager.get_customers()
    
    # Add deal and interaction counts
    for customer in customers:
        customer_deals = [d for d in data_manager.get_deals() if d.customer_id == customer.id]
        customer.total_deals = len(customer_deals)
        customer.active_deals = len([d for d in customer_deals if d.status not in ["closed_won", "closed_lost"]])
    
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
        
        customer = data_manager.add_customer(name, email, phone, budget_min, budget_max,
                                           preferred_bedrooms, preferred_bathrooms,
                                           preferred_type, location_preference)
        
        flash(f'Customer "{name}" added successfully!', 'success')
    except Exception as e:
        flash(f'Error adding customer: {str(e)}', 'error')
    
    return redirect(url_for('customers'))

@app.route('/deals')
def deals():
    """Deal management page"""
    deals = data_manager.get_deals()
    properties = data_manager.get_properties()
    customers = data_manager.get_customers()
    agents = data_manager.get_agents()
    
    # Add related information to deals
    for deal in deals:
        deal.property_obj = data_manager.get_property(deal.property_id)
        deal.customer_obj = data_manager.get_customer(deal.customer_id)
        deal.agent_obj = data_manager.get_agent(deal.agent_id)
    
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
        
        deal = data_manager.add_deal(property_id, customer_id, agent_id, status, offer_amount)
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
        
        deal = data_manager.update_deal(deal_id, **updates)
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
    
    tasks = data_manager.get_tasks(agent_id=agent_id, status=status)
    agents = data_manager.get_agents()
    
    # Add agent names to tasks
    for task in tasks:
        task.agent_obj = data_manager.get_agent(task.agent_id)
    
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
        
        task = data_manager.add_task(title, description, agent_id, priority, due_date)
        flash('Task added successfully!', 'success')
    except Exception as e:
        flash(f'Error adding task: {str(e)}', 'error')
    
    return redirect(url_for('tasks'))

@app.route('/tasks/<int:task_id>/complete', methods=['POST'])
def complete_task(task_id):
    """Mark task as completed"""
    try:
        task = data_manager.complete_task(task_id)
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
    customers = data_manager.get_customers()
    return render_template('recommendations.html', customers=customers)

@app.route('/recommendations/<int:customer_id>')
def get_customer_recommendations(customer_id):
    """Get AI recommendations for a specific customer"""
    try:
        customer = data_manager.get_customer(customer_id)
        if not customer:
            flash('Customer not found!', 'error')
            return redirect(url_for('recommendations'))
        
        # Ensure vector database is ready
        ensure_vector_database_ready()
        
        properties = data_manager.get_properties(status="active")
        
        # Get AI-powered recommendations using vector search
        recommendations = gemini_service.get_property_recommendations(customer, properties)
        
        if not recommendations:
            flash('Unable to generate recommendations at this time. Please try again later.', 'warning')
        
        return render_template('recommendations.html', 
                             customers=data_manager.get_customers(),
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
        properties = data_manager.get_properties()
        analysis = gemini_service.analyze_market_trends(properties)
        return jsonify({'analysis': analysis})
    except Exception as e:
        logging.error(f"Error getting market analysis: {e}")
        return jsonify({'error': 'Unable to generate market analysis'}), 500

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
