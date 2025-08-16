"""
Business Directory data models
"""
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, Numeric
from sqlalchemy.sql import func
from geoalchemy2 import Geography
from datetime import datetime
from typing import Optional

from app.core.database import PostgresBase


class Business(PostgresBase):
    """Business entity model for PostgreSQL storage"""
    __tablename__ = "businesses"
    __table_args__ = {"schema": "business_data"}
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    category = Column(String(100), index=True)
    raw_address = Column(Text, nullable=False)
    standardized_address = Column(Text)
    phone_number = Column(String(50))
    email = Column(String(255))
    website = Column(String(255))
    description = Column(Text)
    operating_hours = Column(Text)
    rating = Column(Numeric(2, 1))
    
    # Geospatial columns
    latitude = Column(Numeric(10, 7))
    longitude = Column(Numeric(10, 7))
    geom = Column(Geography(geometry_type='POINT', srid=4326))
    google_place_id = Column(String(255))
    
    # Metadata
    source_url = Column(String(255), nullable=False)
    last_scraped_at = Column(DateTime(timezone=True), nullable=False)
    last_geocoded_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True, index=True)
    scrape_status = Column(String(50), default='pending')
    geocode_status = Column(String(50), default='pending')
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Business(id={self.id}, name='{self.name}', category='{self.category}')>"