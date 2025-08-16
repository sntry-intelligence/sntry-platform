"""
Business Directory Pydantic schemas for API validation
"""
from pydantic import BaseModel, Field, validator, EmailStr
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
import re


class BusinessBase(BaseModel):
    """Base business schema with Jamaican-specific validation"""
    name: str = Field(..., min_length=1, max_length=255, description="Business name")
    category: Optional[str] = Field(None, max_length=100, description="Business category")
    raw_address: str = Field(..., min_length=1, description="Raw address as scraped")
    phone_number: Optional[str] = Field(None, max_length=50, description="Jamaican phone number")
    email: Optional[EmailStr] = Field(None, description="Email address")
    website: Optional[str] = Field(None, max_length=255, description="Website URL")
    description: Optional[str] = Field(None, description="Business description")
    operating_hours: Optional[str] = Field(None, description="Operating hours")
    rating: Optional[Decimal] = Field(None, ge=0, le=5, description="Business rating")

    @validator('phone_number')
    def validate_jamaican_phone(cls, v):
        """Validate Jamaican phone number formats"""
        if v is None:
            return v
        
        # Remove all non-digit characters for validation
        digits_only = re.sub(r'\D', '', v)
        
        # Jamaican phone number patterns:
        # - 7-digit local: 1234567
        # - 10-digit with area code: 8761234567 (876 is Jamaica area code)
        # - 11-digit with country code: 18761234567 (1 is NANP country code)
        # - International format: +18761234567
        
        if len(digits_only) == 7:
            # Local 7-digit number
            return v
        elif len(digits_only) == 10 and digits_only.startswith('876'):
            # 10-digit with Jamaica area code
            return v
        elif len(digits_only) == 11 and digits_only.startswith('1876'):
            # 11-digit with NANP country code
            return v
        else:
            raise ValueError('Invalid Jamaican phone number format. Expected formats: 1234567, 8761234567, 18761234567, or +18761234567')
    
    @validator('website')
    def validate_website_url(cls, v):
        """Validate website URL format"""
        if v is None:
            return v
        
        # Basic URL validation
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if not url_pattern.match(v):
            raise ValueError('Invalid website URL format')
        
        return v


class BusinessCreate(BusinessBase):
    """Schema for creating a business"""
    source_url: str = Field(..., max_length=255, description="Source URL where data was scraped")


