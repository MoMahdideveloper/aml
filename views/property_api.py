import logging
from flask import jsonify, request
from .property_helpers import _wants_json
from property_error_handlers import handle_property_errors, validate_property_id, require_property_exists, log_property_operation
from database import db
from services.database_service import database_service
from services.vector_service import vector_service
from services.gemini_service import gemini_service
from sqlalchemy_models import ContactReveal
from error_handlers import safe_json_response

# These functions will be imported and attached to the blueprint in the main properties.py file

def reveal_contact(property_id):
    """Track when a user reveals contact info for a property"""
    property_obj = database_service.get_property(property_id)
    if not property_obj:
        return safe_json_response(message="Property not found", status=404)
    try:
        reveal = ContactReveal(
            property_id=property_id,
            viewer_ip=request.remote_addr,
        )
        db.session.add(reveal)
        db.session.commit()
        agent = property_obj.agent
        contact_info = {
            "agent_name": agent.name if agent else None,
            "agent_phone": agent.phone if agent else None,
            "agent_email": agent.email if agent else None,
        }
        return safe_json_response(data={"contact": contact_info})
    except Exception as e:
        logging.error(f"Error revealing contact for property {property_id}: {e}")
        return safe_json_response(message=str(e), status=500)


def smart_search():
    """Semantic search for properties using vector embeddings"""
    query = request.args.get("q", "")
    if not query:
        return safe_json_response(data={"properties": []})

    try:
        # Get all properties for the vector service to filter/rank
        all_properties = database_service.get_properties()

        # Use vector service to find semantic matches
        # We'll mock a Customer object to satisfy the signature if needed
        class DummyCustomer:
            def __init__(self, query):
                self.preferences = query
                self.budget_min = 0
                self.budget_max = 1000000000
                self.preferred_bedrooms = 0
                self.preferred_bathrooms = 0
                self.preferred_type = ""
                self.location_preference = ""

        dummy = DummyCustomer(query)
        results = vector_service.search_properties(dummy, all_properties, top_k=20)

        formatted_results = []
        for res in results:
            p = res["property"]
            formatted_results.append({
                "id": p.id,
                "title": p.title,
                "address": p.address,
                "price": p.price,
                "property_type": p.property_type,
                "bedrooms": p.bedrooms,
                "bathrooms": p.bathrooms,
                "square_feet": p.square_feet,
                "score": res.get("score", 0),
                "image_filename": p.image_filename
            })

        return safe_json_response(data={"properties": formatted_results})
    except Exception as e:
        logging.error(f"Smart Search failed: {e}")
        return safe_json_response(message=f"Smart Search failed: {str(e)}", status=500)


def extract_property_from_image():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if file:
        try:
            image_bytes = file.read()
            mime_type = file.mimetype or "image/jpeg"
            data = gemini_service.extract_property_from_image(image_bytes, mime_type)
            return jsonify(data)
        except Exception as e:
            logging.error(f"Image extraction error: {e}")
            return jsonify({"error": "Failed to extract data"}), 500

    return jsonify({"error": "Unknown error"}), 400


def extract_property_from_text():
    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    if not text:
        return jsonify({"error": "No text provided"}), 400

    try:
        result = gemini_service.extract_property_from_text(text)
        # extract_property_from_text returns {entity, data: {...}, missing, confidence}
        # The frontend expects a flat dict of property fields (same as image endpoint)
        data = result.get("data", {}) if isinstance(result, dict) else {}
        return jsonify(data)
    except Exception as e:
        logging.error(f"Text extraction error: {e}")
        return jsonify({"error": "Failed to extract data"}), 500