"""
Business Directory Repository Layer with CRUD operations and spatial queries
"""
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text, desc, asc
from sqlalchemy.exc import SQLAlchemyError
from geoalchemy2.functions import ST_DWithin, ST_Distance, ST_MakePoint, ST_SetSRID
from datetime import datetime
import logging

from app.business_directory.models import Business
from app.business_directory.schemas import (
    BusinessData, BusinessCreate, BusinessUpdate, 
    BusinessSearchFilters, ParsedAddress
)

logger = logging.getLogger(__name__)


class BusinessRepository:
    """Repository class for business data CRUD operations and spatial queries"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, business_data: BusinessCreate) -> Business:
        """Create a new business record"""
        try:
            db_business = Business(
                name=business_data.name,
                category=business_data.category,
                raw_address=business_data.raw_address,
                phone_number=business_data.phone_number,
                email=str(business_data.email) if business_data.email else None,
                website=business_data.website,
                description=business_data.description,
                operating_hours=business_data.operating_hours,
                rating=business_data.rating,
                source_url=business_data.source_url,
                last_scraped_at=datetime.utcnow(),
                is_active=True,
                scrape_status='success',
                geocode_status='pending'
            )
            
            self.db.add(db_business)
            self.db.commit()
            self.db.refresh(db_business)
            
            logger.info(f"Created business record: {db_business.id} - {db_business.name}")
            return db_business
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Error creating business record: {e}")
            raise
    
    def get_by_id(self, business_id: int) -> Optional[Business]:
        """Get business by ID"""
        try:
            return self.db.query(Business).filter(Business.id == business_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving business {business_id}: {e}")
            raise
    
    def get_by_ids(self, business_ids: List[int]) -> List[Business]:
        """Get multiple businesses by IDs"""
        try:
            return self.db.query(Business).filter(Business.id.in_(business_ids)).all()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving businesses by IDs: {e}")
            raise
    
    def update(self, business_id: int, business_update: BusinessUpdate) -> Optional[Business]:
        """Update business record"""
        try:
            db_business = self.get_by_id(business_id)
            if not db_business:
                return None
            
            # Update only provided fields
            update_data = business_update.dict(exclude_unset=True)
            for field, value in update_data.items():
                if field == 'email' and value:
                    value = str(value)
                setattr(db_business, field, value)
            
            self.db.commit()
            self.db.refresh(db_business)
            
            logger.info(f"Updated business record: {business_id}")
            return db_business
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Error updating business {business_id}: {e}")
            raise
    
    def soft_delete(self, business_id: int) -> bool:
        """Soft delete business record using is_active flag"""
        try:
            db_business = self.get_by_id(business_id)
            if not db_business:
                return False
            
            db_business.is_active = False
            self.db.commit()
            
            logger.info(f"Soft deleted business record: {business_id}")
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Error soft deleting business {business_id}: {e}")
            raise
    
    def hard_delete(self, business_id: int) -> bool:
        """Hard delete business record (permanent removal)"""
        try:
            db_business = self.get_by_id(business_id)
            if not db_business:
                return False
            
            self.db.delete(db_business)
            self.db.commit()
            
            logger.info(f"Hard deleted business record: {business_id}")
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Error hard deleting business {business_id}: {e}")
            raise
    
    def search(
        self, 
        filters: BusinessSearchFilters,
        skip: int = 0,
        limit: int = 100,
        order_by: str = "name",
        order_direction: str = "asc"
    ) -> Tuple[List[Business], int]:
        """Search businesses with filtering, pagination, and sorting"""
        try:
            query = self.db.query(Business)
            
            # Apply filters
            if filters.is_active is not None:
                query = query.filter(Business.is_active == filters.is_active)
            
            if filters.category:
                query = query.filter(Business.category.ilike(f"%{filters.category}%"))
            
            if filters.query:
                # Search across multiple text fields
                search_term = f"%{filters.query}%"
                query = query.filter(
                    or_(
                        Business.name.ilike(search_term),
                        Business.description.ilike(search_term),
                        Business.raw_address.ilike(search_term),
                        Business.standardized_address.ilike(search_term)
                    )
                )
            
            if filters.location:
                # Search by location in address fields
                location_term = f"%{filters.location}%"
                query = query.filter(
                    or_(
                        Business.raw_address.ilike(location_term),
                        Business.standardized_address.ilike(location_term)
                    )
                )
            
            # Spatial filtering if coordinates and radius provided
            if all([filters.latitude, filters.longitude, filters.radius]):
                point = ST_SetSRID(ST_MakePoint(filters.longitude, filters.latitude), 4326)
                # Convert radius from kilometers to meters for ST_DWithin
                radius_meters = filters.radius * 1000
                query = query.filter(
                    ST_DWithin(Business.geom, point, radius_meters)
                )
            
            # Get total count before pagination
            total = query.count()
            
            # Apply sorting
            order_column = getattr(Business, order_by, Business.name)
            if order_direction.lower() == "desc":
                query = query.order_by(desc(order_column))
            else:
                query = query.order_by(asc(order_column))
            
            # Apply pagination
            businesses = query.offset(skip).limit(limit).all()
            
            return businesses, total
            
        except SQLAlchemyError as e:
            logger.error(f"Error searching businesses: {e}")
            raise
    
    def find_nearby(
        self, 
        latitude: float, 
        longitude: float, 
        radius_km: float,
        category: Optional[str] = None,
        limit: int = 50
    ) -> List[Tuple[Business, float]]:
        """Find businesses within radius using ST_DWithin with distance calculation"""
        try:
            point = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
            radius_meters = radius_km * 1000
            
            query = self.db.query(
                Business,
                ST_Distance(Business.geom, point).label('distance_meters')
            ).filter(
                and_(
                    Business.is_active == True,
                    Business.geom.isnot(None),
                    ST_DWithin(Business.geom, point, radius_meters)
                )
            )
            
            if category:
                query = query.filter(Business.category.ilike(f"%{category}%"))
            
            # Order by distance (closest first)
            results = query.order_by('distance_meters').limit(limit).all()
            
            # Convert distance from meters to kilometers and return as tuples
            return [(business, distance_meters / 1000) for business, distance_meters in results]
            
        except SQLAlchemyError as e:
            logger.error(f"Error finding nearby businesses: {e}")
            raise
    
    def get_by_category(self, category: str, active_only: bool = True) -> List[Business]:
        """Get all businesses in a specific category"""
        try:
            query = self.db.query(Business).filter(Business.category.ilike(f"%{category}%"))
            
            if active_only:
                query = query.filter(Business.is_active == True)
            
            return query.all()
            
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving businesses by category {category}: {e}")
            raise
    
    def get_categories(self) -> List[str]:
        """Get all unique business categories"""
        try:
            categories = self.db.query(Business.category).filter(
                and_(
                    Business.category.isnot(None),
                    Business.is_active == True
                )
            ).distinct().all()
            
            return [category[0] for category in categories if category[0]]
            
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving business categories: {e}")
            raise
    
    def update_geocoding_data(
        self, 
        business_id: int, 
        latitude: float, 
        longitude: float,
        google_place_id: Optional[str] = None,
        formatted_address: Optional[str] = None
    ) -> Optional[Business]:
        """Update geocoding data for a business"""
        try:
            db_business = self.get_by_id(business_id)
            if not db_business:
                return None
            
            db_business.latitude = latitude
            db_business.longitude = longitude
            db_business.google_place_id = google_place_id
            if formatted_address:
                db_business.standardized_address = formatted_address
            db_business.last_geocoded_at = datetime.utcnow()
            db_business.geocode_status = 'OK'
            
            # The geom column will be automatically updated by the database trigger
            
            self.db.commit()
            self.db.refresh(db_business)
            
            logger.info(f"Updated geocoding data for business: {business_id}")
            return db_business
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Error updating geocoding data for business {business_id}: {e}")
            raise
    
    def get_pending_geocoding(self, limit: int = 100) -> List[Business]:
        """Get businesses that need geocoding"""
        try:
            return self.db.query(Business).filter(
                and_(
                    Business.is_active == True,
                    Business.geocode_status == 'pending',
                    Business.latitude.is_(None),
                    Business.longitude.is_(None)
                )
            ).limit(limit).all()
            
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving businesses pending geocoding: {e}")
            raise
    
    def get_failed_geocoding(self, limit: int = 100) -> List[Business]:
        """Get businesses with failed geocoding for retry"""
        try:
            return self.db.query(Business).filter(
                and_(
                    Business.is_active == True,
                    Business.geocode_status.in_(['ZERO_RESULTS', 'INVALID_REQUEST', 'UNKNOWN_ERROR']),
                    Business.latitude.is_(None),
                    Business.longitude.is_(None)
                )
            ).limit(limit).all()
            
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving businesses with failed geocoding: {e}")
            raise
    
    def update_scrape_status(self, business_id: int, status: str, error_message: Optional[str] = None) -> bool:
        """Update scraping status for a business"""
        try:
            db_business = self.get_by_id(business_id)
            if not db_business:
                return False
            
            db_business.scrape_status = status
            db_business.last_scraped_at = datetime.utcnow()
            
            if error_message and hasattr(db_business, 'scrape_error'):
                db_business.scrape_error = error_message
            
            self.db.commit()
            
            logger.info(f"Updated scrape status for business {business_id}: {status}")
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Error updating scrape status for business {business_id}: {e}")
            raise
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics for monitoring"""
        try:
            stats = {}
            
            # Total counts
            stats['total_businesses'] = self.db.query(Business).count()
            stats['active_businesses'] = self.db.query(Business).filter(Business.is_active == True).count()
            stats['inactive_businesses'] = stats['total_businesses'] - stats['active_businesses']
            
            # Geocoding statistics
            stats['geocoded_businesses'] = self.db.query(Business).filter(
                and_(Business.latitude.isnot(None), Business.longitude.isnot(None))
            ).count()
            stats['pending_geocoding'] = self.db.query(Business).filter(
                Business.geocode_status == 'pending'
            ).count()
            stats['failed_geocoding'] = self.db.query(Business).filter(
                Business.geocode_status.in_(['ZERO_RESULTS', 'INVALID_REQUEST', 'UNKNOWN_ERROR'])
            ).count()
            
            # Scraping statistics
            stats['successful_scrapes'] = self.db.query(Business).filter(
                Business.scrape_status == 'success'
            ).count()
            stats['failed_scrapes'] = self.db.query(Business).filter(
                Business.scrape_status == 'failed'
            ).count()
            
            # Category statistics
            category_counts = self.db.query(
                Business.category, func.count(Business.id)
            ).filter(
                and_(Business.is_active == True, Business.category.isnot(None))
            ).group_by(Business.category).all()
            
            stats['categories'] = {category: count for category, count in category_counts}
            stats['total_categories'] = len(stats['categories'])
            
            return stats
            
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving database statistics: {e}")
            raise
    
    def search_by_name_and_address(self, name: str, address: str) -> Optional[Business]:
        """Search for existing business by name and address for deduplication"""
        try:
            return self.db.query(Business).filter(
                and_(
                    Business.name.ilike(f"%{name}%"),
                    Business.raw_address.ilike(f"%{address}%"),
                    Business.is_active == True
                )
            ).first()
            
        except SQLAlchemyError as e:
            logger.error(f"Error searching business by name and address: {e}")
            raise
    
    def bulk_create(self, businesses_data: List[BusinessCreate]) -> List[Business]:
        """Bulk create multiple business records for efficient data loading"""
        try:
            db_businesses = []
            for business_data in businesses_data:
                db_business = Business(
                    name=business_data.name,
                    category=business_data.category,
                    raw_address=business_data.raw_address,
                    phone_number=business_data.phone_number,
                    email=str(business_data.email) if business_data.email else None,
                    website=business_data.website,
                    description=business_data.description,
                    operating_hours=business_data.operating_hours,
                    rating=business_data.rating,
                    source_url=business_data.source_url,
                    last_scraped_at=datetime.utcnow(),
                    is_active=True,
                    scrape_status='success',
                    geocode_status='pending'
                )
                db_businesses.append(db_business)
            
            self.db.add_all(db_businesses)
            self.db.commit()
            
            # Refresh all objects to get their IDs
            for db_business in db_businesses:
                self.db.refresh(db_business)
            
            logger.info(f"Bulk created {len(db_businesses)} business records")
            return db_businesses
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Error bulk creating business records: {e}")
            raise