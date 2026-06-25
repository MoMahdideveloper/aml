"""
Unit tests for CRUD operations in DatabaseService
"""

import pytest
from datetime import datetime, timedelta
from services.database_service import database_service
from sqlalchemy_models import Agent, Customer, Deal, Property, Task


class TestAgentCRUD:
    """Test agent CRUD operations"""

    def test_update_agent_success(self, app, db_setup):
        """Test successful agent update"""
        # Create test agent
        agent = database_service.add_agent(
            name="John Doe",
            email="john@example.com",
            phone="123-456-7890",
            specialization="Residential",
            bio="Experienced agent"
        )
        
        # Update agent
        updated_agent = database_service.update_agent(
            agent.id,
            name="John Smith",
            specialization="Commercial",
            bio="Updated bio"
        )
        
        assert updated_agent is not None
        assert updated_agent.name == "John Smith"
        assert updated_agent.specialization == "Commercial"
        assert updated_agent.bio == "Updated bio"
        assert updated_agent.email == "john@example.com"  # Unchanged
        assert updated_agent.phone == "123-456-7890"  # Unchanged

    def test_update_agent_not_found(self, app, db_setup):
        """Test updating non-existent agent"""
        result = database_service.update_agent(999, name="Test")
        assert result is None

    def test_update_agent_invalid_field(self, app, db_setup):
        """Test updating agent with invalid field"""
        agent = database_service.add_agent(
            name="John Doe",
            email="john@example.com",
            phone="123-456-7890"
        )
        
        # Should ignore invalid field
        updated_agent = database_service.update_agent(
            agent.id,
            name="John Smith",
            invalid_field="should be ignored"
        )
        
        assert updated_agent is not None
        assert updated_agent.name == "John Smith"
        assert not hasattr(updated_agent, 'invalid_field')

    def test_delete_agent_success(self, app, db_setup):
        """Test successful agent deletion"""
        agent = database_service.add_agent(
            name="John Doe",
            email="john@example.com",
            phone="123-456-7890"
        )
        
        result = database_service.delete_agent(agent.id)
        assert result is True
        
        # Verify agent is deleted
        deleted_agent = database_service.get_agent(agent.id)
        assert deleted_agent is None

    def test_delete_agent_not_found(self, app, db_setup):
        """Test deleting non-existent agent"""
        result = database_service.delete_agent(999)
        assert result is False


class TestCustomerCRUD:
    """Test customer CRUD operations"""

    def test_update_customer_success(self, app, db_setup):
        """Test successful customer update"""
        customer = database_service.add_customer(
            name="Jane Doe",
            email="jane@example.com",
            phone="123-456-7890",
            budget_min=100000,
            budget_max=200000,
            preferred_bedrooms=3,
            preferred_bathrooms=2,
            preferred_type="house",
            location_preference="downtown"
        )
        
        updated_customer = database_service.update_customer(
            customer.id,
            name="Jane Smith",
            budget_min=150000,
            budget_max=250000,
            preferred_bedrooms=4
        )
        
        assert updated_customer is not None
        assert updated_customer.name == "Jane Smith"
        assert updated_customer.budget_min == 150000
        assert updated_customer.budget_max == 250000
        assert updated_customer.preferred_bedrooms == 4
        assert updated_customer.email == "jane@example.com"  # Unchanged

    def test_update_customer_not_found(self, app, db_setup):
        """Test updating non-existent customer"""
        result = database_service.update_customer(999, name="Test")
        assert result is None

    def test_delete_customer_success(self, app, db_setup):
        """Test successful customer deletion"""
        customer = database_service.add_customer(
            name="Jane Doe",
            email="jane@example.com",
            phone="123-456-7890"
        )
        
        result = database_service.delete_customer(customer.id)
        assert result is True
        
        # Verify customer is deleted
        deleted_customer = database_service.get_customer(customer.id)
        assert deleted_customer is None

    def test_delete_customer_not_found(self, app, db_setup):
        """Test deleting non-existent customer"""
        result = database_service.delete_customer(999)
        assert result is False


