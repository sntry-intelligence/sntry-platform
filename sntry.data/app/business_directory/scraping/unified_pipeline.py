"""
Unified Data Pipeline for Jamaica Business Directory
Integrates web scraping, social media data, and sentiment analysis
"""
import asyncio
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

from app.business_directory.schemas import BusinessData
from app.business_directory.scraping.scraping_service import ScrapingService
from app.business_directory.scraping.social_media_scraper import SocialMediaScrapingService
from app.business_directory.scraping.sentiment_analysis import BusinessSentimentAnalyzer

logger = logging.getLogger(__name__)


class Customer360Data:
    """
    Container for customer 360 view data
    """
    def __init__(self, business_data: BusinessData):
        self.business_data = business_data
        self.social_media_profiles = {}
        self.sentiment_analysis = {}
        self.customer_insights = {}
        self.lead_score = 0.0
        self.last_updated = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/API response"""
        return {
            "business_data": self.business_data.dict() if hasattr(self.business_data, 'dict') else self.business_data.model_dump(),
            "social_media_profiles": self.social_media_profiles,
            "sentiment_analysis": self.sentiment_analysis,
            "customer_insights": self.customer_insights,
            "lead_score": self.lead_score,
            "last_updated": self.last_updated.isoformat()
        }


class UnifiedDataPipeline:
    """
    Unified pipeline that combines business directory scraping with social media data
    and customer insights for a complete 360-degree view
    """
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.scraping_service = None
        self.social_media_service = None
        self.sentiment_analyzer = BusinessSentimentAnalyzer()
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.scraping_service = ScrapingService(headless=self.headless)
        await self.scraping_service.start()
        self.social_media_service = SocialMediaScrapingService(self.scraping_service.browser)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.scraping_service:
            await self.scraping_service.stop()
    
    async def scrape_businesses_with_customer_360(
        self, 
        category: str, 
        location: str = "", 
        include_social_media: bool = True,
        include_sentiment: bool = True,
        websites: Optional[List[str]] = None
    ) -> List[Customer360Data]:
        """
        Comprehensive business scraping with customer 360 data enrichment
        
        Args:
            category: Business category to search for
            location: Location to search in
            include_social_media: Whether to include social media profile data
            include_sentiment: Whether to perform sentiment analysis
            websites: List of websites to scrape from
            
        Returns:
            List of Customer360Data objects with enriched business information
        """
        logger.info(f"Starting unified pipeline for category '{category}' in location '{location}'")
        
        # Step 1: Scrape basic business data
        logger.info("Step 1: Scraping business directory data...")
        businesses = await self.scraping_service.scrape_category(category, location, websites)
        logger.info(f"Found {len(businesses)} businesses from directory scraping")
        
        # Step 2: Enrich with customer 360 data
        customer_360_data = []
        
        for i, business in enumerate(businesses):
            try:
                logger.info(f"Processing business {i+1}/{len(businesses)}: {business.name}")
                
                # Create customer 360 container
                customer_360 = Customer360Data(business)
                
                # Step 3: Add social media data if requested
                if include_social_media:
                    try:
                        logger.debug(f"Getting social media profiles for {business.name}")
                        social_profiles = await self.social_media_service.get_business_social_profiles(
                            business.name, location
                        )
                        customer_360.social_media_profiles = {
                            platform: profile.dict() if hasattr(profile, 'dict') else profile.model_dump()
                            for platform, profile in social_profiles.items()
                        }
                        
                        # Calculate social media reach
                        total_followers = sum(
                            profile.get('follower_count', 0) or 0 
                            for profile in customer_360.social_media_profiles.values()
                        )
                        customer_360.customer_insights['social_media_reach'] = total_followers
                        
                    except Exception as e:
                        logger.warning(f"Error getting social media data for {business.name}: {e}")
                
                # Step 4: Perform sentiment analysis if requested
                if include_sentiment:
                    try:
                        # For now, we'll analyze the business description as a proxy for reviews
                        # In a full implementation, this would analyze actual reviews and mentions
                        review_texts = []
                        if business.description:
                            review_texts.append(business.description)
                        
                        if review_texts:
                            sentiment_results = self.sentiment_analyzer.analyze_business_mentions(
                                review_texts, business.name
                            )
                            customer_360.sentiment_analysis = sentiment_results
                            
                            # Calculate reputation score
                            reputation_score, reputation_level = self.sentiment_analyzer.get_reputation_score(
                                sentiment_results
                            )
                            customer_360.customer_insights['reputation_score'] = reputation_score
                            customer_360.customer_insights['reputation_level'] = reputation_level
                        
                    except Exception as e:
                        logger.warning(f"Error performing sentiment analysis for {business.name}: {e}")
                
                # Step 5: Calculate lead score
                customer_360.lead_score = self._calculate_lead_score(customer_360)
                
                # Step 6: Add additional customer insights
                customer_360.customer_insights.update(
                    self._generate_customer_insights(customer_360)
                )
                
                customer_360_data.append(customer_360)
                
                # Add delay between businesses to be respectful
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error processing business {business.name}: {e}")
                # Still add the basic business data even if enrichment fails
                customer_360_data.append(Customer360Data(business))
        
        logger.info(f"Completed unified pipeline processing for {len(customer_360_data)} businesses")
        return customer_360_data
    
    def _calculate_lead_score(self, customer_360: Customer360Data) -> float:
        """
        Calculate a lead score based on various business factors
        
        Score is 0-100 where higher scores indicate better lead potential
        """
        score = 50.0  # Base score
        
        # Factor 1: Contact information completeness
        contact_score = 0
        if customer_360.business_data.phone_number:
            contact_score += 15
        if customer_360.business_data.email:
            contact_score += 10
        if customer_360.business_data.website:
            contact_score += 10
        
        # Factor 2: Social media presence
        social_score = 0
        if customer_360.social_media_profiles:
            social_score += len(customer_360.social_media_profiles) * 5
            
            # Bonus for follower count
            total_followers = customer_360.customer_insights.get('social_media_reach', 0)
            if total_followers > 10000:
                social_score += 15
            elif total_followers > 1000:
                social_score += 10
            elif total_followers > 100:
                social_score += 5
        
        # Factor 3: Reputation/sentiment
        reputation_score = customer_360.customer_insights.get('reputation_score', 50)
        reputation_factor = (reputation_score - 50) * 0.3  # -15 to +15 range
        
        # Factor 4: Business description quality
        description_score = 0
        if customer_360.business_data.description:
            desc_length = len(customer_360.business_data.description)
            if desc_length > 200:
                description_score += 10
            elif desc_length > 100:
                description_score += 5
            elif desc_length > 50:
                description_score += 2
        
        # Combine all factors
        final_score = score + contact_score + social_score + reputation_factor + description_score
        
        # Ensure score is within 0-100 range
        return max(0.0, min(100.0, final_score))
    
    def _generate_customer_insights(self, customer_360: Customer360Data) -> Dict[str, Any]:
        """
        Generate additional customer insights based on available data
        """
        insights = {}
        
        # Business maturity indicators
        maturity_indicators = []
        if customer_360.business_data.website:
            maturity_indicators.append("Has website")
        if customer_360.social_media_profiles:
            maturity_indicators.append("Active on social media")
        if customer_360.business_data.email:
            maturity_indicators.append("Professional email")
        
        insights['business_maturity_indicators'] = maturity_indicators
        
        # Digital presence score
        digital_presence = 0
        if customer_360.business_data.website:
            digital_presence += 30
        if customer_360.business_data.email:
            digital_presence += 20
        if customer_360.social_media_profiles:
            digital_presence += len(customer_360.social_media_profiles) * 15
        
        insights['digital_presence_score'] = min(100, digital_presence)
        
        # Contact preference prediction
        contact_methods = []
        if customer_360.business_data.phone_number:
            contact_methods.append("phone")
        if customer_360.business_data.email:
            contact_methods.append("email")
        if customer_360.social_media_profiles:
            contact_methods.append("social_media")
        
        insights['available_contact_methods'] = contact_methods
        
        # Business category insights
        category = customer_360.business_data.category
        if category:
            insights['category'] = category
            insights['category_insights'] = self._get_category_insights(category)
        
        return insights
    
    def _get_category_insights(self, category: str) -> Dict[str, Any]:
        """
        Get category-specific insights for businesses
        """
        category_lower = category.lower()
        
        # Define category-specific characteristics
        category_insights = {
            'restaurant': {
                'key_factors': ['food_quality', 'service', 'ambiance', 'location'],
                'peak_hours': ['lunch', 'dinner'],
                'seasonal_trends': 'moderate',
                'social_media_importance': 'high'
            },
            'hotel': {
                'key_factors': ['location', 'amenities', 'service', 'cleanliness'],
                'peak_seasons': ['winter', 'summer'],
                'seasonal_trends': 'high',
                'social_media_importance': 'very_high'
            },
            'lawyer': {
                'key_factors': ['expertise', 'reputation', 'communication', 'results'],
                'peak_hours': ['business_hours'],
                'seasonal_trends': 'low',
                'social_media_importance': 'medium'
            },
            'gas_station': {
                'key_factors': ['location', 'price', 'convenience', 'service'],
                'peak_hours': ['morning', 'evening'],
                'seasonal_trends': 'low',
                'social_media_importance': 'low'
            }
        }
        
        # Find matching category
        for cat_key, insights in category_insights.items():
            if cat_key in category_lower or category_lower in cat_key:
                return insights
        
        # Default insights
        return {
            'key_factors': ['quality', 'service', 'value', 'location'],
            'seasonal_trends': 'moderate',
            'social_media_importance': 'medium'
        }
    
    async def export_customer_360_data(
        self, 
        customer_360_data: List[Customer360Data], 
        format: str = "json"
    ) -> str:
        """
        Export customer 360 data in various formats
        
        Args:
            customer_360_data: List of Customer360Data objects
            format: Export format ('json', 'csv', 'xlsx')
            
        Returns:
            Exported data as string or file path
        """
        if format.lower() == "json":
            import json
            data = [c360.to_dict() for c360 in customer_360_data]
            return json.dumps(data, indent=2, default=str)
        
        elif format.lower() == "csv":
            import csv
            import io
            
            output = io.StringIO()
            if customer_360_data:
                # Flatten the data for CSV
                fieldnames = [
                    'business_name', 'category', 'phone_number', 'email', 'website',
                    'address', 'description', 'lead_score', 'reputation_score',
                    'social_media_reach', 'digital_presence_score'
                ]
                
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                
                for c360 in customer_360_data:
                    row = {
                        'business_name': c360.business_data.name,
                        'category': c360.business_data.category,
                        'phone_number': c360.business_data.phone_number,
                        'email': c360.business_data.email,
                        'website': c360.business_data.website,
                        'address': c360.business_data.raw_address,
                        'description': c360.business_data.description,
                        'lead_score': c360.lead_score,
                        'reputation_score': c360.customer_insights.get('reputation_score', 0),
                        'social_media_reach': c360.customer_insights.get('social_media_reach', 0),
                        'digital_presence_score': c360.customer_insights.get('digital_presence_score', 0)
                    }
                    writer.writerow(row)
            
            return output.getvalue()
        
        else:
            raise ValueError(f"Unsupported export format: {format}")


# Convenience functions
async def scrape_businesses_with_insights(
    category: str, 
    location: str = "", 
    include_social: bool = True,
    websites: Optional[List[str]] = None
) -> List[Customer360Data]:
    """Convenience function for comprehensive business scraping"""
    async with UnifiedDataPipeline() as pipeline:
        return await pipeline.scrape_businesses_with_customer_360(
            category, location, include_social, True, websites
        )


async def generate_lead_report(category: str, location: str = "") -> str:
    """Generate a lead generation report for a specific category and location"""
    async with UnifiedDataPipeline() as pipeline:
        customer_360_data = await pipeline.scrape_businesses_with_customer_360(
            category, location, True, True
        )
        
        # Sort by lead score
        customer_360_data.sort(key=lambda x: x.lead_score, reverse=True)
        
        # Export as CSV
        return await pipeline.export_customer_360_data(customer_360_data, "csv")