class BusinessUpdate(BaseModel):
    """Schema for updating a business"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    raw_address: Optional[str] = Field(None, min_length=1)
    standardized_address: Optional[str] = Field(None)
    phone_number: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=255)
    website: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None)
    operating_hours: Optional[str] = Field(None)
    rating: Optional[Decimal] = Field(None, ge=0, le=5)


class BusinessResponse(BusinessBase):
    """Schema for business API responses"""
    id: int
    standardized_address: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    google_place_id: Optional[str] = None
    source_url: str
    last_scraped_at: datetime
    last_geocoded_at: Optional[datetime] = None
    is_active: bool
    scrape_status: str
    geocode_status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ParsedAddress(BaseModel):
    """Schema for parsed Jamaican address components with validation"""
    house_number: Optional[str] = Field(None, max_length=20, description="House/building number")
    street_name: Optional[str] = Field(None, max_length=255, description="Street name")
    po_box: Optional[str] = Field(None, max_length=50, description="PO Box number")
    postal_zone: Optional[str] = Field(None, max_length=20, description="Jamaican postal zone")
    city: str = Field(..., max_length=100, description="City name")
    parish: Optional[str] = Field(None, max_length=50, description="Jamaican parish")
    country: str = Field(default="JAMAICA", max_length=50, description="Country")
    formatted_address: str = Field(..., description="Complete formatted address")
    
    @validator('postal_zone')
    def validate_jamaican_postal_zone(cls, v):
        """Validate Jamaican postal zone format"""
        if v is None:
            return v
        
        # Jamaican postal zones are typically in format: CITY ##
        # Examples: KINGSTON 10, SPANISH TOWN 01, MONTEGO BAY 02
        postal_pattern = re.compile(r'^[A-Z\s]+ \d{2}$')
        
        if not postal_pattern.match(v.upper()):
            raise ValueError('Invalid Jamaican postal zone format. Expected format: "CITY ##" (e.g., "KINGSTON 10")')
        
        return v.upper()
    
    @validator('parish')
    def validate_jamaican_parish(cls, v):
        """Validate Jamaican parish names"""
        if v is None:
            return v
        
        # List of valid Jamaican parishes
        valid_parishes = {
            'KINGSTON', 'ST. ANDREW', 'ST. THOMAS', 'PORTLAND', 'ST. MARY',
            'ST. ANN', 'TRELAWNY', 'ST. JAMES', 'HANOVER', 'WESTMORELAND',
            'ST. ELIZABETH', 'MANCHESTER', 'CLARENDON', 'ST. CATHERINE'
        }
        
        parish_upper = v.upper()
        if parish_upper not in valid_parishes:
            raise ValueError(f'Invalid Jamaican parish. Must be one of: {", ".join(valid_parishes)}')
        
        return parish_upper
    
    @validator('country')
    def validate_country(cls, v):
        """Ensure country is JAMAICA"""
        return v.upper()


class AddressComponent(BaseModel):
    """Schema for Google Geocoding API address components"""
    long_name: str = Field(..., description="Full name of the address component")
    short_name: str = Field(..., description="Abbreviated name of the address component")
    types: List[str] = Field(..., description="Array of types that apply to this component")


class GeocodingResult(BaseModel):
    """Schema for Google Geocoding API results with comprehensive response structure"""
    status: str = Field(..., description="Geocoding status: OK, ZERO_RESULTS, OVER_QUERY_LIMIT, etc.")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude coordinate")
    place_id: Optional[str] = Field(None, description="Google Place ID")
    formatted_address: Optional[str] = Field(None, description="Human-readable formatted address")
    address_components: Optional[List[AddressComponent]] = Field(None, description="Detailed address components")
    location_type: Optional[str] = Field(None, description="Geocoding precision: ROOFTOP, RANGE_INTERPOLATED, etc.")
    viewport: Optional[dict] = Field(None, description="Recommended viewport for displaying result")
    error_message: Optional[str] = Field(None, description="Error message if geocoding failed")
    
    @validator('status')
    def validate_geocoding_status(cls, v):
        """Validate Google Geocoding API status codes"""
        valid_statuses = {
            'OK', 'ZERO_RESULTS', 'OVER_DAILY_LIMIT', 'OVER_QUERY_LIMIT',
            'REQUEST_DENIED', 'INVALID_REQUEST', 'UNKNOWN_ERROR'
        }
        
        if v not in valid_statuses:
            raise ValueError(f'Invalid geocoding status. Must be one of: {", ".join(valid_statuses)}')
        
        return v


class BusinessSearchFilters(BaseModel):
    """Schema for business search filters"""
    query: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius: Optional[float] = Field(None, gt=0, description="Search radius in kilometers")
    is_active: bool = True


class BusinessData(BaseModel):
    """Comprehensive business data model with all required fields and validation"""
    id: Optional[int] = Field(None, description="Business ID")
    name: str = Field(..., min_length=1, max_length=255, description="Business name")
    category: Optional[str] = Field(None, max_length=100, description="Business category")
    raw_address: str = Field(..., min_length=1, description="Raw address as scraped")
    standardized_address: Optional[str] = Field(None, description="Libpostal standardized address")
    phone_number: Optional[str] = Field(None, max_length=50, description="Jamaican phone number")
    email: Optional[EmailStr] = Field(None, description="Email address")
    website: Optional[str] = Field(None, max_length=255, description="Website URL")
    description: Optional[str] = Field(None, description="Business description")
    operating_hours: Optional[str] = Field(None, description="Operating hours")
    rating: Optional[float] = Field(None, ge=0, le=5, description="Business rating")
    
    # Geospatial data
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude coordinate")
    google_place_id: Optional[str] = Field(None, description="Google Place ID")
    
    # Metadata
    source_url: str = Field(..., max_length=255, description="Source URL where data was scraped")
    last_scraped_at: datetime = Field(..., description="Timestamp of last scraping")
    last_geocoded_at: Optional[datetime] = Field(None, description="Timestamp of last geocoding")
    is_active: bool = Field(default=True, description="Active status flag")
    scrape_status: str = Field(default="pending", description="Scraping status")
    geocode_status: str = Field(default="pending", description="Geocoding status")
    
    @validator('phone_number')
    def validate_jamaican_phone(cls, v):
        """Validate Jamaican phone number formats"""
        if v is None:
            return v
        
        # Remove all non-digit characters for validation
        digits_only = re.sub(r'\D', '', v)
        
        if len(digits_only) == 7:
            return v
        elif len(digits_only) == 10 and digits_only.startswith('876'):
            return v
        elif len(digits_only) == 11 and digits_only.startswith('1876'):
            return v
        else:
            raise ValueError('Invalid Jamaican phone number format')
    
    @validator('website')
    def validate_website_url(cls, v):
        """Validate website URL format"""
        if v is None:
            return v
        
        url_pattern = re.compile(
            r'^https?://'
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
            r'localhost|'
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
            r'(?::\d+)?'
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if not url_pattern.match(v):
            raise ValueError('Invalid website URL format')
        
        return v
    
    @validator('scrape_status')
    def validate_scrape_status(cls, v):
        """Validate scraping status values"""
        valid_statuses = {'pending', 'success', 'failed', 'anti-bot', 'retry'}
        if v not in valid_statuses:
            raise ValueError(f'Invalid scrape status. Must be one of: {", ".join(valid_statuses)}')
        return v
    
    @validator('geocode_status')
    def validate_geocode_status(cls, v):
        """Validate geocoding status values"""
        valid_statuses = {'pending', 'OK', 'ZERO_RESULTS', 'OVER_QUERY_LIMIT', 'REQUEST_DENIED', 'INVALID_REQUEST', 'UNKNOWN_ERROR'}
        if v not in valid_statuses:
            raise ValueError(f'Invalid geocode status. Must be one of: {", ".join(valid_statuses)}')
        return v

    class Config:
        from_attributes = True


class BusinessSearchResponse(BaseModel):
    """Schema for business search results"""
    businesses: list[BusinessResponse]
    total: int
    skip: int
    limit: int
    filters: BusinessSearchFilters