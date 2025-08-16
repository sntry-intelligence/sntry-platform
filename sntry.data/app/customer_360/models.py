"""
Customer 360 data models
"""
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, Numeric, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional

from app.core.database import PostgresBase, SQLServerBase


class Customer(PostgresBase):
    """Customer profile model for PostgreSQL storage"""
    __tablename__ = "customers"
    __table_args__ = {"schema": "customer_data"}
    
    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(100), unique=True, index=True, nullable=True)  # ID from external systems
    first_name = Column(String(100))
    last_name = Column(String(100))
    email = Column(String(255), unique=True, index=True)
    phone_number = Column(String(50))
    address = Column(Text)
    
    # Customer segmentation
    customer_type = Column(String(50))  # individual, business, etc.
    industry = Column(String(100))
    company_name = Column(String(255))
    
    # Lead scoring
    lead_score = Column(Numeric(5, 2), default=0)
    lead_status = Column(String(50), default='new')  # new, qualified, contacted, converted, lost
    
    # Metadata
    source_system = Column(String(100))  # quickbooks, sheets, manual, etc.
    is_active = Column(Boolean, default=True, index=True)
    last_interaction_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Customer(id={self.id}, email='{self.email}', name='{self.first_name} {self.last_name}')>"


class CustomerInteraction(PostgresBase):
    """Customer interaction tracking model"""
    __tablename__ = "customer_interactions"
    __table_args__ = {"schema": "customer_data"}
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey('customer_data.customers.id'), nullable=False)
    interaction_type = Column(String(50), nullable=False)  # email, call, meeting, website_visit, etc.
    interaction_channel = Column(String(50))  # phone, email, social_media, website, etc.
    subject = Column(String(255))
    description = Column(Text)
    outcome = Column(String(100))
    
    # Interaction metadata
    interaction_date = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Integer)
    created_by = Column(String(100))  # user or system that created the interaction
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    customer = relationship("Customer", backref="interactions")
    
    def __repr__(self):
        return f"<CustomerInteraction(id={self.id}, customer_id={self.customer_id}, type='{self.interaction_type}')>"


class CustomerBusinessRelationship(PostgresBase):
    """Relationship between customers and businesses"""
    __tablename__ = "customer_business_relationships"
    __table_args__ = {"schema": "customer_data"}
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey('customer_data.customers.id'), nullable=False)
    business_id = Column(Integer, ForeignKey('business_data.businesses.id'), nullable=False)
    relationship_type = Column(String(50), nullable=False)  # owner, employee, customer, prospect, etc.
    relationship_status = Column(String(50), default='active')  # active, inactive, potential
    
    # Relationship metadata
    start_date = Column(DateTime(timezone=True))
    end_date = Column(DateTime(timezone=True))
    notes = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    customer = relationship("Customer", backref="business_relationships")
    
    def __repr__(self):
        return f"<CustomerBusinessRelationship(customer_id={self.customer_id}, business_id={self.business_id}, type='{self.relationship_type}')>"


# SQL Server models for data warehouse (if SQL Server is configured)
if SQLServerBase:
    class CustomerDataWarehouse(SQLServerBase):
        """Customer data warehouse model for SQL Server"""
        __tablename__ = "customers"
        __table_args__ = {"schema": "customer_360"}
        
        id = Column(Integer, primary_key=True)
        source_customer_id = Column(Integer, nullable=False)
        source_system = Column(String(100), nullable=False)
        
        # Customer data
        first_name = Column(String(100))
        last_name = Column(String(100))
        email = Column(String(255))
        phone_number = Column(String(50))
        company_name = Column(String(255))
        
        # Aggregated metrics
        total_interactions = Column(Integer, default=0)
        last_interaction_date = Column(DateTime)
        total_revenue = Column(Numeric(15, 2), default=0)
        lifetime_value = Column(Numeric(15, 2), default=0)
        
        # ETL metadata
        etl_created_at = Column(DateTime, server_default=func.now())
        etl_updated_at = Column(DateTime, server_default=func.now())
        
        def __repr__(self):
            return f"<CustomerDataWarehouse(id={self.id}, source_id={self.source_customer_id}, system='{self.source_system}')>"