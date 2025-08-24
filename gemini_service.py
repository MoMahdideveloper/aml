import os
import logging
from typing import List, Dict, Any
from google import genai
from google.genai import types
from models import Property, Customer
from vector_service import vector_service

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

    def get_property_recommendations(self, customer: Customer, properties: List[Property]) -> List[Dict[str, Any]]:
        """
        Get AI-powered property recommendations using vector search with semantic matching
        """
        try:
            self.logger.info(f"Getting recommendations for customer {customer.name} from {len(properties)} properties")
            
            # If no client available, use fallback immediately
            if not self.client:
                self.logger.info("No Gemini client available, using fallback recommendations")
                return self._create_fallback_recommendations(customer, properties[:10])
            
            # Use vector service for semantic search
            vector_recommendations = vector_service.search_properties(
                customer=customer,
                properties=properties,
                top_k=min(10, len(properties))
            )
            
            if vector_recommendations:
                # Convert vector service format to expected format
                formatted_recommendations = []
                for rec in vector_recommendations:
                    # Create analysis text from match reasons
                    analysis_parts = [f"Match Score: {rec['hybrid_score']:.1f}/100"]
                    analysis_parts.extend(f"• {reason}" for reason in rec['match_reasons'])
                    
                    formatted_recommendations.append({
                        'property': rec['property'],
                        'analysis': '\n'.join(analysis_parts),
                        'match_score': int(rec['hybrid_score'])
                    })
                
                self.logger.info(f"Vector search returned {len(formatted_recommendations)} recommendations")
                return formatted_recommendations
            else:
                self.logger.warning("Vector search failed, using fallback recommendations")
                return self._create_fallback_recommendations(customer, properties[:10])

        except Exception as e:
            self.logger.error(f"Error getting property recommendations: {e}")
            # Return fallback recommendations based on simple criteria
            return self._create_fallback_recommendations(customer, properties[:10])

    def _parse_recommendations(self, ai_response: str, properties: List[Property]) -> List[Dict[str, Any]]:
        """
        Parse the AI response and create structured recommendations
        """
        recommendations = []
        
        # Parse the simplified format: "Property [ID]: Score [X]/100 - [Brief reasoning]"
        lines = ai_response.split('\n')
        
        for line in lines:
            line = line.strip()
            if 'Property' in line and ':' in line:
                try:
                    # Extract property ID
                    if 'Property ' in line:
                        id_part = line.split('Property ')[1].split(':')[0].strip()
                        property_id = int(id_part)
                        
                        # Find the property
                        prop = next((p for p in properties if p.id == property_id), None)
                        if prop:
                            # Extract the analysis text
                            analysis_text = line.split(':', 1)[1].strip()
                            
                            recommendations.append({
                                'property': prop,
                                'analysis': analysis_text,
                                'match_score': self._extract_score(analysis_text)
                            })
                except Exception as e:
                    self.logger.warning(f"Could not parse line: {line} - {e}")
                    continue
        
        # If no recommendations were parsed, try fallback parsing
        if not recommendations and properties:
            self.logger.info("Using fallback parsing for AI response")
            # Split response into chunks and match with properties
            chunks = ai_response.split('\n\n')
            for i, chunk in enumerate(chunks):
                if i < len(properties) and chunk.strip():
                    recommendations.append({
                        'property': properties[i],
                        'analysis': chunk.strip(),
                        'match_score': self._extract_score(chunk)
                    })
        
        # Sort by match score (highest first)
        recommendations.sort(key=lambda x: x['match_score'], reverse=True)
        
        return recommendations

    def _create_fallback_recommendations(self, customer: Customer, properties: List[Property]) -> List[Dict[str, Any]]:
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
            
            analysis = f"Match Score: {score}/100\n" + "\n".join(f"• {reason}" for reason in reasons)
            if not reasons:
                analysis = "This property may not fully match your preferences, but could still be worth considering."
            
            recommendations.append({
                'property': prop,
                'analysis': analysis,
                'match_score': score
            })
        
        # Sort by match score (highest first)
        recommendations.sort(key=lambda x: x['match_score'], reverse=True)
        
        return recommendations

    def _extract_score(self, analysis: str) -> int:
        """
        Extract match score from analysis text
        """
        # Look for patterns like "score: 85" or "match score: 92"
        import re
        score_patterns = [
            r'score[:\s]+(\d+)',
            r'match[:\s]+(\d+)',
            r'rating[:\s]+(\d+)',
            r'(\d+)[:/]100',
            r'(\d+)%'
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
                return property_data.get('description', '')
                
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
                model="gemini-2.5-flash",
                contents=prompt
            )

            return response.text if response.text else property_data.get('description', '')

        except Exception as e:
            self.logger.error(f"Error generating property description: {e}")
            return property_data.get('description', '')

    def analyze_market_trends(self, properties: List[Property]) -> str:
        """
        Analyze market trends based on available properties
        """
        try:
            # If no client available, return basic analysis
            if not self.client:
                return "Market analysis unavailable - AI service not configured."
                
            # Prepare property data for analysis
            property_summary = []
            for prop in properties:
                property_summary.append(f"{prop.property_type}: ${prop.price:,} - {prop.bedrooms}bed/{prop.bathrooms}bath - {prop.square_feet}sqft")

            properties_text = "\n".join(property_summary)

            prompt = f"""
            Analyze the following real estate properties and provide market insights:

            Properties:
            {properties_text}

            Provide analysis on:
            1. Average pricing by property type
            2. Price per square foot trends
            3. Most common property configurations
            4. Market observations and trends
            5. Investment opportunities

            Keep the analysis professional and data-driven, suitable for real estate professionals.
            """

            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )

            return response.text if response.text else "Market analysis unavailable at this time."

        except Exception as e:
            self.logger.error(f"Error analyzing market trends: {e}")
            return "Market analysis unavailable due to technical issues."

# Global Gemini service instance
gemini_service = GeminiService()
