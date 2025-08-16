"""
FindYello.com scraper implementation for Jamaica business directory
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


class FindYelloScraper(BaseScraper):
    """Scraper for findyello.com Jamaica business directory"""
    
    def __init__(self, browser: Browser):
        super().__init__(browser, "https://www.findyello.com")
        self.search_url = self.base_url  # Use homepage for search
        self.category_base_url = f"{self.base_url}/jamaica"
        
    async def scrape_category(self, category: str, location: str = "") -> List[BusinessData]:
        """Scrape businesses by category and location from FindYello"""
        result = ScrapingResult()
        result.source_website = "findyello.com"
        
        try:
            # Navigate to search page using anti-bot measures
            if not await self.safe_navigate(self.search_url):
                raise Exception("Failed to navigate to search page")
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
        logger.info(f"FindYello scraping completed: {result.to_dict()}")
        return result.businesses
    
    async def _perform_search(self, category: str, location: str = ""):
        """Perform search on FindYello using the homepage search or category browsing"""
        await self.page.wait_for_load_state("networkidle")
        
        # Try homepage search first
        search_query = f"{category} {location}".strip()
        
        # FindYello specific selectors based on the HTML structure
        search_selectors = [
            '#home-what',  # Main homepage search input
            'input[name="what"]',  # Form input name
            '#what',  # Header search input
            'input[placeholder*="We know"]'  # Placeholder text
        ]
        
        search_filled = False
        used_selector = None
        
        for selector in search_selectors:
            try:
                element = await self.page.wait_for_selector(selector, timeout=3000)
                if element:
                    await element.fill(search_query)
                    search_filled = True
                    used_selector = selector
                    logger.info(f"Successfully filled search using selector: {selector}")
                    break
            except Exception as e:
                logger.debug(f"Search selector {selector} failed: {e}")
                continue
        
        if search_filled:
            # Submit the search form
            submit_selectors = [
                '.home-submit',  # Homepage submit button
                'form#home-form button',
                'form#home-form input[type="submit"]',
                'form#vform button',
                'form#vform input[type="submit"]'
            ]
            
            search_submitted = False
            for selector in submit_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=3000)
                    if element:
                        await element.click()
                        search_submitted = True
                        logger.info(f"Successfully submitted search using: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Submit selector {selector} failed: {e}")
                    continue
            
            if not search_submitted:
                # Try pressing Enter
                try:
                    await self.page.focus(used_selector)
                    await self.page.keyboard.press('Enter')
                    search_submitted = True
                    logger.info("Submitted search using Enter key")
                except Exception as e:
                    logger.debug(f"Enter key submission failed: {e}")
            
            if search_submitted:
                await self.page.wait_for_load_state("networkidle")
                await self.human_delay(2, 4)
                return
        
        # If search didn't work, try category browsing
        logger.info("Search form not found or failed, trying category browsing")
        await self._browse_by_category(category, location)
    
    async def _browse_by_category(self, category: str, location: str = ""):
        """Browse businesses by category using FindYello's category structure"""
        try:
            logger.info(f"Attempting to browse by category: {category}")
            
            # First, try to find category tiles on the homepage
            category_tiles = await self.page.query_selector_all('.category-tile a')
            
            for tile in category_tiles:
                try:
                    tile_text = await tile.text_content()
                    href = await tile.get_attribute('href')
                    
                    if tile_text and href:
                        # Check if this tile matches our category
                        if (category.lower() in tile_text.lower() or 
                            tile_text.lower() in category.lower()):
                            logger.info(f"Found matching category tile: {tile_text}")
                            await tile.click()
                            await self.page.wait_for_load_state("networkidle")
                            await self.human_delay(2, 4)
                            return
                except Exception as e:
                    logger.debug(f"Error checking category tile: {e}")
                    continue
            
            # If no matching tile found, try direct URL construction based on FindYello's structure
            category_mappings = {
                'restaurant': 'restaurants',
                'hotel': 'hotels-resorts',
                'lawyer': 'lawyers',
                'attorney': 'lawyers',
                'gas station': 'gas-stations',
                'auto parts': 'auto-parts',
                'bar': 'bars-nightclubs',
                'nightclub': 'bars-nightclubs',
                'doctor': 'doctors',
                'hospital': 'hospitals',
                'pharmacy': 'pharmacies',
                'bank': 'banks',
                'insurance': 'insurance',
                'real estate': 'real-estate',
                'construction': 'construction',
                'mechanic': 'auto-repair',
                'plumber': 'plumbing',
                'electrician': 'electrical',
                'dentist': 'dentists'
            }
            
            # Try to map the category to FindYello's URL structure
            category_slug = category_mappings.get(category.lower(), category.lower().replace(' ', '-'))
            
            potential_urls = [
                f"{self.category_base_url}/{category_slug}/",
                f"{self.category_base_url}/{category.lower().replace(' ', '-')}/",
                f"{self.category_base_url}/{category.lower()}/",
                f"{self.base_url}/search?what={category.replace(' ', '+')}"
            ]
            
            for url in potential_urls:
                try:
                    logger.info(f"Trying category URL: {url}")
                    if not await self.safe_navigate(url):
                        continue
                    await self.human_delay(2, 4)
                    
                    # Check if we got to a valid category page
                    # Look for business listings or category content
                    listings = await self.page.query_selector_all('.carousel-card, .business-listing, .listing, .result-item')
                    if listings and len(listings) > 0:
                        logger.info(f"Successfully found category page at: {url} with {len(listings)} listings")
                        return
                        
                    # Also check for category page indicators
                    category_indicators = await self.page.query_selector_all('h1, h2, .page-title, .category-title')
                    for indicator in category_indicators:
                        text = await indicator.text_content()
                        if text and category.lower() in text.lower():
                            logger.info(f"Found category page at: {url}")
                            return
                            
                except Exception as e:
                    logger.debug(f"Category URL {url} failed: {e}")
                    continue
            
            logger.warning(f"Could not find category page for: {category}")
            
        except Exception as e:
            logger.error(f"Error in category browsing: {e}")
    
    async def _get_total_pages(self) -> int:
        """Extract total number of pages from pagination"""
        try:
            # Common pagination selectors
            pagination_selectors = [
                '.pagination a:last-child',
                '.pager a:last-child',
                '.page-numbers a:last-child',
                'a[aria-label="Last page"]',
                '.pagination-last'
            ]
            
            for selector in pagination_selectors:
                try:
                    last_page_element = await self.page.wait_for_selector(selector, timeout=3000)
                    if last_page_element:
                        page_text = await last_page_element.text_content()
                        if page_text and page_text.isdigit():
                            return int(page_text)
                        
                        # Check href for page number
                        href = await last_page_element.get_attribute('href')
                        if href:
                            page_match = re.search(r'page[=\/](\d+)', href)
                            if page_match:
                                return int(page_match.group(1))
                except:
                    continue
            
            # Look for pagination info text like "Page 1 of 5"
            pagination_info_selectors = [
                '.pagination-info',
                '.page-info',
                '.results-info'
            ]
            
            for selector in pagination_info_selectors:
                try:
                    info_element = await self.page.wait_for_selector(selector, timeout=3000)
                    if info_element:
                        info_text = await info_element.text_content()
                        page_match = re.search(r'of\s+(\d+)', info_text, re.IGNORECASE)
                        if page_match:
                            return int(page_match.group(1))
                except:
                    continue
            
            # Default to 1 page if pagination not found
            return 1
            
        except Exception as e:
            logger.warning(f"Could not determine total pages: {e}")
            return 1
    
    async def _navigate_to_page(self, page_num: int):
        """Navigate to a specific page number"""
        try:
            # Look for page link
            page_selectors = [
                f'a[href*="page={page_num}"]',
                f'a[href*="page/{page_num}"]',
                f'a:has-text("{page_num}")',
                f'.pagination a:nth-child({page_num})'
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
                    '.pagination-next',
                    'a:has-text("Next")',
                    '.pager-next a'
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
            # FindYello specific selectors based on the HTML structure
            listing_selectors = [
                '.carousel-card',  # Main business cards in carousels
                '.business-listing',
                '.listing',
                '.result-item',
                '.business-item',
                '.search-result',
                '.directory-listing',
                '.business-card',
                '.company-listing'
            ]
            
            listings = []
            used_selector = None
            
            # Try each selector to find business listings
            for selector in listing_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)
                    elements = await self.page.query_selector_all(selector)
                    if elements and len(elements) > 0:
                        listings = elements
                        used_selector = selector
                        logger.info(f"Found {len(listings)} listings using selector: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            # If no listings found, check if we're on a search results page
            if not listings:
                try:
                    # Check for "no results" or similar messages
                    no_results_selectors = [
                        '.no-results',
                        '.no-listings',
                        '.empty-results',
                        'p:has-text("No results")',
                        'div:has-text("No businesses found")'
                    ]
                    
                    for selector in no_results_selectors:
                        try:
                            element = await self.page.wait_for_selector(selector, timeout=2000)
                            if element:
                                logger.info("No results found for this search")
                                return businesses
                        except:
                            continue
                            
                    # If we're on the homepage, try to extract from carousels
                    carousel_cards = await self.page.query_selector_all('.carousel-card')
                    if carousel_cards:
                        listings = carousel_cards
                        used_selector = ".carousel-card"
                        logger.info(f"Found {len(listings)} carousel cards on homepage")
                    
                except Exception as e:
                    logger.debug(f"Error checking for no results: {e}")
            
            if not listings:
                logger.warning("No business listings found on current page")
                return businesses
            
            logger.info(f"Processing {len(listings)} business listings from current page")
            
            for i, listing in enumerate(listings):
                try:
                    business_data = await self._extract_business_from_listing(listing)
                    if business_data and business_data.name and len(business_data.name.strip()) > 2:
                        # Basic validation to ensure we have meaningful data
                        businesses.append(business_data)
                        logger.debug(f"Successfully extracted business {i+1}: {business_data.name}")
                    else:
                        logger.debug(f"Skipped business {i+1}: insufficient data")
                        
                except Exception as e:
                    logger.warning(f"Error extracting business {i+1}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error scraping current page: {e}")
            
        logger.info(f"Successfully extracted {len(businesses)} valid businesses from current page")
        return businesses
    
    async def _extract_business_from_listing(self, listing) -> Optional[BusinessData]:
        """Extract business data from a single listing element"""
        try:
            # Extract business name - FindYello specific selectors
            name_selectors = [
                '.carousel-card-content h4 a',  # Carousel card business name
                'h4 a',  # Generic h4 link
                '.business-name',
                '.company-name',
                '.listing-title',
                '.business-title',
                '.name',
                '.title',
                'h1 a', 'h2 a', 'h3 a', 'h5 a',
                'h1', 'h2', 'h3', 'h4', 'h5',
                '.title a',
                '.heading a',
                'a.black.noul',  # FindYello specific link class
                'strong'
            ]
            
            name = ""
            business_url = ""
            
            for selector in name_selectors:
                try:
                    name_element = await listing.query_selector(selector)
                    if name_element:
                        name = await name_element.text_content()
                        name = name.strip() if name else ""
                        
                        # Also get the business URL if it's a link
                        if name_element.tag_name.lower() == 'a':
                            href = await name_element.get_attribute('href')
                            if href:
                                business_url = href if href.startswith('http') else f"{self.base_url}{href}"
                        
                        # Validate name quality
                        if name and len(name) > 2 and len(name) < 200:
                            # Filter out common non-business text
                            invalid_patterns = [
                                'search', 'filter', 'sort', 'page', 'next', 'previous',
                                'home', 'about', 'contact us', 'privacy', 'terms',
                                'login', 'register', 'sign up', 'sign in',
                                'advertisement', 'sponsored', 'ad',
                                'loading', 'please wait', 'error', 'open', 'closed'
                            ]
                            name_lower = name.lower()
                            if not any(pattern in name_lower for pattern in invalid_patterns):
                                break
                        name = ""  # Reset if validation failed
                except Exception as e:
                    logger.debug(f"Name selector {selector} failed: {e}")
                    continue
            
            if not name:
                logger.debug("Could not extract business name from listing")
                return None
            
            # Extract address - look in business URL path for FindYello
            address = ""
            
            # FindYello often includes address info in the URL path
            if business_url:
                try:
                    # Extract address from URL path like "/jamaica/business-name/profile/address-info/"
                    url_parts = business_url.split('/')
                    if len(url_parts) > 4:
                        # The last part before trailing slash often contains address info
                        potential_address = url_parts[-2] if url_parts[-1] == '' else url_parts[-1]
                        if potential_address and potential_address != 'profile':
                            # Clean up the address from URL format
                            address = potential_address.replace('-', ' ').title()
                            if len(address) > 5:
                                logger.debug(f"Extracted address from URL: {address}")
                except Exception as e:
                    logger.debug(f"Error extracting address from URL: {e}")
            
            # Also try traditional address selectors
            if not address:
                address_selectors = [
                    '.address',
                    '.location',
                    '.business-address',
                    '.company-address',
                    '.listing-address',
                    '.contact-address',
                    '.street-address',
                    '[itemprop="address"]'
                ]
                
                for selector in address_selectors:
                    try:
                        address_element = await listing.query_selector(selector)
                        if address_element:
                            address = await address_element.text_content()
                            address = address.strip() if address else ""
                            if address and len(address) > 5:
                                break
                    except Exception as e:
                        logger.debug(f"Address selector {selector} failed: {e}")
                        continue
            
            # If still no address, look for Jamaican location patterns in text
            if not address:
                try:
                    all_text = await listing.text_content()
                    if all_text:
                        # Jamaican address patterns
                        jamaica_patterns = [
                            r'[^.]*(?:kingston|spanish town|montego bay|mandeville|may pen|portmore|st\.?\s*\w+)[^.]*',
                            r'[^.]*(?:\d+\s+\w+\s+(?:road|street|avenue|lane|drive|way))[^.]*',
                            r'[^.]*(?:road|street|avenue|lane|drive|way|plaza|square|crescent|close)[^.]*'
                        ]
                        
                        for pattern in jamaica_patterns:
                            match = re.search(pattern, all_text, re.IGNORECASE)
                            if match:
                                potential_address = match.group(0).strip()
                                if len(potential_address) > 10 and len(potential_address) < 200:
                                    address = potential_address
                                    break
                except Exception as e:
                    logger.debug(f"Address pattern matching failed: {e}")
            
            # Extract phone number - FindYello specific structure
            phone_selectors = [
                '.carousel-contact',  # FindYello carousel contact info
                '.phone',
                '.telephone',
                '.tel',
                '.contact-phone',
                '.business-phone',
                'a[href^="tel:"]',
                '[itemprop="telephone"]'
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
                            phone_text = await phone_element.text_content()
                            if phone_text:
                                # Extract phone number from text that might include icon or other text
                                # Look for Jamaican phone patterns first
                                phone_match = re.search(r'876[-.\s]?\d{3}[-.\s]?\d{4}', phone_text)
                                if phone_match:
                                    phone = phone_match.group(0)
                                else:
                                    # Look for any phone-like pattern but validate it's reasonable
                                    phone_match = re.search(r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}', phone_text)
                                    if phone_match:
                                        potential_phone = phone_match.group(0)
                                        # Only accept if it looks like a valid phone number
                                        digits = re.sub(r'\D', '', potential_phone)
                                        if len(digits) >= 7 and len(digits) <= 11:
                                            phone = potential_phone
                                    
                                if not phone:
                                    # Fallback to any reasonable phone-like text
                                    phone = phone_text.strip()
                        
                        if phone:
                            # Validate the extracted phone number
                            digits = re.sub(r'\D', '', phone)
                            if len(digits) >= 7 and len(digits) <= 11:
                                # Only keep Jamaican numbers or reasonable local numbers
                                if (digits.startswith('876') or 
                                    digits.startswith('1876') or 
                                    len(digits) == 7):
                                    break
                            phone = ""  # Reset if validation failed
                except Exception as e:
                    logger.debug(f"Phone selector {selector} failed: {e}")
                    continue
            
            # If no specific phone found, look for Jamaican phone patterns in all text
            if not phone:
                try:
                    all_text = await listing.text_content()
                    if all_text:
                        # Jamaican phone number patterns (prioritize Jamaica numbers)
                        phone_patterns = [
                            r'876[-.\s]?\d{3}[-.\s]?\d{4}',  # 876 area code
                            r'\+1[-.\s]?876[-.\s]?\d{3}[-.\s]?\d{4}',  # With country code
                            r'\b\d{3}[-.\s]?\d{4}\b'  # 7-digit local numbers
                        ]
                        
                        for pattern in phone_patterns:
                            match = re.search(pattern, all_text)
                            if match:
                                potential_phone = match.group(0).strip()
                                # Validate the phone number
                                digits = re.sub(r'\D', '', potential_phone)
                                if len(digits) >= 7 and len(digits) <= 11:
                                    # Prefer Jamaican numbers
                                    if (digits.startswith('876') or 
                                        digits.startswith('1876') or 
                                        len(digits) == 7):
                                        phone = potential_phone
                                        break
                except Exception as e:
                    logger.debug(f"Phone pattern matching failed: {e}")
            
            # Extract email with comprehensive selectors and patterns
            email_selectors = [
                '.email',
                '.e-mail',
                '.contact-email',
                '.business-email',
                'a[href^="mailto:"]',
                '[itemprop="email"]',
                '[data-email]'
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
                        if email and '@' in email and '.' in email:
                            break
                except Exception as e:
                    logger.debug(f"Email selector {selector} failed: {e}")
                    continue
            
            # If no specific email found, look for email patterns
            if not email:
                try:
                    all_text = await listing.text_content()
                    if all_text:
                        email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
                        match = email_pattern.search(all_text)
                        if match:
                            email = match.group(0).strip().lower()
                except Exception as e:
                    logger.debug(f"Email pattern matching failed: {e}")
            
            # Extract website
            website_selectors = [
                '.website a',
                '.url a',
                'a[href^="http"]:not([href^="mailto:"]):not([href^="tel:"])'
            ]
            
            website = ""
            for selector in website_selectors:
                try:
                    website_element = await listing.query_selector(selector)
                    if website_element:
                        website = await website_element.get_attribute('href')
                        website = website.strip() if website else ""
                        if website and not website.startswith('mailto:') and not website.startswith('tel:'):
                            break
                except:
                    continue
            
            # Extract category - try to infer from URL or page context
            category = ""
            if business_url:
                try:
                    # Extract category from URL structure like "/jamaica/restaurants/business-name/"
                    url_parts = business_url.split('/')
                    for part in url_parts:
                        if part in ['restaurants', 'hotels-resorts', 'lawyers', 'gas-stations', 
                                   'auto-parts', 'bars-nightclubs', 'doctors', 'hospitals']:
                            category = part.replace('-', ' ').title()
                            break
                except Exception as e:
                    logger.debug(f"Error extracting category from URL: {e}")
            
            # Also try traditional category selectors
            if not category:
                category_selectors = [
                    '.category',
                    '.business-type',
                    '.industry',
                    '.classification'
                ]
                
                for selector in category_selectors:
                    try:
                        category_element = await listing.query_selector(selector)
                        if category_element:
                            category = await category_element.text_content()
                            category = category.strip() if category else ""
                            if category:
                                break
                    except Exception as e:
                        logger.debug(f"Category selector {selector} failed: {e}")
                        continue
            
            # Extract description - FindYello carousel cards have description in <p> tags
            description_selectors = [
                '.carousel-card-content p',  # FindYello carousel description
                '.description',
                '.business-description',
                '.summary',
                '.company-description',
                'p'  # Generic paragraph
            ]
            
            description = ""
            for selector in description_selectors:
                try:
                    desc_element = await listing.query_selector(selector)
                    if desc_element:
                        description = await desc_element.text_content()
                        description = description.strip() if description else ""
                        # Validate description quality
                        if description and len(description) > 20 and len(description) < 1000:
                            # Filter out non-descriptive text
                            invalid_desc_patterns = [
                                'click here', 'read more', 'contact us', 'phone number',
                                'open', 'closed', 'reviews', 'rating'
                            ]
                            desc_lower = description.lower()
                            if not any(pattern in desc_lower for pattern in invalid_desc_patterns):
                                break
                        description = ""
                except Exception as e:
                    logger.debug(f"Description selector {selector} failed: {e}")
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
            
            # Extract detailed business information
            # This would be implemented based on the specific structure of business detail pages
            # For now, return None as this is typically called for additional details
            return None
            
        except Exception as e:
            logger.error(f"Error scraping business details from {business_url}: {e}")
            return None
    
    async def get_categories(self) -> List[str]:
        """Get available business categories from FindYello"""
        try:
            # Navigate to homepage
            await self.page.goto(self.base_url, wait_until="networkidle")
            await self.human_delay(2, 4)
            
            categories = []
            
            # Extract categories from category tiles on homepage
            category_tiles = await self.page.query_selector_all('.category-tile h3')
            for tile in category_tiles:
                try:
                    text = await tile.text_content()
                    if text and text.strip():
                        categories.append(text.strip())
                except Exception as e:
                    logger.debug(f"Error extracting category from tile: {e}")
                    continue
            
            # Also try to get categories from navigation menus
            nav_selectors = [
                '.dropdown-menu a',
                '.categories a',
                '.category-list a',
                'select[name="category"] option'
            ]
            
            for selector in nav_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    for element in elements:
                        text = await element.text_content()
                        if text and text.strip() and len(text.strip()) > 2:
                            categories.append(text.strip())
                except Exception as e:
                    logger.debug(f"Error with selector {selector}: {e}")
                    continue
            
            # Add common Jamaican business categories if none found
            if not categories:
                categories = [
                    "Gas Station", "Auto Parts", "Hotel", "Restaurant", "Lawyer",
                    "Bars", "Doctors", "Hospitals", "Pharmacies", "Banks",
                    "Insurance", "Real Estate", "Construction", "Auto Repair",
                    "Plumbing", "Electrical", "Dentists", "Supermarkets"
                ]
            
            return list(set(categories))  # Remove duplicates
            
        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            return []
    
    async def get_locations(self) -> List[str]:
        """Get available locations from FindYello"""
        try:
            # Navigate to main page
            await self.page.goto(self.base_url, wait_until="networkidle")
            await self.human_delay(2, 4)
            
            # Look for location options
            location_selectors = [
                '.locations a',
                '.location-list a',
                'select[name="location"] option',
                '.parishes a'
            ]
            
            locations = []
            for selector in location_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    for element in elements:
                        text = await element.text_content()
                        if text and text.strip():
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
                    "Port Antonio", "Linstead", "Half Way Tree", "Ocho Rios"
                ]
            
            return list(set(locations))  # Remove duplicates
            
        except Exception as e:
            logger.error(f"Error getting locations: {e}")
            return []