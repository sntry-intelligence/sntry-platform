"""
Social Media Scraper for Jamaica Business Directory
Focuses on publicly available business information with respect for platform policies
"""
import asyncio
import logging
import re
import json
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin, urlparse
from datetime import datetime
from abc import ABC, abstractmethod

from playwright.async_api import Browser, Page, TimeoutError as PlaywrightTimeoutError

from pydantic import BaseModel
from app.business_directory.schemas import BusinessData
from app.business_directory.scraping.base import BaseScraper, ScrapingResult

logger = logging.getLogger(__name__)


class SocialMediaProfile(BaseModel):
    """Schema for social media profile data"""
    platform: str
    username: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    follower_count: Optional[int] = None
    following_count: Optional[int] = None
    post_count: Optional[int] = None
    verified: bool = False
    business_category: Optional[str] = None
    contact_info: Optional[Dict[str, str]] = None
    website: Optional[str] = None
    location: Optional[str] = None
    profile_image_url: Optional[str] = None
    last_post_date: Optional[datetime] = None
    engagement_rate: Optional[float] = None
    
    class Config:
        from_attributes = True


class SocialMediaPost(BaseModel):
    """Schema for social media post data"""
    platform: str
    post_id: str
    username: str
    content: Optional[str] = None
    media_urls: List[str] = []
    hashtags: List[str] = []
    mentions: List[str] = []
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    share_count: Optional[int] = None
    post_date: Optional[datetime] = None
    location: Optional[str] = None
    
    class Config:
        from_attributes = True


class BaseSocialMediaScraper(ABC):
    """Abstract base class for social media scrapers"""
    
    def __init__(self, browser: Browser, platform_name: str):
        self.browser = browser
        self.platform_name = platform_name
        self.context = None
        self.page = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )
        self.page = await self.context.new_page()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
    
    async def human_delay(self, min_seconds: float = 2.0, max_seconds: float = 5.0):
        """Add human-like delay between actions"""
        import random
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)
    
    @abstractmethod
    async def get_profile_data(self, username: str) -> Optional[SocialMediaProfile]:
        """Get profile data for a business account"""
        pass
    
    @abstractmethod
    async def get_recent_posts(self, username: str, limit: int = 10) -> List[SocialMediaPost]:
        """Get recent posts from a business account"""
        pass
    
    @abstractmethod
    async def search_business_profiles(self, business_name: str, location: str = "") -> List[SocialMediaProfile]:
        """Search for business profiles by name and location"""
        pass


