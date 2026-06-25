"""
End-to-end integration tests for CRUD operations
Tests complete workflows from frontend to database
"""

import pytest
from flask import url_for
from services.database_service import database_service


class TestCRUDIntegration:
    """Integration tests for complete CRUD workflows"""

    def test_agent_edit_workflow(self, client, app, db_setup):
        """Test complete agent edit workflow"""
        with app.app_context():
            # Create initial agent
            agent = database_service.add_agent(
                name="Original Agent",
                email="original@example.com",
                phone="123-456-7890",
                specialization="Residential",
                bio="Original bio"
            )
            
            # Step 1: Get edit form
            response = client.get(f'/agents/{agent.id}/edit',
                                headers={'X-Requested-With': 'XMLHttpRequest'})
            assert response.status_code == 200
            data = response.get_json()
            assert data['agent']['name'] == "Original Agent"
            
            # Step 2: Submit update
            response = client.post(f'/agents/{agent.id}',
                                 data={
                                     'name': 'Updated Agent',
                                     'email': 'updated@example.com',
                                     'phone': '987-654-3210',
                                     'specialization': 'Commercial',
                                     'bio': 'Updated bio',
                                     '_method': 'PUT'
                                 },
                                 headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            
            # Step 3: Verify database update
            updated_agent = database_service.get_agent(agent.id)
            assert updated_agent.name == 'Updated Agent'
            assert updated_agent.email == 'updated@example.com'
            assert updated_agent.specialization == 'Commercial'

    def test_customer_delete_workflow(self, client, app, db_setup):
        """Test complete customer delete workflow"""
        with app.app_context():
            # Create customer with related data
            customer = database_service.add_customer(
                name="Test Customer",
                email="customer@example.com",
                phone="123-456-7890",
                budget_min=100000,
                budget_max=200000
            )
            
            # Create related deal
            agent = database_service.add_agent(
                name="Test Agent",
                email="agent@example.com",
                phone="987-654-3210"
            )
            
            property_obj = database_service.add_property(
                title="Test Property",
                address="123 Test St",
                price=150000,
                property_type="house",
                bedrooms=3,
                bathrooms=2,
                square_feet=1500,
                description="Test property"
            )
            
            deal = database_service.add_deal(
                property_id=property_obj.id,
                customer_id=customer.id,
                agent_id=agent.id,
                status="prospecting"
            )
            deal_id = deal.id
            
            # Step 1: Delete customer
            response = client.delete(f'/customers/{customer.id}',
                                   headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            
            # Step 2: Verify customer is deleted
            deleted_customer = database_service.get_customer(customer.id)
            assert deleted_customer is None
            
            # Step 3: Verify related deal is also deleted (cascade)
            deleted_deal = database_service.get_deal(deal_id)
            assert deleted_deal is None

    def test_deal_view_workflow(self, client, app, db_setup):
        """Test complete deal view workflow"""
        with app.app_context():
            # Create complete deal with all relations
            agent = database_service.add_agent(
                name="Deal Agent",
                email="dealagent@example.com",
                phone="123-456-7890"
            )
            
            customer = database_service.add_customer(
                name="Deal Customer",
                email="dealcustomer@example.com",
                phone="987-654-3210",
                budget_min=150000,
                budget_max=250000
            )
            
            property_obj = database_service.add_property(
                title="Deal Property",
                address="456 Deal St",
                price=200000,
                property_type="house",
                bedrooms=3,
                bathrooms=2,
                square_feet=1600,
                description="Perfect family home",
                agent_id=agent.id
            )
            
            deal = database_service.add_deal(
                property_id=property_obj.id,
                customer_id=customer.id,
                agent_id=agent.id,
                status="negotiating",
                offer_amount=190000
            )
            
            # Step 1: Get deal details
            response = client.get(f'/deals/{deal.id}',
                                headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response.status_code == 200
            data = response.get_json()
            
            # Step 2: Verify all related data is included
            assert data['deal']['id'] == deal.id
            assert data['deal']['status'] == 'negotiating'
            assert data['deal']['offer_amount'] == 190000
            assert data['property']['title'] == 'Deal Property'
            assert data['customer']['name'] == 'Deal Customer'
            assert data['agent']['name'] == 'Deal Agent'

    def test_task_update_workflow(self, client, app, db_setup):
        """Test complete task update workflow"""
        with app.app_context():
            # Create agent and task
            agent = database_service.add_agent(
                name="Task Agent",
                email="taskagent@example.com",
                phone="123-456-7890"
            )
            
            task = database_service.add_task(
                title="Original Task",
                description="Original description",
                agent_id=agent.id,
                priority="low",
                status="pending"
            )
            
            # Step 1: Get edit form
            response = client.get(f'/tasks/{task.id}/edit',
                                headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['task']['title'] == "Original Task"
            assert data['task']['priority'] == "low"
            
            # Step 2: Submit update
            response = client.post(f'/tasks/{task.id}',
                                 data={
                                     'title': 'Updated Task',
                                     'description': 'Updated description',
                                     'priority': 'high',
                                     'status': 'in_progress',
                                     '_method': 'PUT'
                                 },
                                 headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            
            # Step 3: Verify database update
            updated_task = database_service.get_task(task.id)
            assert updated_task.title == 'Updated Task'
            assert updated_task.priority == 'high'
            assert updated_task.status == 'in_progress'

    def test_export_functionality(self, client, app, db_setup):
        """Test export functionality workflow"""
        with app.app_context():
            # Create test data for export
            agent = database_service.add_agent(
                name="Export Agent",
                email="export@example.com",
                phone="123-456-7890"
            )
            
            customer = database_service.add_customer(
                name="Export Customer",
                email="exportcustomer@example.com",
                phone="987-654-3210",
                budget_min=100000,
                budget_max=300000,
                preferred_bedrooms=3,
                preferred_type="house"
            )
            
            # Create matching properties
            prop1 = database_service.add_property(
                title="Export Property 1",
                address="123 Export St",
                price=200000,
                property_type="house",
                bedrooms=3,
                bathrooms=2,
                square_feet=1500,
                description="Great house",
                status="active",
                agent_id=agent.id
            )
            
            prop2 = database_service.add_property(
                title="Export Property 2",
                address="456 Export Ave",
                price=250000,
                property_type="house",
                bedrooms=3,
                bathrooms=2,
                square_feet=1700,
                description="Another great house",
                status="active",
                agent_id=agent.id
            )
            
            # Create deals
            deal1 = database_service.add_deal(
                property_id=prop1.id,
                customer_id=customer.id,
                agent_id=agent.id,
                status="closed",
                offer_amount=195000
            )
            
            deal2 = database_service.add_deal(
                property_id=prop2.id,
                customer_id=customer.id,
                agent_id=agent.id,
                status="prospecting",
                offer_amount=240000
            )
            
            # Test recommendations export
            response = client.get(f'/recommendations/export?customer_id={customer.id}',
                                headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['customer_id'] == customer.id
            assert data['total_properties'] == 2
            assert len(data['properties']) == 2
            
            # Test deals export
            response = client.get('/deals/export',
                                headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['summary']['total_deals'] == 2
            assert data['summary']['total_value'] == 435000
            assert data['summary']['closed_deals'] == 1
            assert len(data['deals']) == 2

    def test_error_handling_workflow(self, client, app, db_setup):
        """Test error handling in complete workflows"""
        with app.app_context():
            # Test 1: Edit non-existent agent
            response = client.get('/agents/99999/edit',
                                headers={'X-Requested-With': 'XMLHttpRequest'})
            assert response.status_code == 404
            
            # Test 2: Update with validation errors
            agent = database_service.add_agent(
                name="Test Agent",
                email="test@example.com",
                phone="123-456-7890"
            )
            
            response = client.post(f'/agents/{agent.id}',
                                 data={
                                     'name': '',  # Required field empty
                                     'email': 'invalid-email',  # Invalid format
                                     'phone': '123-456-7890',
                                     '_method': 'PUT'
                                 },
                                 headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response.status_code == 400
            data = response.get_json()
            assert data['error'] == 'Validation failed'
            assert 'errors' in data
            
            # Test 3: Delete non-existent record
            response = client.delete('/customers/99999',
                                   headers={'X-Requested-With': 'XMLHttpRequest'})
            assert response.status_code == 404

    def test_data_integrity_workflow(self, client, app, db_setup):
        """Test data integrity across CRUD operations"""
        with app.app_context():
            # Create interconnected data
            agent = database_service.add_agent(
                name="Integrity Agent",
                email="integrity@example.com",
                phone="123-456-7890"
            )
            
            customer = database_service.add_customer(
                name="Integrity Customer",
                email="integritycustomer@example.com",
                phone="987-654-3210"
            )
            
            property_obj = database_service.add_property(
                title="Integrity Property",
                address="789 Integrity Blvd",
                price=300000,
                property_type="house",
                bedrooms=4,
                bathrooms=3,
                square_feet=2000,
                description="Luxury home",
                agent_id=agent.id
            )
            
            deal = database_service.add_deal(
                property_id=property_obj.id,
                customer_id=customer.id,
                agent_id=agent.id,
                status="negotiating",
                offer_amount=290000
            )
            deal_id = deal.id
            
            task = database_service.add_task(
                title="Follow up on deal",
                description="Call customer about offer",
                agent_id=agent.id,
                priority="high",
                status="pending"
            )
            
            # Test 1: Update agent and verify relationships maintained
            response = client.post(f'/agents/{agent.id}',
                                 data={
                                     'name': 'Updated Integrity Agent',
                                     'email': 'updated-integrity@example.com',
                                     'phone': '555-123-4567',
                                     '_method': 'PUT'
                                 },
                                 headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response.status_code == 200
            
            # Verify relationships still exist
            updated_deal = database_service.get_deal_with_relations(deal_id)
            assert updated_deal.agent.name == 'Updated Integrity Agent'
            
            updated_task = database_service.get_task(task.id)
            assert updated_task.agent_id == agent.id
            
            # Test 2: Delete customer and verify cascade
            response = client.delete(f'/customers/{customer.id}',
                                   headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response.status_code == 200
            
            # Verify deal is also deleted (cascade)
            deleted_deal = database_service.get_deal(deal_id)
            assert deleted_deal is None
            
            # Verify agent and property still exist
            remaining_agent = database_service.get_agent(agent.id)
            assert remaining_agent is not None
            
            remaining_property = database_service.get_property(property_obj.id)
            assert remaining_property is not None

    def test_concurrent_operations_workflow(self, client, app, db_setup):
        """Test handling of concurrent operations"""
        with app.app_context():
            # Create test agent
            agent = database_service.add_agent(
                name="Concurrent Agent",
                email="concurrent@example.com",
                phone="123-456-7890"
            )
            
            # Simulate concurrent updates
            # First update
            response1 = client.post(f'/agents/{agent.id}',
                                  data={
                                      'name': 'First Update',
                                      'email': 'first@example.com',
                                      'phone': '111-111-1111',
                                      '_method': 'PUT'
                                  },
                                  headers={'X-Requested-With': 'XMLHttpRequest'})
            
            # Second update (should overwrite first)
            response2 = client.post(f'/agents/{agent.id}',
                                  data={
                                      'name': 'Second Update',
                                      'email': 'second@example.com',
                                      'phone': '222-222-2222',
                                      '_method': 'PUT'
                                  },
                                  headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response1.status_code == 200
            assert response2.status_code == 200
            
            # Verify final state
            final_agent = database_service.get_agent(agent.id)
            assert final_agent.name == 'Second Update'
            assert final_agent.email == 'second@example.com'

    def test_bulk_operations_workflow(self, client, app, db_setup):
        """Test bulk operations and their effects"""
        with app.app_context():
            # Create multiple agents
            agents = []
            for i in range(5):
                agent = database_service.add_agent(
                    name=f"Bulk Agent {i+1}",
                    email=f"bulk{i+1}@example.com",
                    phone=f"123-456-789{i}"
                )
                agents.append(agent)
            
            # Create customers and deals for each agent
            for i, agent in enumerate(agents):
                customer = database_service.add_customer(
                    name=f"Bulk Customer {i+1}",
                    email=f"bulkcustomer{i+1}@example.com",
                    phone=f"987-654-321{i}"
                )
                
                property_obj = database_service.add_property(
                    title=f"Bulk Property {i+1}",
                    address=f"{i+1}00 Bulk St",
                    price=200000 + (i * 50000),
                    property_type="house",
                    bedrooms=3,
                    bathrooms=2,
                    square_feet=1500,
                    description=f"Bulk property {i+1}",
                    agent_id=agent.id
                )
                
                database_service.add_deal(
                    property_id=property_obj.id,
                    customer_id=customer.id,
                    agent_id=agent.id,
                    status="prospecting",
                    offer_amount=200000 + (i * 45000)
                )
            
            # Test bulk export
            response = client.get('/deals/export',
                                headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['summary']['total_deals'] == 5
            assert len(data['deals']) == 5
            
            # Test recommendations export (all properties)
            response = client.get('/recommendations/export',
                                headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['total_properties'] == 5
            assert len(data['properties']) == 5
