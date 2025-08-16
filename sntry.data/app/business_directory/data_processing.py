"""
Data processing and standardization services for business directory data.
Implements data cleaning, validation, address parsing, and deduplication.
"""
import re
import logging
import hashlib
import datetime
from typing import List, Optional, Dict, Any, Tuple, Set
from urllib.parse import urlparse
import unicodedata
from decimal import Decimal
from enum import Enum

logger = logging.getLogger(__name__)

try:
    from rapidfuzz import fuzz, process
    RAPIDFUZZ_AVAILABLE = True
    logger.info("RapidFuzz successfully loaded for fuzzy matching")
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    logger.warning("RapidFuzz not available. Fuzzy matching will be disabled.")

try:
    from postal.parser import parse_address
    from postal.expand import expand_address
    LIBPOSTAL_AVAILABLE = True
    logger.info("Libpostal successfully loaded for address parsing")
except ImportError:
    LIBPOSTAL_AVAILABLE = False
    logger.warning("Libpostal not available. Address parsing will use fallback method.")

from app.business_directory.schemas import BusinessData, ParsedAddress


class DuplicateType(Enum):
    """Types of duplicate detection"""
    EXACT = "exact"
    FUZZY = "fuzzy"
    NONE = "none"


class ConfidenceLevel(Enum):
    """Confidence levels for duplicate matching"""
    HIGH = "high"      # 90-100% confidence
    MEDIUM = "medium"  # 70-89% confidence
    LOW = "low"        # 50-69% confidence
    NONE = "none"      # <50% confidence


class DuplicateMatch:
    """Represents a potential duplicate match between two businesses"""
    
    def __init__(
        self,
        business1: BusinessData,
        business2: BusinessData,
        duplicate_type: DuplicateType,
        confidence_score: float,
        confidence_level: ConfidenceLevel,
        matching_fields: List[str],
        similarity_scores: Dict[str, float]
    ):
        self.business1 = business1
        self.business2 = business2
        self.duplicate_type = duplicate_type
        self.confidence_score = confidence_score
        self.confidence_level = confidence_level
        self.matching_fields = matching_fields
        self.similarity_scores = similarity_scores
        self.requires_manual_review = confidence_level in [ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW]
    
    def __repr__(self):
        return (f"DuplicateMatch(business1='{self.business1.name}', "
                f"business2='{self.business2.name}', "
                f"type={self.duplicate_type.value}, "
                f"confidence={self.confidence_score:.2f})")


class MergeDecision:
    """Represents a decision on how to merge duplicate businesses"""
    
    def __init__(
        self,
        primary_business: BusinessData,
        secondary_business: BusinessData,
        merged_data: Dict[str, Any],
        merge_strategy: str,
        confidence_score: float
    ):
        self.primary_business = primary_business
        self.secondary_business = secondary_business
        self.merged_data = merged_data
        self.merge_strategy = merge_strategy
        self.confidence_score = confidence_score