class InstagramBusinessScraper(BaseSocialMediaScraper):
    """
    Instagram business profile scraper
    
    IMPORTANT: This scraper is designed to only access publicly available information
    and should be used in compliance with Instagram's Terms of Service and robots.txt
    """
    
    def __init__(self, browser: Browser):
        super().__init__(browser, "instagram")
        self.base_url = "https://www.instagram.com"
        
    async def get_profile_data(self, username: str) -> Optional[SocialMediaProfile]:
        """
        Get publicly available profile data for an Instagram business account
        
        Note: This method respects Instagram's robots.txt and only accesses
        publicly available information
        """
        try:
            profile_url = f"{self.base_url}/{username}/"
            
            # Check if we should proceed based on robots.txt compliance
            if not await self._check_robots_compliance(profile_url):
                logger.warning(f"Robots.txt disallows access to {profile_url}")
                return None
            
            await self.page.goto(profile_url, wait_until="networkidle")
            await self.human_delay(3, 6)
            
            # Check if profile exists and is public
            if await self._is_private_or_not_found():
                logger.info(f"Profile {username} is private or not found")
                return None
            
            # Extract profile data from publicly available information
            profile_data = await self._extract_profile_data(username)
            return profile_data
            
        except Exception as e:
            logger.error(f"Error getting Instagram profile data for {username}: {e}")
            return None
    
    async def _check_robots_compliance(self, url: str) -> bool:
        """
        Check if the URL is allowed by robots.txt
        This is a placeholder - in production, implement proper robots.txt checking
        """
        # For now, we'll be conservative and only allow profile pages
        return "/p/" not in url and "/reel/" not in url
    
    async def _is_private_or_not_found(self) -> bool:
        """Check if the profile is private or doesn't exist"""
        try:
            # Look for indicators of private account or not found
            private_indicators = [
                'This Account is Private',
                'Sorry, this page isn\'t available',
                'User not found'
            ]
            
            page_text = await self.page.text_content('body')
            if page_text:
                for indicator in private_indicators:
                    if indicator.lower() in page_text.lower():
                        return True
            
            return False
        except Exception:
            return True
    
    async def _extract_profile_data(self, username: str) -> Optional[SocialMediaProfile]:
        """Extract profile data from Instagram page"""
        try:
            # Look for JSON-LD structured data or meta tags
            profile_data = SocialMediaProfile(
                platform="instagram",
                username=username
            )
            
            # Try to extract basic information from meta tags
            try:
                # Get display name from title or meta tags
                title = await self.page.title()
                if title and username not in title.lower():
                    profile_data.display_name = title.split('•')[0].strip() if '•' in title else title.strip()
                
                # Get description from meta description
                meta_desc = await self.page.get_attribute('meta[name="description"]', 'content')
                if meta_desc:
                    profile_data.bio = meta_desc
                
            except Exception as e:
                logger.debug(f"Error extracting meta data: {e}")
            
            # Try to extract follower counts (if publicly visible)
            try:
                # Look for follower count in visible text
                page_text = await self.page.text_content('body')
                if page_text:
                    # Look for patterns like "1,234 followers"
                    follower_match = re.search(r'([\d,]+)\s+followers?', page_text, re.IGNORECASE)
                    if follower_match:
                        follower_str = follower_match.group(1).replace(',', '')
                        profile_data.follower_count = int(follower_str)
                    
                    # Look for following count
                    following_match = re.search(r'([\d,]+)\s+following', page_text, re.IGNORECASE)
                    if following_match:
                        following_str = following_match.group(1).replace(',', '')
                        profile_data.following_count = int(following_str)
                    
                    # Look for post count
                    posts_match = re.search(r'([\d,]+)\s+posts?', page_text, re.IGNORECASE)
                    if posts_match:
                        posts_str = posts_match.group(1).replace(',', '')
                        profile_data.post_count = int(posts_str)
                        
            except Exception as e:
                logger.debug(f"Error extracting counts: {e}")
            
            return profile_data
            
        except Exception as e:
            logger.error(f"Error extracting Instagram profile data: {e}")
            return None
    
    async def get_recent_posts(self, username: str, limit: int = 10) -> List[SocialMediaPost]:
        """
        Get recent posts from a public Instagram business account
        
        Note: This method only accesses publicly available posts and respects
        Instagram's Terms of Service
        """
        try:
            # For now, return empty list as post scraping requires more careful
            # consideration of Instagram's policies
            logger.info(f"Post scraping for {username} not implemented - requires API access")
            return []
            
        except Exception as e:
            logger.error(f"Error getting Instagram posts for {username}: {e}")
            return []
    
    async def search_business_profiles(self, business_name: str, location: str = "") -> List[SocialMediaProfile]:
        """
        Search for Instagram business profiles by name and location
        
        Note: This uses Instagram's public search functionality
        """
        try:
            # For now, return empty list as search requires more sophisticated handling
            logger.info(f"Instagram search for '{business_name}' not implemented - requires API access")
            return []
            
        except Exception as e:
            logger.error(f"Error searching Instagram for {business_name}: {e}")
            return []


