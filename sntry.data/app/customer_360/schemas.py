"""
Customer 360 Pydantic schemas for API validation
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class CustomerBase(BaseModel):
    """Base customer schema"""
    first_name: Optional[str] = Field(None, max_length=100, description="Customer first name")
    last_name: Optional[str] = Field(None, max_length=100, description="Customer last name")
    email: Optional[EmailStr] = Field(None, description="Customer email address")
    phone_number: Optional[str] = Field(None, max_length=50, description="Customer phone number")
    address: Optional[str] = Field(None, description="Customer address")
    customer_type: Optional[str] = Field(None, max_length=50, description="Customer type")
    industry: Optional[str] = Field(None, max_length=100, description="Customer industry")
    company_name: Optional[str] = Field(None, max_length=255, description="Company name")


class CustomerCreate(CustomerBase):
    """Schema for creating a customer"""
    external_id: Optional[str] = Field(None, max_length=100, description="External system ID")
    source_system: Optional[str] = Field(None, max_length=100, description="Source system")


class CustomerUpdate(CustomerBase):
    """Schema for updating a customer"""
    lead_score: Optional[Decimal] = Field(None, ge=0, description="Lead score")
    lead_status: Optional[str] = Field(None, max_length=50, description="Lead status")
    is_active: Optional[bool] = Field(None, description="Customer active status")


class CustomerResponse(CustomerBase):
    """Schema for customer API responses"""
    id: int
    external_id: Optional[str] = None
    lead_score: Decimal
    lead_status: str
    source_system: Optional[str] = None
    is_active: bool
    last_interaction_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CustomerInteractionBase(BaseModel):
    """Base customer interaction schema"""
    interaction_type: str = Field(..., max_length=50, description="Type of interaction")
    interaction_channel: Optional[str] = Field(None, max_length=50, description="Interaction channel")
    subject: Optional[str] = Field(None, max_length=255, description="Interaction subject")
    description: Optional[str] = Field(None, description="Interaction description")
    outcome: Optional[str] = Field(None, max_length=100, description="Interaction outcome")
    interaction_date: datetime = Field(..., description="Date and time of interaction")
    duration_minutes: Optional[int] = Field(None, ge=0, description="Duration in minutes")


class CustomerInteractionCreate(CustomerInteractionBase):
    """Schema for creating a customer interaction"""
    customer_id: int = Field(..., description="Customer ID")
    created_by: Optional[str] = Field(None, max_length=100, description="Created by user/system")


class CustomerInteractionResponse(CustomerInteractionBase):
    """Schema for customer interaction API responses"""
    id: int
    customer_id: int
    created_by: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class CustomerBusinessRelationshipBase(BaseModel):
    """Base customer-business relationship schema"""
    relationship_type: str = Field(..., max_length=50, description="Type of relationship")
    relationship_status: str = Field(default="active", max_length=50, description="Relationship status")
    start_date: Optional[datetime] = Field(None, description="Relationship start date")
    end_date: Optional[datetime] = Field(None, description="Relationship end date")
    notes: Optional[str] = Field(None, description="Relationship notes")


class CustomerBusinessRelationshipCreate(CustomerBusinessRelationshipBase):
    """Schema for creating a customer-business relationship"""
    customer_id: int = Field(..., description="Customer ID")
    business_id: int = Field(..., description="Business ID")


class CustomerBusinessRelationshipResponse(CustomerBusinessRelationshipBase):
    """Schema for customer-business relationship API responses"""
    id: int
    customer_id: int
    business_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class Customer360View(BaseModel):
    """Comprehensive customer 360-degree view schema"""
    customer: CustomerResponse
    interactions: List[CustomerInteractionResponse]
    business_relationships: List[CustomerBusinessRelationshipResponse]
    
    # Aggregated metrics
    total_interactions: int
    last_interaction_date: Optional[datetime] = None
    interaction_frequency: float  # interactions per month
    
    # Lead scoring metrics
    engagement_score: float
    recency_score: float
    frequency_score: float
    
    # Social media insights (placeholder for future implementation)
    social_media_presence: dict = {}
    
    # Predictive analytics (placeholder for future implementation)
    churn_probability: Optional[float] = None
    lifetime_value_prediction: Optional[Decimal] = None
    next_best_action: Optional[str] = None


class LeadResponse(BaseModel):
    """Schema for lead generation responses"""
    customer: CustomerResponse
    lead_score: Decimal
    lead_reasons: List[str]  # Reasons why this is a good lead
    business_connections: List[dict]  # Connected businesses
    recommended_actions: List[str]  # Suggested next steps
    
    # Geographic data
    location: Optional[dict] = None  # lat, lon if available
    territory: Optional[str] = None


class LeadSearchFilters(BaseModel):
    """Schema for lead search filters"""
    min_score: Optional[float] = Field(None, ge=0, description="Minimum lead score")
    max_score: Optional[float] = Field(None, ge=0, description="Maximum lead score")
    lead_status: Optional[str] = Field(None, description="Lead status filter")
    industry: Optional[str] = Field(None, description="Industry filter")
    location: Optional[str] = Field(None, description="Location filter")
    latitude: Optional[float] = Field(None, description="Latitude for geographic search")
    longitude: Optional[float] = Field(None, description="Longitude for geographic search")
    radius: Optional[float] = Field(None, gt=0, description="Search radius in kilometers")


class LeadSearchResponse(BaseModel):
    """Schema for lead search results"""
    leads: List[LeadResponse]
    total: int
    skip: int
    limit: int
    filters: LeadSearchFilters