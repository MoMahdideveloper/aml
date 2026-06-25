
import pytest
from unittest.mock import Mock, patch
from flask import json
import io
from services.database_service import DatabaseService
from sqlalchemy_models import PropertyAIHistory

def test_extract_property_success(client):
    """Test successful property extraction from image"""
    with patch('views.properties.gemini_service') as mock_gemini:
        # Mock extracted data
        mock_data = {
            "title": "AI Extracted House",
            "price": 500000,
            "bedrooms": 4,
            "bathrooms": 3
        }
        mock_gemini.extract_property_from_image.return_value = mock_data
        
        # Create dummy image
        data = {
            'image': (io.BytesIO(b"fake_image_data"), 'test.jpg')
        }
        
        response = client.post(
            '/properties/extract-from-image',
            data=data,
            content_type='multipart/form-data'
        )
        
        assert response.status_code == 200
        json_data = json.loads(response.data)
        assert json_data['title'] == "AI Extracted House"
        assert json_data['price'] == 500000
        
        # Verify service called correctly
        mock_gemini.extract_property_from_image.assert_called_once()


def test_extract_property_no_file(client):
    """Test extraction with no file uploaded"""
    response = client.post(
        '/properties/extract-from-image',
        data={},
        content_type='multipart/form-data'
    )
    
    assert response.status_code == 400
    json_data = json.loads(response.data)
    assert "error" in json_data


def test_extract_property_error(client):
    """Test extraction when service fails"""
    with patch('views.properties.gemini_service') as mock_gemini:
        mock_gemini.extract_property_from_image.side_effect = Exception("AI Error")
        
        data = {
            'image': (io.BytesIO(b"data"), 'test.jpg')
        }
        
        response = client.post(
            '/properties/extract-from-image',
            data=data,
            content_type='multipart/form-data'
        )
        
        assert response.status_code == 500
        json_data = json.loads(response.data)
        assert "error" in json_data


def test_add_property_with_ai_flag(client):
    """Test adding property with is_ai_extracted flag via View"""
    with patch('views.properties.database_service') as mock_db, \
         patch('views.properties.PropertyForm') as mock_form_cls:
        
        # Mock form validation
        mock_form = Mock()
        mock_form.validate_on_submit.return_value = True
        
        # Setup form data
        mock_form.title.data = "AI House View Test"
        mock_form.address.data = "123 View St"
        mock_form.listing_type.data = "sale"
        mock_form.sale_price.data = 100000
        mock_form.property_type.data = "house"
        mock_form.bedrooms.data = 3
        mock_form.bathrooms.data = 2
        mock_form.square_feet.data = 1500
        mock_form.description.data = "Desc"
        mock_form.agent_id.data = None
        mock_form.year_built.data = 2020
        mock_form.parking_spaces.data = 2
        mock_form.floors.data = 1
        mock_form.units.data = 1
        mock_form.property_condition.data = "good"
        mock_form.heating_type.data = "gas"
        mock_form.cooling_type.data = "ac"
        mock_form.property_features.data = ""
        mock_form.neighborhood.data = "Hood"
        mock_form.property_category.data = "residential"
        mock_form.image.data = None
        mock_form.latitude.data = 0
        mock_form.longitude.data = 0
        mock_form.document_type.data = None
        mock_form.floor_number.data = None
        mock_form.built_area.data = None
        mock_form.land_area.data = None
        mock_form.floor_covering.data = None
        mock_form.facade_type.data = None
        mock_form.wall_covering.data = None
        mock_form.cabinet_type.data = None
        mock_form.property_direction.data = None
        mock_form.is_exchangeable.data = False
        mock_form.boundary_width.data = None
        mock_form.density.data = None
        mock_form.commercial_status.data = None
        mock_form.usage_type.data = None
        mock_form.ceiling_count.data = None
        mock_form.permit_ceiling.data = None
        mock_form.property_length.data = None
        mock_form.property_height.data = None
        mock_form.price_per_meter.data = None
        mock_form.custom_fields.data = ""
        
        # Critical flag checks
        mock_form.is_ai_extracted.data = "true" 
        mock_form.ai_raw_data.data = '{"mock": "data"}'

        mock_form_cls.return_value = mock_form
        
        response = client.post('/properties/add')
        
        assert response.status_code == 302
        
        # Check if database_service.add_property was called with is_ai_extracted
        assert mock_db.add_property.called
        call_args = mock_db.add_property.call_args
        
        # Verify arguments passed to service
        assert call_args.kwargs.get('is_ai_extracted') is True
        assert call_args.kwargs.get('ai_raw_data') == '{"mock": "data"}'


def test_database_service_saves_ai_history(app, db_setup):
    """Test that DatabaseService actually saves history when flag is set"""
    service = DatabaseService()
    
    with app.app_context():
        # Add property with AI flag
        prop = service.add_property(
            title="AI DB Service Test",
            address="123 Database Way",
            price=250000,
            property_type="house",
            bedrooms=3,
            bathrooms=2,
            square_feet=2000,
            description="Test Desc",
            is_ai_extracted=True,
            ai_raw_data='{"original_price": 250000, "source": "ai"}'
        )
        
        assert prop.id is not None
        
        # Verify history record created
        history = PropertyAIHistory.query.filter_by(property_id=prop.id).first()
        assert history is not None
        assert history.raw_data == '{"original_price": 250000, "source": "ai"}'
        assert history.user_note == "Initial AI Extraction"