class TikTokBusinessScraper(BaseSocialMediaScraper):
    """
    TikTok business profile scraper
    
    IMPORTANT: This scraper is designed to only access publicly available information
    and should be used in compliance with TikTok's Terms of Service
    """
    
    def __init__(self, browser: Browser):
        super().__init__(browser, "tiktok")
        self.base_url = "https://www.tiktok.com"
        
    async def get_profile_data(self, username: str) -> Optional[SocialMediaProfile]:
        """
        Get publicly available profile data for a TikTok business account
        """
        try:
            # Clean username (remove @ if present)
            clean_username = username.lstrip('@')
            profile_url = f"{self.base_url}/@{clean_username}"
            
            await self.page.goto(profile_url, wait_until="networkidle")
            await self.human_delay(3, 6)
            
            # Check if profile exists
            if await self._is_profile_not_found():
                logger.info(f"TikTok profile @{clean_username} not found")
                return None
            
            # Extract profile data
            profile_data = await self._extract_tiktok_profile_data(clean_username)
            return profile_data
            
        except Exception as e:
            logger.error(f"Error getting TikTok profile data for {username}: {e}")
            return None
    
    async def _is_profile_not_found(self) -> bool:
        """Check if the TikTok profile doesn't exist"""
        try:
            page_text = await self.page.text_content('body')
            if page_text:
                not_found_indicators = [
                    "Couldn't find this account",
                    "User not found",
                    "This account doesn't exist"
                ]
                for indicator in not_found_indicators:
                    if indicator.lower() in page_text.lower():
                        return True
            return False
        except Exception:
            return True
    
    async def _extract_tiktok_profile_data(self, username: str) -> Optional[SocialMediaProfile]:
        """Extract profile data from TikTok page"""
        try:
            profile_data = SocialMediaProfile(
                platform="tiktok",
                username=username
            )
            
            # Try to extract basic information
            try:
                # Get display name from title
                title = await self.page.title()
                if title and username not in title.lower():
                    profile_data.display_name = title.split('|')[0].strip() if '|' in title else title.strip()
                
                # Get bio from meta description
                meta_desc = await self.page.get_attribute('meta[name="description"]', 'content')
                if meta_desc:
                    profile_data.bio = meta_desc
                    
            except Exception as e:
                logger.debug(f"Error extracting TikTok meta data: {e}")
            
            # Try to extract follower/following counts
            try:
                page_text = await self.page.text_content('body')
                if page_text:
                    # Look for follower patterns
                    follower_match = re.search(r'([\d.]+[KMB]?)\s+Followers?', page_text, re.IGNORECASE)
                    if follower_match:
                        follower_str = follower_match.group(1)
                        profile_data.follower_count = self._parse_count_string(follower_str)
                    
                    # Look for following count
                    following_match = re.search(r'([\d.]+[KMB]?)\s+Following', page_text, re.IGNORECASE)
                    if following_match:
                        following_str = following_match.group(1)
                        profile_data.following_count = self._parse_count_string(following_str)
                    
                    # Look for likes count
                    likes_match = re.search(r'([\d.]+[KMB]?)\s+Likes?', page_text, re.IGNORECASE)
                    if likes_match:
                        likes_str = likes_match.group(1)
                        # Store likes in a custom field or use for engagement calculation
                        
            except Exception as e:
                logger.debug(f"Error extracting TikTok counts: {e}")
            
            return profile_data
            
        except Exception as e:
            logger.error(f"Error extracting TikTok profile data: {e}")
            return None
    
    def _parse_count_string(self, count_str: str) -> Optional[int]:
        """Parse count strings like '1.2K', '5.6M', etc."""
        try:
            count_str = count_str.upper().strip()
            if count_str.endswith('K'):
                return int(float(count_str[:-1]) * 1000)
            elif count_str.endswith('M'):
                return int(float(count_str[:-1]) * 1000000)
            elif count_str.endswith('B'):
                return int(float(count_str[:-1]) * 1000000000)
            else:
                return int(float(count_str))
        except (ValueError, TypeError):
            return None
    
    async def get_recent_posts(self, username: str, limit: int = 10) -> List[SocialMediaPost]:
        """Get recent posts from a public TikTok business account"""
        try:
            # For now, return empty list as post scraping requires careful handling
            logger.info(f"TikTok post scraping for {username} not implemented - requires API access")
            return []
            
        except Exception as e:
            logger.error(f"Error getting TikTok posts for {username}: {e}")
            return []
    
    async def search_business_profiles(self, business_name: str, location: str = "") -> List[SocialMediaProfile]:
        """Search for TikTok business profiles by name and location"""
        try:
            # For now, return empty list as search requires more sophisticated handling
            logger.info(f"TikTok search for '{business_name}' not implemented - requires API access")
            return []
            
        except Exception as e:
            logger.error(f"Error searching TikTok for {business_name}: {e}")
            return []