class DataCleaningService:
    """
    Service for cleaning and validating scraped business data.
    Handles business name standardization, phone number formatting,
    email validation, and website URL normalization.
    """
    
    def __init__(self):
        """Initialize the data cleaning service with validation patterns."""
        # Jamaican phone number patterns
        self.phone_patterns = {
            'local_7_digit': re.compile(r'^\d{7}$'),
            'area_code_10_digit': re.compile(r'^876\d{7}$'),
            'country_code_11_digit': re.compile(r'^1876\d{7}$'),
            'international': re.compile(r'^\+?1?876\d{7}$')
        }
        
        # Email validation pattern (basic)
        self.email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        
        # URL validation pattern
        self.url_pattern = re.compile(
            r'^https?://'
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
            r'localhost|'
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
            r'(?::\d+)?'
            r'(?:/?|[/?]\S+)$', re.IGNORECASE
        )
        
        # Common business name prefixes/suffixes to standardize
        self.business_name_patterns = {
            'ltd': ['ltd', 'ltd.', 'limited'],
            'inc': ['inc', 'inc.', 'incorporated'],
            'corp': ['corp', 'corp.', 'corporation'],
            'co': ['co', 'co.', 'company'],
            'llc': ['llc', 'l.l.c.', 'limited liability company'],
            'plc': ['plc', 'p.l.c.', 'public limited company']
        }
    
    def clean_business_data(self, raw_data: List[Dict[str, Any]]) -> List[BusinessData]:
        """
        Clean and validate a list of raw business data records.
        
        Args:
            raw_data: List of raw business data dictionaries
            
        Returns:
            List of cleaned and validated BusinessData objects
        """
        cleaned_businesses = []
        
        for idx, raw_business in enumerate(raw_data):
            try:
                cleaned_business = self._clean_single_business(raw_business)
                if cleaned_business:
                    cleaned_businesses.append(cleaned_business)
                    logger.debug(f"Successfully cleaned business {idx + 1}: {cleaned_business.name}")
                else:
                    logger.warning(f"Failed to clean business {idx + 1}: invalid data")
            except Exception as e:
                logger.error(f"Error cleaning business {idx + 1}: {str(e)}")
                continue
        
        logger.info(f"Cleaned {len(cleaned_businesses)} out of {len(raw_data)} businesses")
        return cleaned_businesses
    
    def _clean_single_business(self, raw_business: Dict[str, Any]) -> Optional[BusinessData]:
        """
        Clean and validate a single business record.
        
        Args:
            raw_business: Raw business data dictionary
            
        Returns:
            Cleaned BusinessData object or None if invalid
        """
        try:
            # Clean and validate required fields
            name = self.standardize_business_name(raw_business.get('name', ''))
            if not name or len(name.strip()) == 0:
                logger.warning("Business name is empty or invalid")
                return None
            
            raw_address = raw_business.get('raw_address', '').strip()
            if not raw_address:
                logger.warning("Raw address is empty")
                return None
            
            source_url = raw_business.get('source_url', '').strip()
            if not source_url:
                logger.warning("Source URL is empty")
                return None
            
            # Clean optional fields
            category = self._clean_category(raw_business.get('category'))
            phone_number = self.format_jamaican_phone_number(raw_business.get('phone_number'))
            email = self.validate_and_normalize_email(raw_business.get('email'))
            website = self.validate_and_normalize_website(raw_business.get('website'))
            description = self._clean_description(raw_business.get('description'))
            operating_hours = self._clean_operating_hours(raw_business.get('operating_hours'))
            rating = self._clean_rating(raw_business.get('rating'))
            
            # Create BusinessData object
            business_data = BusinessData(
                name=name,
                category=category,
                raw_address=raw_address,
                phone_number=phone_number,
                email=email,
                website=website,
                description=description,
                operating_hours=operating_hours,
                rating=rating,
                source_url=source_url,
                last_scraped_at=raw_business.get('last_scraped_at'),
                scrape_status=raw_business.get('scrape_status', 'pending'),
                geocode_status=raw_business.get('geocode_status', 'pending'),
                is_active=raw_business.get('is_active', True)
            )
            
            return business_data
            
        except Exception as e:
            logger.error(f"Error processing business data: {str(e)}")
            return None
    
    def standardize_business_name(self, name: str) -> str:
        """
        Standardize business name by removing extra spaces, fixing capitalization,
        and normalizing common business suffixes.
        
        Args:
            name: Raw business name
            
        Returns:
            Standardized business name
        """
        if not name:
            return ""
        
        # Remove extra whitespace and normalize unicode
        name = unicodedata.normalize('NFKD', name.strip())
        
        # Remove multiple spaces
        name = re.sub(r'\s+', ' ', name)
        
        # Convert to title case but preserve all caps words (likely acronyms)
        words = name.split()
        standardized_words = []
        
        for word in words:
            # Keep all-caps words as they are (likely acronyms)
            if word.isupper() and len(word) > 1:
                standardized_words.append(word)
            # Keep words with mixed case that look intentional
            elif any(c.isupper() for c in word[1:]) and any(c.islower() for c in word):
                standardized_words.append(word)
            # Otherwise, convert to title case
            else:
                standardized_words.append(word.title())
        
        name = ' '.join(standardized_words)
        
        # Standardize common business suffixes
        name_lower = name.lower()
        for standard_suffix, variations in self.business_name_patterns.items():
            for variation in variations:
                pattern = rf'\b{re.escape(variation)}\b$'
                if re.search(pattern, name_lower):
                    name = re.sub(pattern, standard_suffix.upper(), name, flags=re.IGNORECASE)
                    break
        
        return name.strip()
    
    def format_jamaican_phone_number(self, phone: str) -> Optional[str]:
        """
        Format and validate Jamaican phone numbers.
        
        Args:
            phone: Raw phone number string
            
        Returns:
            Formatted phone number or None if invalid
        """
        if not phone:
            return None
        
        # Remove all non-digit characters
        digits_only = re.sub(r'\D', '', phone)
        
        if not digits_only:
            return None
        
        # Format based on length and pattern
        if len(digits_only) == 7:
            # Local 7-digit number: format as XXX-XXXX
            return f"{digits_only[:3]}-{digits_only[3:]}"
        elif len(digits_only) == 10 and digits_only.startswith('876'):
            # 10-digit with area code: format as (876) XXX-XXXX
            return f"(876) {digits_only[3:6]}-{digits_only[6:]}"
        elif len(digits_only) == 11 and digits_only.startswith('1876'):
            # 11-digit with country code: format as +1 (876) XXX-XXXX
            return f"+1 (876) {digits_only[4:7]}-{digits_only[7:]}"
        else:
            # Invalid format
            logger.warning(f"Invalid Jamaican phone number format: {phone}")
            return None
    
    def validate_and_normalize_email(self, email: str) -> Optional[str]:
        """
        Validate and normalize email addresses.
        
        Args:
            email: Raw email string
            
        Returns:
            Normalized email or None if invalid
        """
        if not email:
            return None
        
        # Clean and normalize
        email = email.strip().lower()
        
        # Basic email validation
        if not self.email_pattern.match(email):
            logger.warning(f"Invalid email format: {email}")
            return None
        
        return email
    
    def validate_and_normalize_website(self, website: str) -> Optional[str]:
        """
        Validate and normalize website URLs.
        
        Args:
            website: Raw website URL
            
        Returns:
            Normalized URL or None if invalid
        """
        if not website:
            return None
        
        website = website.strip()
        
        # Add protocol if missing
        if not website.startswith(('http://', 'https://')):
            website = f"https://{website}"
        
        # Validate URL format
        if not self.url_pattern.match(website):
            logger.warning(f"Invalid website URL format: {website}")
            return None
        
        # Parse and normalize
        try:
            parsed = urlparse(website)
            # Reconstruct URL with normalized components
            normalized_url = f"{parsed.scheme}://{parsed.netloc.lower()}{parsed.path}"
            if parsed.query:
                normalized_url += f"?{parsed.query}"
            if parsed.fragment:
                normalized_url += f"#{parsed.fragment}"
            
            return normalized_url
        except Exception as e:
            logger.warning(f"Error normalizing website URL {website}: {str(e)}")
            return None
    
    def _clean_category(self, category: str) -> Optional[str]:
        """Clean and standardize business category."""
        if not category:
            return None
        
        category = category.strip().title()
        return category if len(category) > 0 else None
    
    def _clean_description(self, description: str) -> Optional[str]:
        """Clean business description text."""
        if not description:
            return None
        
        # Remove extra whitespace and normalize
        description = unicodedata.normalize('NFKD', description.strip())
        description = re.sub(r'\s+', ' ', description)
        
        return description if len(description) > 0 else None
    
    def _clean_operating_hours(self, hours: str) -> Optional[str]:
        """Clean operating hours text."""
        if not hours:
            return None
        
        hours = hours.strip()
        return hours if len(hours) > 0 else None
    
    def _clean_rating(self, rating: Any) -> Optional[float]:
        """Clean and validate business rating."""
        if rating is None:
            return None
        
        try:
            rating_float = float(rating)
            if 0 <= rating_float <= 5:
                return rating_float
            else:
                logger.warning(f"Rating out of range (0-5): {rating}")
                return None
        except (ValueError, TypeError):
            logger.warning(f"Invalid rating format: {rating}")
            return None
    
    def remove_invalid_entries(self, businesses: List[BusinessData]) -> List[BusinessData]:
        """
        Remove business entries that don't meet minimum quality standards.
        
        Args:
            businesses: List of business data
            
        Returns:
            Filtered list of valid businesses
        """
        valid_businesses = []
        
        for business in businesses:
            if self._is_valid_business_entry(business):
                valid_businesses.append(business)
            else:
                logger.info(f"Removing invalid business entry: {business.name}")
        
        logger.info(f"Kept {len(valid_businesses)} out of {len(businesses)} businesses after validation")
        return valid_businesses
    
    def _is_valid_business_entry(self, business: BusinessData) -> bool:
        """
        Check if a business entry meets minimum quality standards.
        
        Args:
            business: Business data to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Must have name and address
        if not business.name or not business.raw_address:
            return False
        
        # Name must be reasonable length
        if len(business.name.strip()) < 2:
            return False
        
        # Address must be reasonable length
        if len(business.raw_address.strip()) < 5:
            return False
        
        # Must have at least one contact method (phone, email, or website)
        if not any([business.phone_number, business.email, business.website]):
            logger.debug(f"Business {business.name} has no contact information")
            # Don't reject, but log for review
        
        return True


class AddressParsingService:
    """
    Service for parsing and standardizing Jamaican addresses using Libpostal.
    Falls back to custom parsing logic when Libpostal is not available.
    Implements Jamaican-specific address standardization rules.
    """
    
    def __init__(self):
        """Initialize the address parsing service with Jamaican-specific patterns."""
        self.use_libpostal = LIBPOSTAL_AVAILABLE
        # Jamaican parishes
        self.parishes = {
            'KINGSTON', 'ST. ANDREW', 'ST. THOMAS', 'PORTLAND', 'ST. MARY',
            'ST. ANN', 'TRELAWNY', 'ST. JAMES', 'HANOVER', 'WESTMORELAND',
            'ST. ELIZABETH', 'MANCHESTER', 'CLARENDON', 'ST. CATHERINE'
        }
        
        # Common Jamaican cities/towns
        self.cities = {
            'KINGSTON', 'SPANISH TOWN', 'PORTMORE', 'MONTEGO BAY', 'MAY PEN',
            'MANDEVILLE', 'OLD HARBOUR', 'SAVANNA-LA-MAR', 'OCHO RIOS',
            'PORT ANTONIO', 'LINSTEAD', 'HALF WAY TREE', 'CROSS ROADS',
            'NEW KINGSTON', 'DOWNTOWN', 'UPTOWN', 'PAPINE', 'LIGUANEA',
            'CONSTANT SPRING', 'HOPE PASTURES', 'BARBICAN', 'MEADOWBROOK'
        }
        
        # Postal zone pattern (e.g., KINGSTON 10, SPANISH TOWN 01)
        self.postal_zone_pattern = re.compile(r'\b([A-Z\s]+)\s+(\d{2})\b')
        
        # PO Box pattern
        self.po_box_pattern = re.compile(r'\b(?:P\.?O\.?\s*BOX|POST\s*OFFICE\s*BOX)\s*(\d+)\b', re.IGNORECASE)
        
        # House number patterns
        self.house_number_pattern = re.compile(r'^\s*(\d+[A-Z]?)\s+')
        
        # Street type abbreviations
        self.street_types = {
            'ST': 'STREET', 'ST.': 'STREET', 'STR': 'STREET', 'STREET': 'STREET',
            'RD': 'ROAD', 'RD.': 'ROAD', 'ROAD': 'ROAD',
            'AVE': 'AVENUE', 'AVE.': 'AVENUE', 'AVENUE': 'AVENUE',
            'BLVD': 'BOULEVARD', 'BLVD.': 'BOULEVARD', 'BOULEVARD': 'BOULEVARD',
            'DR': 'DRIVE', 'DR.': 'DRIVE', 'DRIVE': 'DRIVE',
            'LN': 'LANE', 'LANE': 'LANE',
            'CT': 'COURT', 'COURT': 'COURT',
            'PL': 'PLACE', 'PLACE': 'PLACE',
            'WAY': 'WAY', 'CRESCENT': 'CRESCENT', 'CLOSE': 'CLOSE',
            'GARDENS': 'GARDENS', 'HEIGHTS': 'HEIGHTS', 'PLAZA': 'PLAZA'
        }
    
    def parse_address(self, raw_address: str) -> ParsedAddress:
        """
        Parse a raw Jamaican address into standardized components using Libpostal.
        Falls back to custom parsing when Libpostal is not available.
        
        Args:
            raw_address: Raw address string
            
        Returns:
            ParsedAddress object with parsed components
        """
        if not raw_address:
            raise ValueError("Address cannot be empty")
        
        if self.use_libpostal:
            return self._parse_with_libpostal(raw_address)
        else:
            return self._parse_with_fallback(raw_address)
    
    def _parse_with_libpostal(self, raw_address: str) -> ParsedAddress:
        """
        Parse address using Libpostal with Jamaican-specific post-processing.
        
        Args:
            raw_address: Raw address string
            
        Returns:
            ParsedAddress object with parsed components
        """
        try:
            # Clean and normalize the address first
            cleaned_address = self._clean_address(raw_address)
            
            # Use Libpostal to parse the address
            parsed_components = parse_address(cleaned_address)
            
            # Initialize components dictionary
            components = {
                'house_number': None,
                'street_name': None,
                'po_box': None,
                'postal_zone': None,
                'city': None,
                'parish': None,
                'country': 'JAMAICA',
                'formatted_address': cleaned_address
            }
            
            # Map Libpostal components to our schema
            for component, label in parsed_components:
                component = component.strip()
                
                if label == 'house_number':
                    components['house_number'] = component
                elif label in ['road', 'street']:
                    if components['street_name']:
                        components['street_name'] += f" {component}"
                    else:
                        components['street_name'] = component
                elif label in ['city', 'suburb', 'neighbourhood']:
                    if not components['city']:  # Use first city-like component
                        components['city'] = component.upper()
                elif label == 'postcode':
                    # Handle Jamaican postal zones
                    if re.match(r'^[A-Z\s]+ \d{2}$', component.upper()):
                        components['postal_zone'] = component.upper()
                        if not components['city']:
                            city_part = component.upper().split()[0]
                            components['city'] = city_part
                elif label in ['state', 'state_district']:
                    # In Jamaica, this might be a parish
                    parish_candidate = component.upper()
                    if parish_candidate in self.parishes:
                        components['parish'] = parish_candidate
                elif label == 'country':
                    components['country'] = component.upper()
            
            # Post-process with Jamaican-specific logic
            components = self._post_process_libpostal_components(components, raw_address)
            
            # Standardize street name
            if components['street_name']:
                components['street_name'] = self._standardize_street_name(components['street_name'])
            
            # Create formatted address
            components['formatted_address'] = self._format_address(components)
            
            return ParsedAddress(**components)
            
        except Exception as e:
            logger.warning(f"Libpostal parsing failed for '{raw_address}': {str(e)}. Using fallback method.")
            return self._parse_with_fallback(raw_address)
    
    def _post_process_libpostal_components(self, components: Dict[str, Optional[str]], raw_address: str) -> Dict[str, Optional[str]]:
        """
        Post-process Libpostal components with Jamaican-specific logic.
        
        Args:
            components: Components dictionary from Libpostal
            raw_address: Original raw address
            
        Returns:
            Enhanced components dictionary
        """
        # Extract PO Box if not found by Libpostal
        if not components['po_box']:
            po_box_match = self.po_box_pattern.search(raw_address.upper())
            if po_box_match:
                components['po_box'] = f"PO BOX {po_box_match.group(1)}"
        
        # Extract postal zone if not found
        if not components['postal_zone']:
            postal_match = self.postal_zone_pattern.search(raw_address.upper())
            if postal_match:
                city_part = postal_match.group(1).strip()
                zone_part = postal_match.group(2)
                components['postal_zone'] = f"{city_part} {zone_part}"
                if not components['city']:
                    components['city'] = city_part
        
        # Try to identify city if not found
        if not components['city']:
            components['city'] = self._extract_city(raw_address)
        
        # Ensure we have at least a city (required field)
        if not components['city']:
            components['city'] = "UNKNOWN"
        
        # Try to identify parish if not found
        if not components['parish']:
            components['parish'] = self._extract_parish(raw_address)
        
        # Ensure city is uppercase for consistency
        if components['city']:
            components['city'] = components['city'].upper()
        
        return components
    
    def _parse_with_fallback(self, raw_address: str) -> ParsedAddress:
        """
        Parse address using fallback method when Libpostal is not available.
        
        Args:
            raw_address: Raw address string
            
        Returns:
            ParsedAddress object with parsed components
        """
        # Clean and normalize the address
        address = self._clean_address(raw_address)
        
        # Initialize components
        components = {
            'house_number': None,
            'street_name': None,
            'po_box': None,
            'postal_zone': None,
            'city': None,
            'parish': None,
            'country': 'JAMAICA',
            'formatted_address': address
        }
        
        # Extract PO Box if present
        po_box_match = self.po_box_pattern.search(address)
        if po_box_match:
            components['po_box'] = f"PO BOX {po_box_match.group(1)}"
            # Remove PO Box from address for further parsing
            address = self.po_box_pattern.sub('', address).strip()
        
        # Extract postal zone (e.g., "KINGSTON 10")
        postal_match = self.postal_zone_pattern.search(address)
        if postal_match:
            city_part = postal_match.group(1).strip()
            zone_part = postal_match.group(2)
            components['postal_zone'] = f"{city_part} {zone_part}"
            components['city'] = city_part
            # Remove postal zone from address
            address = self.postal_zone_pattern.sub('', address).strip()
        
        # Extract house number
        house_match = self.house_number_pattern.match(address)
        if house_match:
            components['house_number'] = house_match.group(1)
            # Remove house number from address
            address = self.house_number_pattern.sub('', address).strip()
        
        # Extract street name and standardize (remaining text after removing other components)
        if address:
            # Remove city and parish from the remaining address text
            remaining_address = address
            if components['city']:
                remaining_address = remaining_address.replace(components['city'], '').strip()
            if components['parish'] and components['parish'] != components['city']:
                remaining_address = remaining_address.replace(components['parish'], '').strip()
            
            # Clean up remaining commas and spaces
            remaining_address = re.sub(r'^[,\s]+|[,\s]+$', '', remaining_address)
            remaining_address = re.sub(r'\s*,\s*', ' ', remaining_address)
            
            if remaining_address:
                street_name = self._standardize_street_name(remaining_address)
                components['street_name'] = street_name
        
        # Try to identify city if not found in postal zone
        if not components['city']:
            components['city'] = self._extract_city(raw_address)
        
        # Ensure we have at least a city (required field)
        if not components['city']:
            components['city'] = "UNKNOWN"
        
        # Try to identify parish
        components['parish'] = self._extract_parish(raw_address)
        
        # Create formatted address
        components['formatted_address'] = self._format_address(components)
        
        return ParsedAddress(**components)
    
    def _clean_address(self, address: str) -> str:
        """Clean and normalize address string."""
        # Remove extra whitespace and normalize
        address = unicodedata.normalize('NFKD', address.strip().upper())
        address = re.sub(r'\s+', ' ', address)
        
        # Remove common prefixes
        address = re.sub(r'^(ADDRESS:|LOCATED AT:|AT:)\s*', '', address)
        
        # Standardize common abbreviations
        address = re.sub(r'\bJAMAICA\b.*$', 'JAMAICA', address)
        address = re.sub(r'\bW\.?I\.?\b', 'WEST INDIES', address)
        
        return address.strip()
    
    def _standardize_street_name(self, street_text: str) -> str:
        """Standardize street name by expanding abbreviations."""
        words = street_text.split()
        standardized_words = []
        
        for word in words:
            # Remove punctuation for lookup
            clean_word = word.rstrip('.,')
            if clean_word in self.street_types:
                standardized_words.append(self.street_types[clean_word])
            else:
                standardized_words.append(word)
        
        return ' '.join(standardized_words)
    
    def _extract_city(self, address: str) -> Optional[str]:
        """Extract city name from address."""
        address_upper = address.upper()
        
        # Check for known cities
        for city in self.cities:
            if city in address_upper:
                return city
        
        # If no known city found, try to extract from context
        # Look for patterns like "... in CITY_NAME" or "CITY_NAME, JAMAICA"
        city_patterns = [
            r'\bIN\s+([A-Z\s]+?)(?:\s*,|\s*JAMAICA|\s*$)',
            r'\b([A-Z\s]+?)\s*,\s*JAMAICA',
            r'\b([A-Z\s]+?)\s+\d{2}\b'  # City before postal zone
        ]
        
        for pattern in city_patterns:
            match = re.search(pattern, address_upper)
            if match:
                potential_city = match.group(1).strip()
                if len(potential_city) > 2 and potential_city not in ['JAMAICA', 'WEST INDIES']:
                    return potential_city
        
        return None
    
    def _extract_parish(self, address: str) -> Optional[str]:
        """Extract parish name from address."""
        address_upper = address.upper()
        
        for parish in self.parishes:
            if parish in address_upper:
                return parish
        
        return None
    
    def _format_address(self, components: Dict[str, Optional[str]]) -> str:
        """Format address components into a standardized address string."""
        parts = []
        
        # Add house number and street
        if components['house_number'] and components['street_name']:
            parts.append(f"{components['house_number']} {components['street_name']}")
        elif components['street_name']:
            parts.append(components['street_name'])
        elif components['house_number']:
            parts.append(components['house_number'])
        
        # Add PO Box
        if components['po_box']:
            parts.append(components['po_box'])
        
        # Add postal zone or city
        if components['postal_zone']:
            parts.append(components['postal_zone'])
        elif components['city']:
            parts.append(components['city'])
        
        # Add parish if different from city
        if components['parish'] and components['parish'] != components['city']:
            parts.append(components['parish'])
        
        # Add country
        parts.append(components['country'])
        
        return ', '.join(filter(None, parts))
    
    def validate_parsed_address(self, parsed_address: ParsedAddress) -> Tuple[bool, List[str]]:
        """
        Validate a parsed address and return comprehensive validation results.
        
        Args:
            parsed_address: ParsedAddress object to validate
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check if we have at least some address information
        has_street_info = bool(parsed_address.house_number or parsed_address.street_name)
        has_po_box = bool(parsed_address.po_box)
        
        if not has_street_info and not has_po_box:
            issues.append("No street address or PO Box found")
        
        # Check if city is present
        if not parsed_address.city:
            issues.append("No city identified")
        elif parsed_address.city not in self.cities and not any(city in parsed_address.city for city in self.cities):
            issues.append(f"Unrecognized city: {parsed_address.city}")
        
        # Validate postal zone format if present
        if parsed_address.postal_zone:
            if not self.postal_zone_pattern.match(parsed_address.postal_zone):
                issues.append("Invalid postal zone format")
            else:
                # Check if postal zone city matches the identified city
                postal_city = parsed_address.postal_zone.split()[0]
                if parsed_address.city and postal_city != parsed_address.city:
                    issues.append("Postal zone city doesn't match identified city")
        
        # Validate parish if present
        if parsed_address.parish and parsed_address.parish not in self.parishes:
            issues.append("Invalid or unrecognized parish")
        
        # Check country
        if parsed_address.country != 'JAMAICA':
            issues.append("Country should be JAMAICA")
        
        # Validate house number format if present
        if parsed_address.house_number:
            if not re.match(r'^\d+[A-Z]?$', parsed_address.house_number):
                issues.append("Invalid house number format")
        
        # Check for completeness
        completeness_score = self.calculate_completeness_score(parsed_address)
        if completeness_score < 0.3:
            issues.append("Address has very low completeness score")
        
        is_valid = len(issues) == 0
        return is_valid, issues
    
    def calculate_completeness_score(self, parsed_address: ParsedAddress) -> float:
        """
        Calculate a comprehensive completeness score (0-1) for a parsed address.
        Uses weighted scoring based on importance for geocoding and identification.
        
        Args:
            parsed_address: ParsedAddress object to score
            
        Returns:
            Completeness score between 0 and 1
        """
        score = 0.0
        
        # Core address components (weighted by importance)
        if parsed_address.house_number:
            score += 1.0  # House number helps with precise location
        
        if parsed_address.street_name:
            score += 2.0  # Street name is crucial for geocoding
            # Bonus for complete street names (not just abbreviations)
            if len(parsed_address.street_name) > 5:
                score += 0.5
        
        if parsed_address.po_box:
            score += 1.5  # PO Box is alternative to street address
        
        if parsed_address.city:
            score += 2.0  # City is essential for location
            # Bonus for recognized cities
            if parsed_address.city in self.cities:
                score += 0.5
        
        if parsed_address.postal_zone:
            score += 1.5  # Postal zone provides precise area identification
            # Bonus for valid format
            if self.postal_zone_pattern.match(parsed_address.postal_zone):
                score += 0.5
        
        if parsed_address.parish:
            score += 1.0  # Parish provides regional context
            # Bonus for valid parish
            if parsed_address.parish in self.parishes:
                score += 0.5
        
        if parsed_address.country == 'JAMAICA':
            score += 0.5  # Country confirmation
        
        # Bonus for having both street address and postal zone
        has_street = bool(parsed_address.house_number or parsed_address.street_name)
        if has_street and parsed_address.postal_zone:
            score += 1.0
        
        # Bonus for having both PO Box and postal zone
        if parsed_address.po_box and parsed_address.postal_zone:
            score += 1.0
        
        # Maximum possible score calculation
        max_possible_score = 10.0  # Adjusted for all bonuses
        
        # Normalize to 0-1 scale
        normalized_score = min(score / max_possible_score, 1.0)
        
        return round(normalized_score, 3)
    
    def standardize_addresses(self, addresses: List[str]) -> List[ParsedAddress]:
        """
        Parse and standardize a list of addresses.
        
        Args:
            addresses: List of raw address strings
            
        Returns:
            List of ParsedAddress objects
        """
        parsed_addresses = []
        
        for idx, address in enumerate(addresses):
            try:
                parsed = self.parse_address(address)
                parsed_addresses.append(parsed)
                logger.debug(f"Successfully parsed address {idx + 1}: {address}")
            except Exception as e:
                logger.error(f"Error parsing address {idx + 1} '{address}': {str(e)}")
                # Create a minimal ParsedAddress with the raw address
                parsed_addresses.append(ParsedAddress(
                    city="UNKNOWN",
                    country="JAMAICA",
                    formatted_address=address
                ))
        
        logger.info(f"Parsed {len(parsed_addresses)} addresses")
        return parsed_addresses
    
    def expand_address_variations(self, address: str) -> List[str]:
        """
        Generate address variations using Libpostal's expand_address function.
        This helps with geocoding by providing multiple standardized formats.
        
        Args:
            address: Address string to expand
            
        Returns:
            List of address variations
        """
        if not self.use_libpostal:
            logger.warning("Libpostal not available for address expansion")
            return [address]
        
        try:
            # Clean the address first
            cleaned_address = self._clean_address(address)
            
            # Use Libpostal to expand address variations
            expansions = expand_address(cleaned_address)
            
            # Remove duplicates while preserving order
            unique_expansions = []
            seen = set()
            for expansion in expansions:
                if expansion not in seen:
                    unique_expansions.append(expansion)
                    seen.add(expansion)
            
            logger.debug(f"Generated {len(unique_expansions)} address variations for: {address}")
            return unique_expansions
            
        except Exception as e:
            logger.error(f"Error expanding address '{address}': {str(e)}")
            return [address]
    
    def standardize_address_for_geocoding(self, parsed_address: ParsedAddress) -> List[str]:
        """
        Generate standardized address formats optimized for geocoding.
        Combines Libpostal expansion with Jamaican-specific formatting.
        
        Args:
            parsed_address: ParsedAddress object
            
        Returns:
            List of standardized address strings for geocoding
        """
        geocoding_candidates = []
        
        # Start with the formatted address
        base_address = parsed_address.formatted_address
        
        # Generate variations using Libpostal if available
        if self.use_libpostal:
            expansions = self.expand_address_variations(base_address)
            geocoding_candidates.extend(expansions)
        else:
            geocoding_candidates.append(base_address)
        
        # Add Jamaican-specific variations
        jamaican_variations = self._generate_jamaican_address_variations(parsed_address)
        geocoding_candidates.extend(jamaican_variations)
        
        # Remove duplicates while preserving order
        unique_candidates = []
        seen = set()
        for candidate in geocoding_candidates:
            if candidate not in seen:
                unique_candidates.append(candidate)
                seen.add(candidate)
        
        logger.debug(f"Generated {len(unique_candidates)} geocoding candidates")
        return unique_candidates
    
    def _generate_jamaican_address_variations(self, parsed_address: ParsedAddress) -> List[str]:
        """
        Generate Jamaican-specific address variations for better geocoding success.
        
        Args:
            parsed_address: ParsedAddress object
            
        Returns:
            List of Jamaican-specific address variations
        """
        variations = []
        
        # Build base components
        street_part = ""
        if parsed_address.house_number and parsed_address.street_name:
            street_part = f"{parsed_address.house_number} {parsed_address.street_name}"
        elif parsed_address.street_name:
            street_part = parsed_address.street_name
        elif parsed_address.house_number:
            street_part = parsed_address.house_number
        
        # Variation 1: Street + Postal Zone + Country
        if street_part and parsed_address.postal_zone:
            variations.append(f"{street_part}, {parsed_address.postal_zone}, Jamaica")
        
        # Variation 2: Street + City + Parish + Country
        if street_part and parsed_address.city:
            city_part = parsed_address.city
            if parsed_address.parish and parsed_address.parish != parsed_address.city:
                city_part += f", {parsed_address.parish}"
            variations.append(f"{street_part}, {city_part}, Jamaica")
        
        # Variation 3: PO Box + Postal Zone + Country
        if parsed_address.po_box and parsed_address.postal_zone:
            variations.append(f"{parsed_address.po_box}, {parsed_address.postal_zone}, Jamaica")
        
        # Variation 4: PO Box + City + Country
        if parsed_address.po_box and parsed_address.city:
            variations.append(f"{parsed_address.po_box}, {parsed_address.city}, Jamaica")
        
        # Variation 5: Just City + Parish + Country (for general area)
        if parsed_address.city:
            city_part = parsed_address.city
            if parsed_address.parish and parsed_address.parish != parsed_address.city:
                city_part += f", {parsed_address.parish}"
            variations.append(f"{city_part}, Jamaica")
        
        # Variation 6: Postal Zone + Country (for general area)
        if parsed_address.postal_zone:
            variations.append(f"{parsed_address.postal_zone}, Jamaica")
        
        return variations