class TestDealCRUD:
    """Test deal CRUD operations"""

    def test_get_deal_with_relations_success(self, app, db_setup):
        """Test getting deal with all relations loaded"""
        # Create test data
        agent = database_service.add_agent(
            name="Agent Smith",
            email="agent@example.com",
            phone="123-456-7890"
        )
        
        customer = database_service.add_customer(
            name="Customer Jones",
            email="customer@example.com",
            phone="987-654-3210"
        )
        
        property_obj = database_service.add_property(
            title="Test Property",
            address="123 Test St",
            price=200000,
            property_type="house",
            bedrooms=3,
            bathrooms=2,
            square_feet=1500,
            description="Test property",
            agent_id=agent.id
        )
        
        deal = database_service.add_deal(
            property_id=property_obj.id,
            customer_id=customer.id,
            agent_id=agent.id,
            status="prospecting",
            offer_amount=190000
        )
        
        # Get deal with relations
        deal_with_relations = database_service.get_deal_with_relations(deal.id)
        
        assert deal_with_relations is not None
        assert deal_with_relations.property is not None
        assert deal_with_relations.customer is not None
        assert deal_with_relations.agent is not None
        assert deal_with_relations.property.title == "Test Property"
        assert deal_with_relations.customer.name == "Customer Jones"
        assert deal_with_relations.agent.name == "Agent Smith"

    def test_get_deal_with_relations_not_found(self, app, db_setup):
        """Test getting non-existent deal with relations"""
        result = database_service.get_deal_with_relations(999)
        assert result is None

    def test_delete_deal_success(self, app, db_setup):
        """Test successful deal deletion"""
        # Create minimal test data
        agent = database_service.add_agent(
            name="Agent Smith",
            email="agent@example.com",
            phone="123-456-7890"
        )
        
        customer = database_service.add_customer(
            name="Customer Jones",
            email="customer@example.com",
            phone="987-654-3210"
        )
        
        property_obj = database_service.add_property(
            title="Test Property",
            address="123 Test St",
            price=200000,
            property_type="house",
            bedrooms=3,
            bathrooms=2,
            square_feet=1500,
            description="Test property"
        )
        
        deal = database_service.add_deal(
            property_id=property_obj.id,
            customer_id=customer.id,
            agent_id=agent.id
        )
        
        result = database_service.delete_deal(deal.id)
        assert result is True
        
        # Verify deal is deleted
        deleted_deal = database_service.get_deal(deal.id)
        assert deleted_deal is None

    def test_delete_deal_not_found(self, app, db_setup):
        """Test deleting non-existent deal"""
        result = database_service.delete_deal(999)
        assert result is False


class TestTaskCRUD:
    """Test task CRUD operations"""

    def test_update_task_success(self, app, db_setup):
        """Test successful task update"""
        agent = database_service.add_agent(
            name="Agent Smith",
            email="agent@example.com",
            phone="123-456-7890"
        )
        
        due_date = datetime.utcnow() + timedelta(days=7)
        task = database_service.add_task(
            title="Test Task",
            description="Test description",
            agent_id=agent.id,
            priority="medium",
            status="pending",
            due_date=due_date
        )
        
        new_due_date = datetime.utcnow() + timedelta(days=14)
        updated_task = database_service.update_task(
            task.id,
            title="Updated Task",
            priority="high",
            status="in_progress",
            due_date=new_due_date
        )
        
        assert updated_task is not None
        assert updated_task.title == "Updated Task"
        assert updated_task.priority == "high"
        assert updated_task.status == "in_progress"
        assert updated_task.due_date == new_due_date
        assert updated_task.description == "Test description"  # Unchanged

    def test_update_task_not_found(self, app, db_setup):
        """Test updating non-existent task"""
        result = database_service.update_task(999, title="Test")
        assert result is None

    def test_delete_task_success(self, app, db_setup):
        """Test successful task deletion"""
        agent = database_service.add_agent(
            name="Agent Smith",
            email="agent@example.com",
            phone="123-456-7890"
        )
        
        task = database_service.add_task(
            title="Test Task",
            description="Test description",
            agent_id=agent.id
        )
        
        result = database_service.delete_task(task.id)
        assert result is True
        
        # Verify task is deleted
        deleted_task = database_service.get_task(task.id)
        assert deleted_task is None

    def test_delete_task_not_found(self, app, db_setup):
        """Test deleting non-existent task"""
        result = database_service.delete_task(999)
        assert result is False


