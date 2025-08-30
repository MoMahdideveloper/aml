import os
import logging
import json
import re
from typing import List, Dict, Any
from google import genai
from google.genai import types
from sqlalchemy_models import Property, Customer
from vector_service import vector_service
from schemas import PropertyAI, CustomerAI

JSON_INSTRUCTIONS = """
Return ONLY valid JSON. Do not include backticks or prose.
Numbers must be numbers. Booleans must be booleans. Use null if unknown.
"""

PROPERTY_SCHEMA_HINT = {
    "title": "string or null",
    "address": "string or null",
    "price": 0,
    "property_type": "string or null",
    "bedrooms": 0,
    "bathrooms": 0,
    "square_feet": 0,
    "description": "string or null",
    "status": "active|pending|sold|null",
    "agent_id": 0,
    "year_built": 0,
    "parking_spaces": 0,
    "floors": 1,
    "units": 1,
    "property_condition": "excellent|good|fair|needs_renovation|null",
    "heating_type": "string or null",
    "cooling_type": "string or null",
    "rental_price": 0,
    "property_features": ["comma, separated, items"],
    "neighborhood": "string or null",
    "property_category": "residential|commercial|null",
    "listing_type": "sale|rental|null",
    "rahn": 0,
    "ejare": 0,
}

CUSTOMER_SCHEMA_HINT = {
    "name": "string or null",
    "email": "string or null",
    "phone": "string or null",
    "preferences": "string or null",
    "budget_min": 0,
    "budget_max": 0,
    "desired_neighborhoods": ["comma, separated"],
    "desired_property_type": "string or null",
    "bedrooms_min": 0,
    "bathrooms_min": 0,
}


