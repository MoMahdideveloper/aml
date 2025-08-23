import os
import logging
from typing import List, Dict, Any
from google import genai
from google.genai import types
from models import Property, Customer

class GeminiService:
    def __init__(self):
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", "default_key"))
        self.logger = logging.getLogger(__name__)

    def get_property_recommendations(self, customer: Customer, properties: List[Property]) -> List[Dict[str, Any]]:
        """
        Get AI-powered property recommendations for a customer based on their preferences
        """
        try:
            # Prepare customer preferences
            customer_profile = f"""
            Customer Profile:
            - Name: {customer.name}
            - Budget: ${customer.budget_min:,} - ${customer.budget_max:,}
            - Preferred Bedrooms: {customer.preferred_bedrooms}
            - Preferred Bathrooms: {customer.preferred_bathrooms}
            - Preferred Property Type: {customer.preferred_type}
            - Location Preference: {customer.location_preference}
            """

            # Prepare property data
            property_data = []
            for prop in properties:
                property_info = f"""
                Property ID: {prop.id}
                Title: {prop.title}
                Address: {prop.address}
                Price: ${prop.price:,}
                Type: {prop.property_type}
                Bedrooms: {prop.bedrooms}
                Bathrooms: {prop.bathrooms}
                Square Feet: {prop.square_feet:,}
                Description: {prop.description}
                """
                property_data.append(property_info)

            properties_text = "\n\n".join(property_data)

            prompt = f"""
            {customer_profile}

            Available Properties:
            {properties_text}

            Based on the customer's preferences and budget, analyze each property and provide recommendations.
            For each property, provide:
            1. A match score from 1-100 (100 being perfect match)
            2. Reasons why it matches or doesn't match the customer's preferences
            3. Highlight key selling points for this customer
            4. Any potential concerns or drawbacks

            Format your response as a structured analysis for each property, focusing on the best matches first.
            Be specific about how each property aligns with the customer's stated preferences.
            """

            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )

            if response.text:
                # Parse the AI response and create recommendations
                recommendations = self._parse_recommendations(response.text, properties)
                return recommendations
            else:
                self.logger.error("Empty response from Gemini API")
                return []

        except Exception as e:
            self.logger.error(f"Error getting property recommendations: {e}")
            return []

    def _parse_recommendations(self, ai_response: str, properties: List[Property]) -> List[Dict[str, Any]]:
        """
        Parse the AI response and create structured recommendations
        """
        recommendations = []
        
        # For now, create a simple structure based on the AI response
        # In a production system, you might want to use structured output from Gemini
        lines = ai_response.split('\n')
        current_property_id = None
        current_analysis = []
        
        for line in lines:
            line = line.strip()
            if 'Property ID:' in line:
                # Save previous analysis if exists
                if current_property_id and current_analysis:
                    prop = next((p for p in properties if p.id == current_property_id), None)
                    if prop:
                        recommendations.append({
                            'property': prop,
                            'analysis': '\n'.join(current_analysis),
                            'match_score': self._extract_score('\n'.join(current_analysis))
                        })
                
                # Start new property analysis
                try:
                    current_property_id = int(line.split('Property ID:')[1].strip())
                    current_analysis = []
                except:
                    current_property_id = None
            elif current_property_id and line:
                current_analysis.append(line)
        
        # Add the last property if exists
        if current_property_id and current_analysis:
            prop = next((p for p in properties if p.id == current_property_id), None)
            if prop:
                recommendations.append({
                    'property': prop,
                    'analysis': '\n'.join(current_analysis),
                    'match_score': self._extract_score('\n'.join(current_analysis))
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