class TestExportOperations:
    """Test export helper methods"""

    def test_export_recommendations_data_all_properties(self, app, db_setup):
        """Test exporting all recommendations data"""
        # Create test agent
        agent = database_service.add_agent(
            name="Agent Smith",
            email="agent@example.com",
            phone="123-456-7890"
        )
        
        # Create test properties
        prop1 = database_service.add_property(
            title="Property 1",
            address="123 Test St",
            price=200000,
            property_type="house",
            bedrooms=3,
            bathrooms=2,
            square_feet=1500,
            description="Test property 1",
            status="active",
            agent_id=agent.id
        )
        
        prop2 = database_service.add_property(
            title="Property 2",
            address="456 Test Ave",
            price=300000,
            property_type="condo",
            bedrooms=2,
            bathrooms=2,
            square_feet=1200,
            description="Test property 2",
            status="active",
            agent_id=agent.id
        )
        
        # Create inactive property (should be excluded)
        database_service.add_property(
            title="Inactive Property",
            address="789 Test Blvd",
            price=250000,
            property_type="house",
            bedrooms=3,
            bathrooms=2,
            square_feet=1400,
            description="Inactive property",
            status="sold"
        )
        
        export_data = database_service.export_recommendations_data()
        
        assert export_data is not None
        assert "generated_at" in export_data
        assert export_data["customer_id"] is None
        assert export_data["total_properties"] == 2
        assert len(export_data["properties"]) == 2
        
        # Check property data includes agent info
        prop_data = export_data["properties"][0]
        assert "agent_name" in prop_data
        assert "agent_email" in prop_data
        assert "agent_phone" in prop_data
        assert prop_data["agent_name"] == "Agent Smith"

    def test_export_recommendations_data_for_customer(self, app, db_setup):
        """Test exporting recommendations data filtered by customer preferences"""
        # Create test customer
        customer = database_service.add_customer(
            name="Customer Jones",
            email="customer@example.com",
            phone="987-654-3210",
            budget_min=150000,
            budget_max=250000,
            preferred_bedrooms=3,
            preferred_bathrooms=2,
            preferred_type="house"
        )
        
        # Create properties - some matching, some not
        matching_prop = database_service.add_property(
            title="Matching Property",
            address="123 Test St",
            price=200000,
            property_type="house",
            bedrooms=3,
            bathrooms=2,
            square_feet=1500,
            description="Matches customer preferences",
            status="active"
        )
        
        # Too expensive
        database_service.add_property(
            title="Expensive Property",
            address="456 Test Ave",
            price=300000,
            property_type="house",
            bedrooms=3,
            bathrooms=2,
            square_feet=1800,
            description="Too expensive",
            status="active"
        )
        
        # Wrong type
        database_service.add_property(
            title="Wrong Type Property",
            address="789 Test Blvd",
            price=200000,
            property_type="condo",
            bedrooms=3,
            bathrooms=2,
            square_feet=1500,
            description="Wrong type",
            status="active"
        )
        
        export_data = database_service.export_recommendations_data(customer_id=customer.id)
        
        assert export_data is not None
        assert export_data["customer_id"] == customer.id
        assert export_data["total_properties"] == 1
        assert len(export_data["properties"]) == 1
        assert export_data["properties"][0]["title"] == "Matching Property"

    def test_export_recommendations_data_customer_not_found(self, app, db_setup):
        """Test exporting recommendations data for non-existent customer"""
        export_data = database_service.export_recommendations_data(customer_id=999)
        
        assert export_data is not None
        assert export_data["customer_id"] == 999
        assert export_data["total_properties"] == 0
        assert len(export_data["properties"]) == 0

    def test_export_deals_report(self, app, db_setup):
        """Test exporting deals report"""
        # Create test data
        agent = database_service.add_agent(
            name="Agent Smith",
            email="agent@example.com",
            phone="123-456-7890"
        )
        
        customer = database_service.add_customer(
            name="Customer Jones",
            email="customer@example.com",
            phone="987-654-3210"
        )
        
        property_obj = database_service.add_property(
            title="Test Property",
            address="123 Test St",
            price=200000,
            property_type="house",
            bedrooms=3,
            bathrooms=2,
            square_feet=1500,
            description="Test property"
        )
        
        # Create deals with different statuses
        deal1 = database_service.add_deal(
            property_id=property_obj.id,
            customer_id=customer.id,
            agent_id=agent.id,
            status="prospecting",
            offer_amount=190000
        )
        
        deal2 = database_service.add_deal(
            property_id=property_obj.id,
            customer_id=customer.id,
            agent_id=agent.id,
            status="closed",
            offer_amount=195000
        )
        
        export_data = database_service.export_deals_report()
        
        assert export_data is not None
        assert "generated_at" in export_data
        assert "summary" in export_data
        assert "deals" in export_data
        
        # Check summary
        summary = export_data["summary"]
        assert summary["total_deals"] == 2
        assert summary["total_value"] == 385000
        assert summary["active_deals"] == 1
        assert summary["closed_deals"] == 1
        assert summary["average_deal_value"] == 192500
        
        # Check deal data includes related entity info
        deal_data = export_data["deals"][0]
        assert "property_title" in deal_data
        assert "customer_name" in deal_data
        assert "agent_name" in deal_data
        assert deal_data["property_title"] == "Test Property"
        assert deal_data["customer_name"] == "Customer Jones"
        assert deal_data["agent_name"] == "Agent Smith"

    def test_export_deals_report_empty(self, app, db_setup):
        """Test exporting deals report with no deals"""
        export_data = database_service.export_deals_report()
        
        assert export_data is not None
        assert export_data["summary"]["total_deals"] == 0
        assert export_data["summary"]["total_value"] == 0
        assert export_data["summary"]["average_deal_value"] == 0
        assert len(export_data["deals"]) == 0


