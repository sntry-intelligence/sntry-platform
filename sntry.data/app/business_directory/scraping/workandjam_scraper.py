"""
WorkAndJam.com scraper implementation for Jamaica business directory
"""
import asyncio
import logging
import re
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin, urlparse, parse_qs
from datetime import datetime

from playwright.async_api import Browser, Page, TimeoutError as PlaywrightTimeoutError

from app.business_directory.schemas import BusinessData
from app.business_directory.scraping.base import BaseScraper, ScrapingResult

logger = logging.getLogger(__name__)


class WorkAndJamScraper(BaseScraper):
    """Scraper for workandjam.com Jamaica business directory"""
    
    def __init__(self, browser: Browser):
        super().__init__(browser, "https://www.workandjam.com")
        self.business_directory_url = f"{self.base_url}/business-directory"
        
    async def scrape_category(self, category: str, location: str = "") -> List[BusinessData]:
        """Scrape businesses by category and location from WorkAndJam"""
        result = ScrapingResult()
        result.source_website = "workandjam.com"
        
        try:
            # Navigate to business directory
            await self.page.goto(self.business_directory_url, wait_until="networkidle")
            await self.human_delay(2, 4)
            
            # Perform search
            await self._perform_search(category, location)
            
            # Get total pages for pagination
            total_pages = await self._get_total_pages()
            result.total_pages = total_pages
            
            logger.info(f"Found {total_pages} pages for category '{category}' in location '{location}'")
            
            # Scrape all pages
            for page_num in range(1, total_pages + 1):
                try:
                    if page_num > 1:
                        await self._navigate_to_page(page_num)
                    
                    businesses = await self._scrape_current_page()
                    for business in businesses:
                        result.add_business(business)
                    
                    result.scraped_pages = page_num
                    logger.info(f"Scraped page {page_num}/{total_pages}, found {len(businesses)} businesses")
                    
                    # Add delay between pages
                    await self.human_delay(3, 6)
                    
                except Exception as e:
                    error_msg = f"Error scraping page {page_num}: {str(e)}"
                    result.add_error(error_msg)
                    continue
                    
        except Exception as e:
            error_msg = f"Error during category scraping: {str(e)}"
            result.add_error(error_msg)
            
        result.finish()
        logger.info(f"WorkAndJam scraping completed: {result.to_dict()}")
        return result.businesses
    
    async def _perform_search(self, category: str, location: str = ""):
        """Perform search on WorkAndJam business directory"""
        # Fill in the search form
        search_query = f"{category} {location}".strip()
        
        # Look for search input field - WorkAndJam specific selectors
        search_selectors = [
            'input[name="search"]',
            'input[placeholder*="Search"]',
            'input[placeholder*="business"]',
            '#business-search',
            '.search-input',
            'input[type="text"]'
        ]
        
        search_filled = False
        for selector in search_selectors:
            if await self.safe_fill(self.page, selector, search_query):
                search_filled = True
                break
        
        if not search_filled:
            # Try to find any text input field
            try:
                text_inputs = await self.page.query_selector_all('input[type="text"]')
                if text_inputs:
                    await text_inputs[0].fill(search_query)
                    search_filled = True
            except:
                pass
        
        if not search_filled:
            logger.warning("Could not find search input field, proceeding with category browsing")
            # Try to browse by category instead
            await self._browse_by_category(category)
            return
        
        # Submit search
        submit_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            '.search-button',
            '#search-btn',
            'button:has-text("Search")',
            '.btn-search'
        ]
        
        search_submitted = False
        for selector in submit_selectors:
            if await self.safe_click(self.page, selector):
                search_submitted = True
                break
        
        if not search_submitted:
            # Try pressing Enter on search field
            await self.page.keyboard.press('Enter')
        
        # Wait for results to load
        await self.page.wait_for_load_state("networkidle")
        await self.human_delay(2, 4)
    
    async def _browse_by_category(self, category: str):
        """Browse businesses by category when search is not available"""
        try:
            # Look for category links or buttons
            category_selectors = [
                f'a:has-text("{category}")',
                f'button:has-text("{category}")',
                f'.category:has-text("{category}")',
                f'.business-category:has-text("{category}")'
            ]
            
            for selector in category_selectors:
                if await self.safe_click(self.page, selector):
                    await self.page.wait_for_load_state("networkidle")
                    await self.human_delay(2, 4)
                    return
            
            # If exact category not found, try partial matches
            category_lower = category.lower()
            all_links = await self.page.query_selector_all('a')
            
            for link in all_links:
                try:
                    text = await link.text_content()
                    if text and category_lower in text.lower():
                        await link.click()
                        await self.page.wait_for_load_state("networkidle")
                        await self.human_delay(2, 4)
                        return
                except:
                    continue
                    
        except Exception as e:
            logger.warning(f"Could not browse by category {category}: {e}")
    
    async def _get_total_pages(self) -> int:
        """Extract total number of pages from pagination"""
        try:
            # WorkAndJam specific pagination selectors
            pagination_selectors = [
                '.pagination .page-item:last-child a',
                '.pagination a:last-child',
                '.pager .last a',
                '.page-numbers a:last-child',
                'a[aria-label="Last page"]',
                '.pagination-last'
            ]
            
            for selector in pagination_selectors:
                try:
                    last_page_element = await self.page.wait_for_selector(selector, timeout=3000)
                    if last_page_element:
                        page_text = await last_page_element.text_content()
                        if page_text and page_text.strip().isdigit():
                            return int(page_text.strip())
                        
                        # Check href for page number
                        href = await last_page_element.get_attribute('href')
                        if href:
                            # Look for page parameter in URL
                            page_match = re.search(r'[?&]page[=\/](\d+)', href)
                            if page_match:
                                return int(page_match.group(1))
                            
                            # Look for page number at end of URL
                            page_match = re.search(r'\/(\d+)/?$', href)
                            if page_match:
                                return int(page_match.group(1))
                except:
                    continue
            
            # Look for pagination info text like "Page 1 of 5" or "Showing 1-10 of 50"
            pagination_info_selectors = [
                '.pagination-info',
                '.page-info',
                '.results-info',
                '.showing-results'
            ]
            
            for selector in pagination_info_selectors:
                try:
                    info_element = await self.page.wait_for_selector(selector, timeout=3000)
                    if info_element:
                        info_text = await info_element.text_content()
                        # Look for "of X" pattern
                        page_match = re.search(r'of\s+(\d+)', info_text, re.IGNORECASE)
                        if page_match:
                            total_results = int(page_match.group(1))
                            # Assume 10 results per page if not specified
                            return max(1, (total_results + 9) // 10)
                except:
                    continue
            
            # Count visible pagination links
            try:
                page_links = await self.page.query_selector_all('.pagination a, .page-numbers a')
                if page_links:
                    max_page = 1
                    for link in page_links:
                        text = await link.text_content()
                        if text and text.strip().isdigit():
                            max_page = max(max_page, int(text.strip()))
                    if max_page > 1:
                        return max_page
            except:
                pass
            
            # Default to 1 page if pagination not found
            return 1
            
        except Exception as e:
            logger.warning(f"Could not determine total pages: {e}")
            return 1
    
    async def _navigate_to_page(self, page_num: int):
        """Navigate to a specific page number"""
        try:
            # Look for specific page link
            page_selectors = [
                f'a[href*="page={page_num}"]',
                f'a[href*="page/{page_num}"]',
                f'a[href*="/{page_num}"]',
                f'.pagination a:has-text("{page_num}")',
                f'.page-numbers a:has-text("{page_num}")'
            ]
            
            for selector in page_selectors:
                if await self.safe_click(self.page, selector):
                    await self.page.wait_for_load_state("networkidle")
                    await self.human_delay(2, 4)
                    return
            
            # If direct page link not found, try next button repeatedly
            current_page = 1
            while current_page < page_num:
                next_selectors = [
                    'a[aria-label="Next page"]',
                    '.pagination .next a',
                    '.pagination-next a',
                    'a:has-text("Next")',
                    '.pager-next a',
                    '.page-item.next a'
                ]
                
                clicked = False
                for selector in next_selectors:
                    if await self.safe_click(self.page, selector):
                        await self.page.wait_for_load_state("networkidle")
                        await self.human_delay(2, 4)
                        current_page += 1
                        clicked = True
                        break
                
                if not clicked:
                    raise Exception(f"Could not navigate to page {page_num}")
                    
        except Exception as e:
            raise Exception(f"Failed to navigate to page {page_num}: {e}")
    
    async def _scrape_current_page(self) -> List[BusinessData]:
        """Scrape business listings from current page"""
        businesses = []
        
        try:
            # Wait for business listings to load - WorkAndJam specific selectors
            listing_selectors = [
                '.business-listing',
                '.business-card',
                '.company-listing',
                '.directory-item',
                '.business-item',
                '.listing-item',
                '.job-listing',  # WorkAndJam might mix job and business listings
                '.company-profile'
            ]
            
            # Try to find listings with any of the selectors
            listings = []
            for selector in listing_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        listings = elements
                        logger.info(f"Found listings using selector: {selector}")
                        break
                except:
                    continue
            
            if not listings:
                # Fallback: look for any div that might contain business info
                try:
                    await self.page.wait_for_selector('div', timeout=5000)
                    # Look for divs that contain business-like information
                    all_divs = await self.page.query_selector_all('div')
                    potential_listings = []
                    
                    for div in all_divs:
                        try:
                            text_content = await div.text_content()
                            if text_content and len(text_content) > 50:  # Reasonable content length
                                # Check if it contains business-like keywords
                                business_keywords = ['phone', 'email', 'address', 'contact', 'website', 'jamaica']
                                if any(keyword in text_content.lower() for keyword in business_keywords):
                                    potential_listings.append(div)
                        except:
                            continue
                    
                    if potential_listings:
                        listings = potential_listings[:20]  # Limit to reasonable number
                        logger.info(f"Using fallback method, found {len(listings)} potential listings")
                except:
                    pass
            
            if not listings:
                logger.warning("No business listings found on current page")
                return businesses
            
            logger.info(f"Found {len(listings)} business listings on current page")
            
            for i, listing in enumerate(listings):
                try:
                    business_data = await self._extract_business_from_listing(listing)
                    if business_data:
                        businesses.append(business_data)
                        
                except Exception as e:
                    logger.warning(f"Error extracting business {i}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error scraping current page: {e}")
            
        return businesses
    
    async def _extract_business_from_listing(self, listing) -> Optional[BusinessData]:
        """Extract business data from a single listing element"""
        try:
            # Extract business name - WorkAndJam specific selectors
            name_selectors = [
                '.company-name',
                '.business-name',
                '.listing-title',
                '.job-title',  # WorkAndJam specific
                '.company-title',
                'h2 a',
                'h3 a',
                'h4 a',
                '.title a',
                'a[href*="company"]',
                'strong'
            ]
            
            name = ""
            for selector in name_selectors:
                try:
                    name_element = await listing.query_selector(selector)
                    if name_element:
                        name = await name_element.text_content()
                        name = name.strip() if name else ""
                        if name and len(name) > 2:  # Reasonable name length
                            break
                except:
                    continue
            
            if not name:
                # Fallback: get the first meaningful text
                try:
                    all_text = await listing.text_content()
                    if all_text:
                        lines = [line.strip() for line in all_text.split('\n') if line.strip()]
                        for line in lines:
                            if len(line) > 2 and len(line) < 100:  # Reasonable name length
                                name = line
                                break
                except:
                    pass
            
            if not name:
                logger.warning("Could not extract business name")
                return None
            
            # Extract address - WorkAndJam specific
            address_selectors = [
                '.address',
                '.location',
                '.company-address',
                '.business-address',
                '.listing-address',
                '.contact-info .address'
            ]
            
            address = ""
            for selector in address_selectors:
                try:
                    address_element = await listing.query_selector(selector)
                    if address_element:
                        address = await address_element.text_content()
                        address = address.strip() if address else ""
                        if address:
                            break
                except:
                    continue
            
            # If no specific address found, look for Jamaica-related text
            if not address:
                try:
                    all_text = await listing.text_content()
                    if all_text:
                        # Look for Jamaica, Kingston, parishes, etc.
                        jamaica_pattern = re.compile(r'[^.]*(?:jamaica|kingston|spanish town|montego bay|mandeville|may pen|st\.\s*\w+)[^.]*', re.IGNORECASE)
                        match = jamaica_pattern.search(all_text)
                        if match:
                            address = match.group(0).strip()
                except:
                    pass
            
            # Extract phone number
            phone_selectors = [
                '.phone',
                '.telephone',
                '.contact-phone',
                'a[href^="tel:"]',
                '.contact-info .phone'
            ]
            
            phone = ""
            for selector in phone_selectors:
                try:
                    phone_element = await listing.query_selector(selector)
                    if phone_element:
                        if selector.startswith('a[href^="tel:"]'):
                            phone = await phone_element.get_attribute('href')
                            phone = phone.replace('tel:', '') if phone else ""
                        else:
                            phone = await phone_element.text_content()
                        phone = phone.strip() if phone else ""
                        if phone:
                            break
                except:
                    continue
            
            # If no specific phone found, look for phone patterns in text
            if not phone:
                try:
                    all_text = await listing.text_content()
                    if all_text:
                        # Jamaican phone patterns
                        phone_patterns = [
                            r'\b(?:\+?1[-.\s]?)?876[-.\s]?\d{3}[-.\s]?\d{4}\b',  # 876 area code
                            r'\b\d{3}[-.\s]?\d{4}\b',  # 7-digit local
                            r'\b(?:\+?1[-.\s]?)?876[-.\s]?\d{7}\b'  # 876 without separators
                        ]
                        
                        for pattern in phone_patterns:
                            match = re.search(pattern, all_text)
                            if match:
                                phone = match.group(0).strip()
                                break
                except:
                    pass
            
            # Extract email
            email_selectors = [
                '.email',
                'a[href^="mailto:"]',
                '.contact-email'
            ]
            
            email = ""
            for selector in email_selectors:
                try:
                    email_element = await listing.query_selector(selector)
                    if email_element:
                        if selector.startswith('a[href^="mailto:"]'):
                            email = await email_element.get_attribute('href')
                            email = email.replace('mailto:', '') if email else ""
                        else:
                            email = await email_element.text_content()
                        email = email.strip() if email else ""
                        if email and '@' in email:
                            break
                except:
                    continue
            
            # If no specific email found, look for email patterns
            if not email:
                try:
                    all_text = await listing.text_content()
                    if all_text:
                        email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
                        match = email_pattern.search(all_text)
                        if match:
                            email = match.group(0).strip()
                except:
                    pass
            
            # Extract website
            website_selectors = [
                '.website a',
                '.url a',
                'a[href^="http"]:not([href^="mailto:"]):not([href^="tel:"])',
                '.company-website a'
            ]
            
            website = ""
            for selector in website_selectors:
                try:
                    website_element = await listing.query_selector(selector)
                    if website_element:
                        website = await website_element.get_attribute('href')
                        website = website.strip() if website else ""
                        if website and website.startswith('http') and 'workandjam.com' not in website:
                            break
                except:
                    continue
            
            # Extract category/description
            category_selectors = [
                '.category',
                '.business-type',
                '.industry',
                '.job-category',  # WorkAndJam specific
                '.classification'
            ]
            
            category = ""
            for selector in category_selectors:
                try:
                    category_element = await listing.query_selector(selector)
                    if category_element:
                        category = await category_element.text_content()
                        category = category.strip() if category else ""
                        if category:
                            break
                except:
                    continue
            
            # Extract description
            description_selectors = [
                '.description',
                '.business-description',
                '.job-description',  # WorkAndJam specific
                '.summary',
                '.company-description'
            ]
            
            description = ""
            for selector in description_selectors:
                try:
                    desc_element = await listing.query_selector(selector)
                    if desc_element:
                        description = await desc_element.text_content()
                        description = description.strip() if description else ""
                        if description and len(description) > 10:
                            break
                except:
                    continue
            
            # Get source URL (current page URL)
            source_url = self.page.url
            
            # Create BusinessData object
            business_data = BusinessData(
                name=name,
                category=category or None,
                raw_address=address or "Address not available",
                phone_number=phone or None,
                email=email or None,
                website=website or None,
                description=description or None,
                source_url=source_url,
                last_scraped_at=datetime.now(),
                scrape_status="success"
            )
            
            return business_data
            
        except Exception as e:
            logger.error(f"Error extracting business data: {e}")
            return None
    
    async def scrape_business_details(self, business_url: str) -> Optional[BusinessData]:
        """Scrape detailed information for a specific business"""
        try:
            await self.page.goto(business_url, wait_until="networkidle")
            await self.human_delay(2, 4)
            
            # Extract detailed business information from business profile page
            # This would be implemented based on WorkAndJam's business detail page structure
            return None
            
        except Exception as e:
            logger.error(f"Error scraping business details from {business_url}: {e}")
            return None
    
    async def get_categories(self) -> List[str]:
        """Get available business categories from WorkAndJam"""
        try:
            # Navigate to business directory or main page
            await self.page.goto(self.business_directory_url, wait_until="networkidle")
            await self.human_delay(2, 4)
            
            # Look for category links or dropdown
            category_selectors = [
                '.categories a',
                '.category-list a',
                'select[name="category"] option',
                '.business-categories a',
                '.industry-list a',
                '.job-categories a'  # WorkAndJam specific
            ]
            
            categories = []
            for selector in category_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    for element in elements:
                        text = await element.text_content()
                        if text and text.strip() and len(text.strip()) > 2:
                            categories.append(text.strip())
                    if categories:
                        break
                except:
                    continue
            
            # Add common Jamaican business categories if none found
            if not categories:
                categories = [
                    "Restaurants", "Hotels", "Tourism", "Construction", "Real Estate",
                    "Automotive", "Healthcare", "Education", "Financial Services",
                    "Retail", "Manufacturing", "Agriculture", "Technology", "Legal Services"
                ]
            
            return list(set(categories))  # Remove duplicates
            
        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            return []
    
    async def get_locations(self) -> List[str]:
        """Get available locations from WorkAndJam"""
        try:
            # Navigate to business directory
            await self.page.goto(self.business_directory_url, wait_until="networkidle")
            await self.human_delay(2, 4)
            
            # Look for location options
            location_selectors = [
                '.locations a',
                '.location-list a',
                'select[name="location"] option',
                '.parishes a',
                '.cities a'
            ]
            
            locations = []
            for selector in location_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    for element in elements:
                        text = await element.text_content()
                        if text and text.strip() and len(text.strip()) > 2:
                            locations.append(text.strip())
                    if locations:
                        break
                except:
                    continue
            
            # Add common Jamaican locations if none found
            if not locations:
                locations = [
                    "Kingston", "Spanish Town", "Portmore", "Montego Bay",
                    "May Pen", "Mandeville", "Old Harbour", "Savanna-la-Mar",
                    "Port Antonio", "Linstead", "Half Way Tree", "Ocho Rios",
                    "Negril", "Port Maria", "Lucea", "Black River"
                ]
            
            return list(set(locations))  # Remove duplicates
            
        except Exception as e:
            logger.error(f"Error getting locations: {e}")
            return []