class DeduplicationEngine:
    """
    Advanced deduplication engine for business data using exact and fuzzy matching.
    Implements confidence scoring and business rules for merging duplicate records.
    """
    
    def __init__(self, fuzzy_threshold: float = 80.0, exact_match_fields: List[str] = None):
        """
        Initialize the deduplication engine.
        
        Args:
            fuzzy_threshold: Minimum similarity score for fuzzy matching (0-100)
            exact_match_fields: Fields that must match exactly for exact duplicates
        """
        self.fuzzy_threshold = fuzzy_threshold
        self.exact_match_fields = exact_match_fields or ['name', 'raw_address']
        self.use_fuzzy_matching = RAPIDFUZZ_AVAILABLE
        
        # Weights for different fields in similarity calculation
        self.field_weights = {
            'name': 0.4,
            'raw_address': 0.3,
            'phone_number': 0.15,
            'email': 0.1,
            'website': 0.05
        }
        
        # Confidence thresholds
        self.confidence_thresholds = {
            ConfidenceLevel.HIGH: 90.0,
            ConfidenceLevel.MEDIUM: 70.0,
            ConfidenceLevel.LOW: 50.0
        }
    
    def find_duplicates(self, businesses: List[BusinessData]) -> List[DuplicateMatch]:
        """
        Find all duplicate matches in a list of businesses.
        
        Args:
            businesses: List of business data to check for duplicates
            
        Returns:
            List of DuplicateMatch objects representing potential duplicates
        """
        if not businesses:
            return []
        
        logger.info(f"Starting duplicate detection for {len(businesses)} businesses")
        
        duplicate_matches = []
        processed_pairs = set()
        
        # Compare each business with every other business
        for i, business1 in enumerate(businesses):
            for j, business2 in enumerate(businesses[i + 1:], i + 1):
                # Skip if we've already processed this pair
                pair_key = tuple(sorted([business1.source_url, business2.source_url]))
                if pair_key in processed_pairs:
                    continue
                processed_pairs.add(pair_key)
                
                # Check for exact duplicates first
                exact_match = self._check_exact_duplicate(business1, business2)
                if exact_match:
                    duplicate_matches.append(exact_match)
                    continue
                
                # Check for fuzzy duplicates if exact match not found
                if self.use_fuzzy_matching:
                    fuzzy_match = self._check_fuzzy_duplicate(business1, business2)
                    if fuzzy_match:
                        duplicate_matches.append(fuzzy_match)
        
        logger.info(f"Found {len(duplicate_matches)} potential duplicate matches")
        return duplicate_matches
    
    def _check_exact_duplicate(self, business1: BusinessData, business2: BusinessData) -> Optional[DuplicateMatch]:
        """
        Check if two businesses are exact duplicates using hash comparison.
        
        Args:
            business1: First business to compare
            business2: Second business to compare
            
        Returns:
            DuplicateMatch object if exact duplicate found, None otherwise
        """
        # Generate hashes for exact match fields
        hash1 = self._generate_business_hash(business1)
        hash2 = self._generate_business_hash(business2)
        
        if hash1 == hash2:
            matching_fields = self.exact_match_fields.copy()
            similarity_scores = {field: 100.0 for field in matching_fields}
            
            return DuplicateMatch(
                business1=business1,
                business2=business2,
                duplicate_type=DuplicateType.EXACT,
                confidence_score=100.0,
                confidence_level=ConfidenceLevel.HIGH,
                matching_fields=matching_fields,
                similarity_scores=similarity_scores
            )
        
        return None
    
    def _check_fuzzy_duplicate(self, business1: BusinessData, business2: BusinessData) -> Optional[DuplicateMatch]:
        """
        Check if two businesses are fuzzy duplicates using RapidFuzz.
        
        Args:
            business1: First business to compare
            business2: Second business to compare
            
        Returns:
            DuplicateMatch object if fuzzy duplicate found, None otherwise
        """
        if not self.use_fuzzy_matching:
            return None
        
        # Calculate similarity scores for each field
        similarity_scores = {}
        weighted_score = 0.0
        matching_fields = []
        
        # Compare business names
        name_similarity = self._calculate_field_similarity(
            business1.name, business2.name, 'name'
        )
        similarity_scores['name'] = name_similarity
        weighted_score += name_similarity * self.field_weights['name']
        
        if name_similarity >= self.fuzzy_threshold:
            matching_fields.append('name')
        
        # Compare addresses
        address_similarity = self._calculate_field_similarity(
            business1.raw_address, business2.raw_address, 'address'
        )
        similarity_scores['raw_address'] = address_similarity
        weighted_score += address_similarity * self.field_weights['raw_address']
        
        if address_similarity >= self.fuzzy_threshold:
            matching_fields.append('raw_address')
        
        # Compare phone numbers (if both exist)
        if business1.phone_number and business2.phone_number:
            phone_similarity = self._calculate_field_similarity(
                business1.phone_number, business2.phone_number, 'phone'
            )
            similarity_scores['phone_number'] = phone_similarity
            weighted_score += phone_similarity * self.field_weights['phone_number']
            
            if phone_similarity >= self.fuzzy_threshold:
                matching_fields.append('phone_number')
        
        # Compare emails (if both exist)
        if business1.email and business2.email:
            email_similarity = self._calculate_field_similarity(
                business1.email, business2.email, 'email'
            )
            similarity_scores['email'] = email_similarity
            weighted_score += email_similarity * self.field_weights['email']
            
            if email_similarity >= self.fuzzy_threshold:
                matching_fields.append('email')
        
        # Compare websites (if both exist)
        if business1.website and business2.website:
            website_similarity = self._calculate_field_similarity(
                business1.website, business2.website, 'website'
            )
            similarity_scores['website'] = website_similarity
            weighted_score += website_similarity * self.field_weights['website']
            
            if website_similarity >= self.fuzzy_threshold:
                matching_fields.append('website')
        
        # Determine if this is a fuzzy duplicate
        if weighted_score >= self.fuzzy_threshold:
            confidence_level = self._determine_confidence_level(weighted_score)
            
            return DuplicateMatch(
                business1=business1,
                business2=business2,
                duplicate_type=DuplicateType.FUZZY,
                confidence_score=weighted_score,
                confidence_level=confidence_level,
                matching_fields=matching_fields,
                similarity_scores=similarity_scores
            )
        
        return None
    
    def _calculate_field_similarity(self, value1: str, value2: str, field_type: str) -> float:
        """
        Calculate similarity score between two field values.
        
        Args:
            value1: First value to compare
            value2: Second value to compare
            field_type: Type of field being compared
            
        Returns:
            Similarity score (0-100)
        """
        if not value1 or not value2:
            return 0.0
        
        # Normalize values for comparison
        norm_value1 = self._normalize_for_comparison(value1, field_type)
        norm_value2 = self._normalize_for_comparison(value2, field_type)
        
        if norm_value1 == norm_value2:
            return 100.0
        
        # Use different fuzzy matching strategies based on field type
        if field_type == 'name':
            # For business names, use token sort ratio for better handling of word order
            return fuzz.token_sort_ratio(norm_value1, norm_value2)
        elif field_type == 'address':
            # For addresses, use token set ratio to handle different formatting
            return fuzz.token_set_ratio(norm_value1, norm_value2)
        elif field_type == 'phone':
            # For phone numbers, extract digits and compare
            digits1 = re.sub(r'\D', '', norm_value1)
            digits2 = re.sub(r'\D', '', norm_value2)
            return fuzz.ratio(digits1, digits2)
        elif field_type in ['email', 'website']:
            # For emails and websites, use simple ratio
            return fuzz.ratio(norm_value1, norm_value2)
        else:
            # Default to simple ratio
            return fuzz.ratio(norm_value1, norm_value2)
    
    def _normalize_for_comparison(self, value: str, field_type: str) -> str:
        """
        Normalize a field value for comparison.
        
        Args:
            value: Value to normalize
            field_type: Type of field
            
        Returns:
            Normalized value
        """
        if not value:
            return ""
        
        # Basic normalization
        normalized = unicodedata.normalize('NFKD', value.strip().lower())
        normalized = re.sub(r'\s+', ' ', normalized)
        
        if field_type == 'name':
            # Remove common business suffixes for name comparison
            suffixes = ['ltd', 'limited', 'inc', 'incorporated', 'corp', 'corporation', 'co', 'company']
            for suffix in suffixes:
                pattern = rf'\b{re.escape(suffix)}\.?\b'
                normalized = re.sub(pattern, '', normalized).strip()
        elif field_type == 'address':
            # Standardize address abbreviations
            address_replacements = {
                r'\bst\.?\b': 'street',
                r'\brd\.?\b': 'road',
                r'\bave\.?\b': 'avenue',
                r'\bblvd\.?\b': 'boulevard',
                r'\bdr\.?\b': 'drive',
                r'\bln\.?\b': 'lane',
                r'\bct\.?\b': 'court',
                r'\bpl\.?\b': 'place'
            }
            for pattern, replacement in address_replacements.items():
                normalized = re.sub(pattern, replacement, normalized)
        elif field_type == 'phone':
            # Keep only digits for phone comparison
            normalized = re.sub(r'\D', '', normalized)
        elif field_type in ['email', 'website']:
            # Remove protocol and www for website comparison
            if field_type == 'website':
                normalized = re.sub(r'^https?://', '', normalized)
                normalized = re.sub(r'^www\.', '', normalized)
        
        return normalized.strip()
    
    def _generate_business_hash(self, business: BusinessData) -> str:
        """
        Generate a hash for exact duplicate detection.
        
        Args:
            business: Business data to hash
            
        Returns:
            SHA-256 hash string
        """
        # Combine exact match fields for hashing
        hash_components = []
        
        for field in self.exact_match_fields:
            value = getattr(business, field, None)
            if value:
                # Normalize the value before hashing
                normalized_value = self._normalize_for_comparison(value, field)
                hash_components.append(f"{field}:{normalized_value}")
        
        # Create hash from combined components
        combined_string = "|".join(sorted(hash_components))
        return hashlib.sha256(combined_string.encode('utf-8')).hexdigest()
    
    def _determine_confidence_level(self, score: float) -> ConfidenceLevel:
        """
        Determine confidence level based on similarity score.
        
        Args:
            score: Similarity score (0-100)
            
        Returns:
            ConfidenceLevel enum value
        """
        if score >= self.confidence_thresholds[ConfidenceLevel.HIGH]:
            return ConfidenceLevel.HIGH
        elif score >= self.confidence_thresholds[ConfidenceLevel.MEDIUM]:
            return ConfidenceLevel.MEDIUM
        elif score >= self.confidence_thresholds[ConfidenceLevel.LOW]:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.NONE
    
    def create_merge_decisions(self, duplicate_matches: List[DuplicateMatch]) -> List[MergeDecision]:
        """
        Create merge decisions for duplicate matches based on business rules.
        
        Args:
            duplicate_matches: List of duplicate matches to process
            
        Returns:
            List of MergeDecision objects
        """
        merge_decisions = []
        
        for match in duplicate_matches:
            # Skip low confidence matches - they require manual review
            if match.confidence_level == ConfidenceLevel.LOW:
                logger.info(f"Skipping low confidence match: {match}")
                continue
            
            # Determine primary and secondary business
            primary, secondary = self._determine_merge_priority(match.business1, match.business2)
            
            # Create merged data
            merged_data = self._merge_business_data(primary, secondary, match)
            
            # Determine merge strategy
            strategy = "automatic" if match.confidence_level == ConfidenceLevel.HIGH else "review_required"
            
            merge_decision = MergeDecision(
                primary_business=primary,
                secondary_business=secondary,
                merged_data=merged_data,
                merge_strategy=strategy,
                confidence_score=match.confidence_score
            )
            
            merge_decisions.append(merge_decision)
        
        logger.info(f"Created {len(merge_decisions)} merge decisions")
        return merge_decisions
    
    def _determine_merge_priority(self, business1: BusinessData, business2: BusinessData) -> Tuple[BusinessData, BusinessData]:
        """
        Determine which business should be primary in a merge.
        
        Args:
            business1: First business
            business2: Second business
            
        Returns:
            Tuple of (primary_business, secondary_business)
        """
        # Priority factors (higher score = better primary candidate)
        def calculate_priority_score(business: BusinessData) -> float:
            score = 0.0
            
            # More complete data gets higher priority
            if business.phone_number:
                score += 1.0
            if business.email:
                score += 1.0
            if business.website:
                score += 1.0
            if business.description:
                score += 0.5
            if business.operating_hours:
                score += 0.5
            if business.rating:
                score += 0.5
            
            # More recent data gets higher priority
            if business.last_scraped_at:
                # Add small bonus for more recent scraping (max 1.0)
                import datetime
                days_old = (datetime.datetime.now() - business.last_scraped_at).days
                recency_bonus = max(0, 1.0 - (days_old / 365))  # Decay over a year
                score += recency_bonus
            
            # Geocoded data gets higher priority
            if business.latitude and business.longitude:
                score += 2.0
            
            return score
        
        score1 = calculate_priority_score(business1)
        score2 = calculate_priority_score(business2)
        
        if score1 >= score2:
            return business1, business2
        else:
            return business2, business1
    
    def _merge_business_data(self, primary: BusinessData, secondary: BusinessData, match: DuplicateMatch) -> Dict[str, Any]:
        """
        Merge data from two businesses, preferring primary but filling gaps with secondary.
        
        Args:
            primary: Primary business (preferred data source)
            secondary: Secondary business (gap filler)
            match: Duplicate match information
            
        Returns:
            Dictionary of merged business data
        """
        merged_data = {}
        
        # Start with primary business data
        for field in primary.__fields__:
            primary_value = getattr(primary, field, None)
            secondary_value = getattr(secondary, field, None)
            
            # Use primary value if it exists, otherwise use secondary
            if primary_value is not None and primary_value != "":
                merged_data[field] = primary_value
            elif secondary_value is not None and secondary_value != "":
                merged_data[field] = secondary_value
            else:
                merged_data[field] = primary_value  # Keep primary even if None
        
        # Special handling for certain fields
        
        # For ratings, use the higher rating if both exist
        if primary.rating and secondary.rating:
            merged_data['rating'] = max(primary.rating, secondary.rating)
        
        # For descriptions, combine if both exist and are different
        if (primary.description and secondary.description and 
            primary.description.strip() != secondary.description.strip()):
            merged_data['description'] = f"{primary.description.strip()} | {secondary.description.strip()}"
        
        # Update metadata to reflect the merge
        merged_data['last_scraped_at'] = max(
            primary.last_scraped_at or datetime.datetime.min,
            secondary.last_scraped_at or datetime.datetime.min
        )
        
        # Mark as active if either is active
        merged_data['is_active'] = primary.is_active or secondary.is_active
        
        # Use the best scrape status
        status_priority = {'success': 3, 'pending': 2, 'retry': 1, 'failed': 0, 'anti-bot': 0}
        primary_priority = status_priority.get(primary.scrape_status, 0)
        secondary_priority = status_priority.get(secondary.scrape_status, 0)
        
        if primary_priority >= secondary_priority:
            merged_data['scrape_status'] = primary.scrape_status
        else:
            merged_data['scrape_status'] = secondary.scrape_status
        
        return merged_data
    
    def get_manual_review_queue(self, duplicate_matches: List[DuplicateMatch]) -> List[DuplicateMatch]:
        """
        Get matches that require manual review.
        
        Args:
            duplicate_matches: List of all duplicate matches
            
        Returns:
            List of matches requiring manual review
        """
        manual_review_matches = [
            match for match in duplicate_matches
            if match.requires_manual_review
        ]
        
        # Sort by confidence score (highest first) for prioritization
        manual_review_matches.sort(key=lambda x: x.confidence_score, reverse=True)
        
        logger.info(f"Found {len(manual_review_matches)} matches requiring manual review")
        return manual_review_matches
    
    def deduplicate_businesses(self, businesses: List[BusinessData]) -> Tuple[List[BusinessData], List[DuplicateMatch]]:
        """
        Complete deduplication workflow: find duplicates, create merge decisions, and return deduplicated list.
        
        Args:
            businesses: List of businesses to deduplicate
            
        Returns:
            Tuple of (deduplicated_businesses, manual_review_matches)
        """
        if not businesses:
            return [], []
        
        logger.info(f"Starting complete deduplication workflow for {len(businesses)} businesses")
        
        # Find all duplicate matches
        duplicate_matches = self.find_duplicates(businesses)
        
        if not duplicate_matches:
            logger.info("No duplicates found")
            return businesses, []
        
        # Create merge decisions
        merge_decisions = self.create_merge_decisions(duplicate_matches)
        
        # Get matches requiring manual review
        manual_review_matches = self.get_manual_review_queue(duplicate_matches)
        
        # Apply automatic merges
        deduplicated_businesses = self._apply_merge_decisions(businesses, merge_decisions)
        
        logger.info(f"Deduplication complete: {len(businesses)} -> {len(deduplicated_businesses)} businesses")
        logger.info(f"{len(manual_review_matches)} matches require manual review")
        
        return deduplicated_businesses, manual_review_matches
    
    def _apply_merge_decisions(self, businesses: List[BusinessData], merge_decisions: List[MergeDecision]) -> List[BusinessData]:
        """
        Apply merge decisions to create deduplicated business list.
        
        Args:
            businesses: Original list of businesses
            merge_decisions: List of merge decisions to apply
            
        Returns:
            Deduplicated list of businesses
        """
        # Create a set of businesses to remove (secondary businesses in merges)
        businesses_to_remove = set()
        merged_businesses = {}
        
        # Process automatic merges only
        for decision in merge_decisions:
            if decision.merge_strategy == "automatic":
                # Mark secondary business for removal
                businesses_to_remove.add(id(decision.secondary_business))
                
                # Create merged business (update primary with merged data)
                merged_business = BusinessData(**decision.merged_data)
                merged_businesses[id(decision.primary_business)] = merged_business
        
        # Build deduplicated list
        deduplicated = []
        for business in businesses:
            business_id = id(business)
            
            # Skip businesses marked for removal
            if business_id in businesses_to_remove:
                continue
            
            # Use merged version if available, otherwise use original
            if business_id in merged_businesses:
                deduplicated.append(merged_businesses[business_id])
            else:
                deduplicated.append(business)
        
        return deduplicated