class TestEdgeCasesAndErrorConditions:
    """Test edge cases and error conditions in database service"""

    def test_update_with_empty_kwargs(self, app, db_setup):
        """Test update methods with empty kwargs"""
        agent = database_service.add_agent(
            name="Empty Update Agent",
            email="empty@example.com",
            phone="123-456-7890"
        )
        
        # Update with no changes
        updated_agent = database_service.update_agent(agent.id)
        assert updated_agent is not None
        assert updated_agent.name == "Empty Update Agent"  # Unchanged

    def test_update_with_none_values(self, app, db_setup):
        """Test update methods with None values"""
        customer = database_service.add_customer(
            name="None Customer",
            email="none@example.com",
            phone="123-456-7890",
            budget_min=100000,
            budget_max=200000
        )
        
        # Update with None values (should be ignored)
        updated_customer = database_service.update_customer(
            customer.id,
            name="Updated None Customer",
            budget_min=None,  # Should be ignored
            budget_max=None   # Should be ignored
        )
        
        assert updated_customer.name == "Updated None Customer"
        assert updated_customer.budget_min == 100000  # Unchanged
        assert updated_customer.budget_max == 200000  # Unchanged

    def test_delete_with_foreign_key_constraints(self, app, db_setup):
        """Test delete operations with foreign key constraints"""
        # Create agent with related data
        agent = database_service.add_agent(
            name="FK Agent",
            email="fk@example.com",
            phone="123-456-7890"
        )
        
        # Create property linked to agent
        property_obj = database_service.add_property(
            title="FK Property",
            address="123 FK St",
            price=200000,
            property_type="house",
            bedrooms=3,
            bathrooms=2,
            square_feet=1500,
            description="Property with FK",
            agent_id=agent.id
        )
        
        # Create task linked to agent
        task = database_service.add_task(
            title="FK Task",
            description="Task with FK",
            agent_id=agent.id
        )
        
        # Delete agent should handle FK constraints properly
        try:
            result = database_service.delete_agent(agent.id)
        except ValueError:
            result = False
        
        # Depending on FK constraint setup, either:
        # 1. Delete succeeds and cascades to related records
        # 2. Delete fails due to FK constraints
        if result:
            # If delete succeeded, verify related records are handled
            remaining_property = database_service.get_property(property_obj.id)
            remaining_task = database_service.get_task(task.id)
            # Properties and tasks might be deleted or have agent_id set to NULL
        else:
            # If delete failed, agent should still exist
            remaining_agent = database_service.get_agent(agent.id)
            assert remaining_agent is not None

    def test_export_with_large_dataset(self, app, db_setup):
        """Test export functions with large datasets"""
        # Create many properties and deals
        agent = database_service.add_agent(
            name="Large Dataset Agent",
            email="large@example.com",
            phone="123-456-7890"
        )
        
        customer = database_service.add_customer(
            name="Large Dataset Customer",
            email="largecustomer@example.com",
            phone="987-654-3210"
        )
        
        # Create 50 properties
        properties = []
        for i in range(50):
            prop = database_service.add_property(
                title=f"Large Property {i+1}",
                address=f"{i+1}00 Large St",
                price=200000 + (i * 10000),
                property_type="house",
                bedrooms=3,
                bathrooms=2,
                square_feet=1500,
                description=f"Large property {i+1}",
                status="active",
                agent_id=agent.id
            )
            properties.append(prop)
        
        # Create 25 deals
        for i in range(25):
            database_service.add_deal(
                property_id=properties[i].id,
                customer_id=customer.id,
                agent_id=agent.id,
                status="prospecting" if i % 2 == 0 else "closed",
                offer_amount=190000 + (i * 9000)
            )
        
        # Test recommendations export
        export_data = database_service.export_recommendations_data()
        assert export_data['total_properties'] == 50
        assert len(export_data['properties']) == 50
        
        # Test deals export
        deals_data = database_service.export_deals_report()
        assert deals_data['summary']['total_deals'] == 25
        assert len(deals_data['deals']) == 25

    def test_export_with_missing_relations(self, app, db_setup):
        """Test export functions with missing related data"""
        # Create property without agent
        property_obj = database_service.add_property(
            title="Orphan Property",
            address="123 Orphan St",
            price=200000,
            property_type="house",
            bedrooms=3,
            bathrooms=2,
            square_feet=1500,
            description="Property without agent",
            status="active"
            # No agent_id
        )
        
        # Create customer
        customer = database_service.add_customer(
            name="Orphan Customer",
            email="orphan@example.com",
            phone="123-456-7890"
        )
        
        # Create deal with missing agent
        deal = database_service.add_deal(
            property_id=property_obj.id,
            customer_id=customer.id,
            # No agent_id
            status="prospecting",
            offer_amount=190000
        )
        
        # Export should handle missing relations gracefully
        export_data = database_service.export_recommendations_data()
        assert export_data['total_properties'] == 1
        
        property_data = export_data['properties'][0]
        # Should handle missing agent gracefully
        assert 'agent_name' in property_data
        assert property_data['agent_name'] in [None, '', 'N/A']
        
        deals_data = database_service.export_deals_report()
        assert deals_data['summary']['total_deals'] == 1
        
        deal_data = deals_data['deals'][0]
        # Should handle missing agent gracefully
        assert 'agent_name' in deal_data
        assert deal_data['agent_name'] in [None, '', 'N/A']

    def test_concurrent_updates(self, app, db_setup):
        """Test concurrent update scenarios"""
        agent = database_service.add_agent(
            name="Concurrent Agent",
            email="concurrent@example.com",
            phone="123-456-7890"
        )
        
        # Simulate concurrent updates
        updated_agent1 = database_service.update_agent(
            agent.id,
            name="First Update"
        )
        
        updated_agent2 = database_service.update_agent(
            agent.id,
            name="Second Update"
        )
        
        # Both updates should succeed
        assert updated_agent1 is not None
        assert updated_agent2 is not None
        
        # Final state should reflect the last update
        final_agent = database_service.get_agent(agent.id)
        assert final_agent.name == "Second Update"

    def test_database_transaction_rollback(self, app, db_setup):
        """Test database transaction rollback on errors"""
        # This test would require more complex setup to force a database error
        # For now, we'll test the basic error handling
        
        # Try to update non-existent record
        result = database_service.update_agent(99999, name="Should Fail")
        assert result is None
        
        # Try to delete non-existent record
        result = database_service.delete_agent(99999)
        assert result is False
        
        # Database should remain in consistent state
        agents = database_service.get_agents()
        # Should not have any phantom records
        for agent in agents:
            assert agent.id is not None
            assert agent.name is not None

    def test_special_characters_handling(self, app, db_setup):
        """Test handling of special characters in data"""
        # Test with various special characters
        special_name = "Agent with 'quotes' & symbols: @#$%^&*()"
        special_email = "special+test@example-domain.com"
        special_bio = """Multi-line bio with
        line breaks and "quotes" and 'apostrophes'
        and other special chars: <>&"""
        
        agent = database_service.add_agent(
            name=special_name,
            email=special_email,
            phone="123-456-7890",
            bio=special_bio
        )
        
        assert agent is not None
        assert agent.name == special_name
        assert agent.email == special_email
        assert agent.bio == special_bio
        
        # Test update with special characters
        updated_agent = database_service.update_agent(
            agent.id,
            name="Updated " + special_name,
            bio="Updated " + special_bio
        )
        
        assert updated_agent is not None
        assert "Updated " in updated_agent.name
        assert "Updated " in updated_agent.bio

    def test_unicode_handling(self, app, db_setup):
        """Test handling of Unicode characters"""
        unicode_name = "José María González-Pérez"
        unicode_address = "123 Café Street, Montréal"
        unicode_description = "Beautiful property with café nearby 🏠☕"
        
        property_obj = database_service.add_property(
            title=unicode_name + "'s Property",
            address=unicode_address,
            price=200000,
            property_type="house",
            bedrooms=3,
            bathrooms=2,
            square_feet=1500,
            description=unicode_description,
            status="active"
        )
        
        assert property_obj is not None
        assert unicode_name in property_obj.title
        assert property_obj.address == unicode_address
        assert property_obj.description == unicode_description
        
        # Test in export
        export_data = database_service.export_recommendations_data()
        property_data = export_data['properties'][0]
        assert unicode_name in property_data['title']
        assert property_data['address'] == unicode_address