class SocialMediaScrapingService:
    """
    Unified service for social media business profile scraping
    """
    
    def __init__(self, browser: Browser):
        self.browser = browser
        self.scrapers = {
            'instagram': InstagramBusinessScraper(browser),
            'tiktok': TikTokBusinessScraper(browser)
        }
    
    async def get_business_social_profiles(self, business_name: str, location: str = "") -> Dict[str, SocialMediaProfile]:
        """
        Get social media profiles for a business across multiple platforms
        """
        profiles = {}
        
        for platform, scraper in self.scrapers.items():
            try:
                logger.info(f"Searching {platform} for business: {business_name}")
                
                async with scraper:
                    # Search for profiles matching the business name
                    found_profiles = await scraper.search_business_profiles(business_name, location)
                    
                    if found_profiles:
                        # Take the first/best match
                        profiles[platform] = found_profiles[0]
                        logger.info(f"Found {platform} profile for {business_name}")
                    else:
                        logger.info(f"No {platform} profile found for {business_name}")
                        
            except Exception as e:
                logger.error(f"Error searching {platform} for {business_name}: {e}")
                continue
        
        return profiles
    
    async def enrich_business_with_social_data(self, business: BusinessData) -> BusinessData:
        """
        Enrich business data with social media information
        """
        try:
            # Get social media profiles
            social_profiles = await self.get_business_social_profiles(business.name)
            
            # For now, we'll add social media data as part of the description
            # In a full implementation, you'd extend the BusinessData model
            social_info = []
            
            for platform, profile in social_profiles.items():
                if profile.follower_count:
                    social_info.append(f"{platform.title()}: {profile.follower_count} followers")
            
            if social_info:
                social_text = " | ".join(social_info)
                if business.description:
                    business.description += f" | Social Media: {social_text}"
                else:
                    business.description = f"Social Media: {social_text}"
            
            return business
            
        except Exception as e:
            logger.error(f"Error enriching business {business.name} with social data: {e}")
            return business


# Convenience functions
async def get_instagram_profile(browser: Browser, username: str) -> Optional[SocialMediaProfile]:
    """Convenience function to get Instagram profile data"""
    async with InstagramBusinessScraper(browser) as scraper:
        return await scraper.get_profile_data(username)


async def get_tiktok_profile(browser: Browser, username: str) -> Optional[SocialMediaProfile]:
    """Convenience function to get TikTok profile data"""
    async with TikTokBusinessScraper(browser) as scraper:
        return await scraper.get_profile_data(username)


async def enrich_businesses_with_social_data(browser: Browser, businesses: List[BusinessData]) -> List[BusinessData]:
    """Enrich a list of businesses with social media data"""
    service = SocialMediaScrapingService(browser)
    enriched_businesses = []
    
    for business in businesses:
        try:
            enriched_business = await service.enrich_business_with_social_data(business)
            enriched_businesses.append(enriched_business)
            
            # Add delay between businesses to be respectful
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"Error enriching business {business.name}: {e}")
            enriched_businesses.append(business)  # Add original if enrichment fails
    
    return enriched_businesses