class GeminiService:
    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key or api_key == "default_key":
            # Use a mock/fallback mode instead of failing
            self.client = None
            self.logger = logging.getLogger(__name__)
            self.logger.warning("GEMINI_API_KEY not found, running in fallback mode")
        else:
            self.client = genai.Client(api_key=api_key)
            self.logger = logging.getLogger(__name__)

    def get_property_recommendations(
        self, customer: Customer, properties: List[Property]
    ) -> List[Dict[str, Any]]:
        """
        Get AI-powered property recommendations using vector search with semantic matching
        """
        try:
            self.logger.info(
                f"Getting recommendations for customer {customer.name} from {len(properties)} properties"
            )

            # If no client available, use fallback immediately
            if not self.client:
                self.logger.info("No Gemini client available, using fallback recommendations")
                return self._create_fallback_recommendations(customer, properties[:10])

            # Use vector service for semantic search
            vector_recommendations = vector_service.search_properties(
                customer=customer, properties=properties, top_k=min(10, len(properties))
            )

            if vector_recommendations:
                # Convert vector service format to expected format
                formatted_recommendations = []
                for rec in vector_recommendations:
                    # Create analysis text from match reasons
                    analysis_parts = [f"Match Score: {rec['hybrid_score']:.1f}/100"]
                    analysis_parts.extend(f"• {reason}" for reason in rec["match_reasons"])

                    formatted_recommendations.append(
                        {
                            "property": rec["property"],
                            "analysis": "\n".join(analysis_parts),
                            "match_score": int(rec["hybrid_score"]),
                        }
                    )

                self.logger.info(
                    f"Vector search returned {len(formatted_recommendations)} recommendations"
                )
                return formatted_recommendations
            else:
                self.logger.warning("Vector search failed, using fallback recommendations")
                return self._create_fallback_recommendations(customer, properties[:10])

        except Exception as e:
            self.logger.error(f"Error getting property recommendations: {e}")
            # Return fallback recommendations based on simple criteria
            return self._create_fallback_recommendations(customer, properties[:10])

    def _parse_recommendations(
        self, ai_response: str, properties: List[Property]
    ) -> List[Dict[str, Any]]:
        """
        Parse the AI response and create structured recommendations
        """
        recommendations = []

        # Parse the simplified format: "Property [ID]: Score [X]/100 - [Brief reasoning]"
        lines = ai_response.split("\n")

        for line in lines:
            line = line.strip()
            if "Property" in line and ":" in line:
                try:
                    # Extract property ID
                    if "Property " in line:
                        id_part = line.split("Property ")[1].split(":")[0].strip()
                        property_id = int(id_part)

                        # Find the property
                        prop = next((p for p in properties if p.id == property_id), None)
                        if prop:
                            # Extract the analysis text
                            analysis_text = line.split(":", 1)[1].strip()

                            recommendations.append(
                                {
                                    "property": prop,
                                    "analysis": analysis_text,
                                    "match_score": self._extract_score(analysis_text),
                                }
                            )
                except Exception as e:
                    self.logger.warning(f"Could not parse line: {line} - {e}")
                    continue

        # If no recommendations were parsed, try fallback parsing
        if not recommendations and properties:
            self.logger.info("Using fallback parsing for AI response")
            # Split response into chunks and match with properties
            chunks = ai_response.split("\n\n")
            for i, chunk in enumerate(chunks):
                if i < len(properties) and chunk.strip():
                    recommendations.append(
                        {
                            "property": properties[i],
                            "analysis": chunk.strip(),
                            "match_score": self._extract_score(chunk),
                        }
                    )

        # Sort by match score (highest first)
        recommendations.sort(key=lambda x: x["match_score"], reverse=True)

        return recommendations

    def _create_fallback_recommendations(
        self, customer: Customer, properties: List[Property]
    ) -> List[Dict[str, Any]]:
        """
        Create basic recommendations when AI is unavailable
        """
        recommendations = []

        for prop in properties:
            # Simple scoring based on basic criteria
            score = 0
            reasons = []

            # Budget match (40 points max)
            if customer.budget_min <= prop.price <= customer.budget_max:
                score += 40
                reasons.append("Within budget range")
            elif prop.price <= customer.budget_max:
                score += 20
                reasons.append("Slightly below budget")

            # Bedroom match (20 points max)
            if prop.bedrooms == customer.preferred_bedrooms:
                score += 20
                reasons.append("Matches bedroom preference")
            elif abs(prop.bedrooms - customer.preferred_bedrooms) <= 1:
                score += 10
                reasons.append("Close to bedroom preference")

            # Bathroom match (20 points max)
            if prop.bathrooms >= customer.preferred_bathrooms:
                score += 20
                reasons.append("Meets bathroom needs")
            elif prop.bathrooms >= customer.preferred_bathrooms - 0.5:
                score += 10
                reasons.append("Close to bathroom preference")

            # Property type match (20 points max)
            if prop.property_type.lower() == customer.preferred_type.lower():
                score += 20
                reasons.append("Matches property type preference")

            analysis = f"Match Score: {score}/100\n" + "\n".join(
                f"• {reason}" for reason in reasons
            )
            if not reasons:
                analysis = "This property may not fully match your preferences, but could still be worth considering."

            recommendations.append({"property": prop, "analysis": analysis, "match_score": score})

        # Sort by match score (highest first)
        recommendations.sort(key=lambda x: x["match_score"], reverse=True)

        return recommendations

    def _extract_score(self, analysis: str) -> int:
        """
        Extract match score from analysis text
        """
        # Look for patterns like "score: 85" or "match score: 92"
        import re

        score_patterns = [
            r"score[:\s]+(\d+)",
            r"match[:\s]+(\d+)",
            r"rating[:\s]+(\d+)",
            r"(\d+)[:/]100",
            r"(\d+)%",
        ]

        for pattern in score_patterns:
            match = re.search(pattern, analysis.lower())
            if match:
                score = int(match.group(1))
                return min(100, max(0, score))  # Ensure score is between 0-100

        # Default score if none found
        return 50

    def generate_property_description(self, property_data: Dict[str, Any]) -> str:
        """
        Generate an enhanced property description using AI
        """
        try:
            # If no client available, return original description
            if not self.client:
                return property_data.get("description", "")

            prompt = f"""
            Create an engaging and professional property description based on the following details:
            
            Property Type: {property_data.get('property_type', '')}
            Address: {property_data.get('address', '')}
            Price: ${property_data.get('price', 0):,}
            Bedrooms: {property_data.get('bedrooms', 0)}
            Bathrooms: {property_data.get('bathrooms', 0)}
            Square Feet: {property_data.get('square_feet', 0):,}
            Current Description: {property_data.get('description', '')}
            
            Create a compelling property description that:
            1. Highlights key features and selling points
            2. Uses professional real estate language
            3. Emphasizes the lifestyle and benefits
            4. Is engaging but not overly promotional
            5. Is about 2-3 paragraphs long
            
            Make it sound appealing to potential buyers while being accurate and professional.
            """

            response = self.client.models.generate_content(
                model="gemini-2.5-flash", contents=prompt
            )

            return response.text if response.text else property_data.get("description", "")

        except Exception as e:
            self.logger.error(f"Error generating property description: {e}")
            return property_data.get("description", "")

    def analyze_market_trends(self, properties: List[Property]) -> str:
        """
        Analyze market trends based on available properties with timeout handling
        """
        try:
            # If no client available or no properties, return manual analysis
            if not self.client or not properties:
                return self._generate_manual_market_analysis(properties)

            # Use a shorter, more focused prompt to reduce API call time
            property_summary = []
            for prop in properties[:20]:  # Limit to first 20 properties to reduce processing time
                property_summary.append(
                    f"{prop.property_type}: ${prop.price:,} - {prop.bedrooms}bed/{prop.bathrooms}bath - {prop.square_feet}sqft"
                )

            properties_text = "\n".join(property_summary)

            # Shorter, more focused prompt
            prompt = f"""
            Analyze these {len(property_summary)} real estate properties. Be concise and specific:

            {properties_text}

            Provide a brief analysis with:
            1. Average prices by property type
            2. Price per square foot ranges
            3. Most common configurations
            4. Key market insights
            5. Investment recommendations

            Keep response under 500 words with specific numbers and percentages.
            """

            # Add timeout to the API call
            import signal
            import time

            def timeout_handler(signum, frame):
                raise TimeoutError("API call timed out")

            # Set a 15-second timeout for the API call
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(15)

            try:
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash", contents=prompt
                )
                signal.alarm(0)  # Cancel the alarm

                if response.text:
                    return response.text
                else:
                    return self._generate_manual_market_analysis(properties)

            except TimeoutError:
                signal.alarm(0)  # Cancel the alarm
                self.logger.warning("Gemini API call timed out, using manual analysis")
                return self._generate_manual_market_analysis(properties)

        except Exception as e:
            self.logger.error(f"Error analyzing market trends: {e}")
            return self._generate_manual_market_analysis(properties)

    def _generate_manual_market_analysis(self, properties: List[Property]) -> str:
        """
        Generate a manual market analysis when AI is unavailable
        """
        if not properties:
            return """
            **Market Analysis**
            
            No properties available for analysis. Add some property listings to get market insights.
            """

        # Calculate basic statistics
        total_properties = len(properties)

        # Group by property type
        type_stats = {}
        for prop in properties:
            prop_type = prop.property_type
            if prop_type not in type_stats:
                type_stats[prop_type] = {"prices": [], "sqft": [], "bedrooms": [], "count": 0}

            type_stats[prop_type]["prices"].append(prop.price)
            type_stats[prop_type]["sqft"].append(prop.square_feet)
            type_stats[prop_type]["bedrooms"].append(prop.bedrooms)
            type_stats[prop_type]["count"] += 1

        # Overall statistics
        all_prices = [p.price for p in properties if p.price > 0]
        all_sqft = [p.square_feet for p in properties if p.square_feet > 0]

        avg_price = sum(all_prices) / len(all_prices) if all_prices else 0
        min_price = min(all_prices) if all_prices else 0
        max_price = max(all_prices) if all_prices else 0

        avg_sqft = sum(all_sqft) / len(all_sqft) if all_sqft else 0
        avg_price_per_sqft = avg_price / avg_sqft if avg_sqft > 0 else 0

        # Most common bedroom count
        bedroom_counts = {}
        for prop in properties:
            bedrooms = prop.bedrooms
            bedroom_counts[bedrooms] = bedroom_counts.get(bedrooms, 0) + 1
        most_common_bedrooms = (
            max(bedroom_counts.items(), key=lambda x: x[1])[0] if bedroom_counts else 0
        )

        analysis = f"""
**MARKET ANALYSIS REPORT**

**OVERVIEW:**
• Total Properties Analyzed: {total_properties}
• Average Price: ${avg_price:,.0f}
• Price Range: ${min_price:,.0f} - ${max_price:,.0f}
• Average Size: {avg_sqft:,.0f} sq ft
• Average Price/Sq Ft: ${avg_price_per_sqft:.0f}

**BY PROPERTY TYPE:**
"""

        for prop_type, stats in type_stats.items():
            if stats["prices"]:
                type_avg_price = sum(stats["prices"]) / len(stats["prices"])
                type_avg_sqft = sum(stats["sqft"]) / len(stats["sqft"]) if stats["sqft"] else 0
                type_price_per_sqft = type_avg_price / type_avg_sqft if type_avg_sqft > 0 else 0

                analysis += f"""
• {prop_type.title()}: {stats['count']} properties
  - Average Price: ${type_avg_price:,.0f}
  - Average Size: {type_avg_sqft:,.0f} sq ft
  - Price/Sq Ft: ${type_price_per_sqft:.0f}
"""

        analysis += f"""

**MARKET INSIGHTS:**
• Most Common Configuration: {most_common_bedrooms} bedrooms
• Property Type Distribution: {', '.join([f"{k}: {v['count']}" for k, v in type_stats.items()])}

**INVESTMENT OPPORTUNITIES:**
• Properties under ${avg_price * 0.8:,.0f} may offer good value
• {most_common_bedrooms}-bedroom properties are in high demand
• Average price per sq ft of ${avg_price_per_sqft:.0f} can guide pricing decisions

**RECOMMENDATIONS:**
1. Focus on {most_common_bedrooms}-bedroom properties for broader appeal
2. Consider properties priced below ${avg_price:,.0f} for potential value
3. Target price per sq ft around ${avg_price_per_sqft:.0f} for competitive pricing

*Note: This analysis is based on your current property database. For more detailed AI-powered insights, ensure your Gemini API is properly configured.*
"""

        return analysis

    def _extract_json(self, prompt: str) -> dict:
        """Extract JSON from Gemini response with fallback handling"""
        if not self.client:
            # Fallback: try to find key/value pairs as a naive baseline
            return {}

        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash-exp", contents=prompt
            )
            text = (getattr(response, "text", None) or "").strip()
            # Remove code fences if any
            text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
            return json.loads(text)
        except Exception as e:
            self.logger.warning(f"Failed to parse strict JSON: {e}")
            return {}

    def extract_property_from_text(self, blob: str) -> dict:
        """Extract property information from free text using AI"""
        prompt = f"""
You are an information extraction assistant for real estate listings.
Extract all possible fields from the text below and output a single JSON object
matching this example schema (values can be null when unknown):

{json.dumps(PROPERTY_SCHEMA_HINT, ensure_ascii=False, indent=2)}

{JSON_INSTRUCTIONS}

TEXT:
{blob}
"""
        data = self._extract_json(prompt)
        try:
            model = PropertyAI(**data or {})
            payload = model.dict()
            missing = [k for k, v in payload.items() if v in (None, [], "")]
            return {
                "entity": "property",
                "data": payload,
                "missing": missing,
                "confidence": 0.75 if data else 0.3,
            }
        except Exception as e:
            self.logger.error(f"Error processing property extraction: {e}")
            return {"entity": "property", "data": {}, "missing": [], "confidence": 0.0}

    def extract_customer_from_text(self, blob: str) -> dict:
        """Extract customer information from free text using AI"""
        prompt = f"""
You are an information extraction assistant for real estate customers.
Extract all possible fields from the text below and output a single JSON object
matching this example schema (values can be null when unknown):

{json.dumps(CUSTOMER_SCHEMA_HINT, ensure_ascii=False, indent=2)}

{JSON_INSTRUCTIONS}

TEXT:
{blob}
"""
        data = self._extract_json(prompt)
        try:
            model = CustomerAI(**data or {})
            payload = model.dict()
            missing = [k for k, v in payload.items() if v in (None, [], "")]
            return {
                "entity": "customer",
                "data": payload,
                "missing": missing,
                "confidence": 0.75 if data else 0.3,
            }
        except Exception as e:
            self.logger.error(f"Error processing customer extraction: {e}")
            return {"entity": "customer", "data": {}, "missing": [], "confidence": 0.0}


# Global Gemini service instance
gemini_service = GeminiService()
