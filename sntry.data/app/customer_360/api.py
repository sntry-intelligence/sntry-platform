"""
Customer 360 API endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from app.core.database import get_postgres_db
from app.customer_360.repository import CustomerRepository
from app.customer_360.schemas import (
    CustomerCreate, CustomerUpdate, CustomerResponse,
    CustomerInteractionCreate, CustomerInteractionResponse,
    CustomerBusinessRelationshipCreate, CustomerBusinessRelationshipResponse,
    Customer360View, LeadResponse, LeadSearchFilters, LeadSearchResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_customer_repository(db: Session = Depends(get_postgres_db)) -> CustomerRepository:
    """Dependency to get customer repository"""
    return CustomerRepository(db)


@router.get("/health")
async def customer_health():
    """Customer 360 health check"""
    return {"status": "healthy", "module": "customer_360"}


@router.post("/customers", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    customer_data: CustomerCreate,
    repository: CustomerRepository = Depends(get_customer_repository)
):
    """Create a new customer profile"""
    try:
        # Check if customer with email already exists
        if customer_data.email:
            existing_customer = repository.get_customer_by_email(str(customer_data.email))
            if existing_customer:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Customer with email {customer_data.email} already exists"
                )
        
        db_customer = repository.create_customer(customer_data)
        logger.info(f"Created customer: {db_customer.id} - {db_customer.email}")
        return db_customer
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating customer: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create customer record"
        )


@router.get("/customers", response_model=List[CustomerResponse])
async def get_customers(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    is_active: bool = Query(True, description="Filter by active status"),
    lead_status: Optional[str] = Query(None, description="Filter by lead status"),
    customer_type: Optional[str] = Query(None, description="Filter by customer type"),
    repository: CustomerRepository = Depends(get_customer_repository)
):
    """Get customers with pagination and filtering"""
    try:
        # For now, we'll implement a simple query in the repository
        # In a full implementation, we'd add these filters to the repository
        from app.customer_360.models import Customer
        
        query = repository.db.query(Customer)
        
        if is_active is not None:
            query = query.filter(Customer.is_active == is_active)
        
        if lead_status:
            query = query.filter(Customer.lead_status == lead_status)
        
        if customer_type:
            query = query.filter(Customer.customer_type == customer_type)
        
        customers = query.offset(skip).limit(limit).all()
        return customers
    except Exception as e:
        logger.error(f"Error retrieving customers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve customers"
        )


@router.get("/customers/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: int,
    repository: CustomerRepository = Depends(get_customer_repository)
):
    """Get customer by ID"""
    try:
        customer = repository.get_customer_by_id(customer_id)
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer with ID {customer_id} not found"
            )
        return customer
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving customer {customer_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve customer"
        )


@router.put("/customers/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: int,
    customer_update: CustomerUpdate,
    repository: CustomerRepository = Depends(get_customer_repository)
):
    """Update customer profile"""
    try:
        updated_customer = repository.update_customer(customer_id, customer_update)
        if not updated_customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer with ID {customer_id} not found"
            )
        logger.info(f"Updated customer: {customer_id}")
        return updated_customer
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating customer {customer_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update customer"
        )


@router.get("/customers/{customer_id}/360-view")
async def get_customer_360_view(
    customer_id: int,
    repository: CustomerRepository = Depends(get_customer_repository)
):
    """Get comprehensive 360-degree customer view"""
    try:
        customer_360 = repository.get_customer_360_view(customer_id)
        if not customer_360:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer with ID {customer_id} not found"
            )
        
        return {
            "customer_id": customer_id,
            "customer": customer_360["customer"],
            "interactions": customer_360["interactions"],
            "business_relationships": customer_360["business_relationships"],
            "connected_businesses": customer_360["connected_businesses"],
            "metrics": {
                "total_interactions": customer_360["total_interactions"],
                "last_interaction_date": customer_360["last_interaction_date"],
                "interaction_frequency": customer_360["interaction_frequency"],
                "engagement_score": customer_360["engagement_score"],
                "recency_score": customer_360["recency_score"],
                "frequency_score": customer_360["frequency_score"]
            },
            "social_media_presence": customer_360["social_media_presence"],
            "predictive_analytics": {
                "churn_probability": customer_360["churn_probability"],
                "lifetime_value_prediction": customer_360["lifetime_value_prediction"],
                "next_best_action": customer_360["next_best_action"]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving customer 360 view for {customer_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve customer 360 view"
        )


@router.post("/customers/{customer_id}/interactions", response_model=CustomerInteractionResponse, status_code=status.HTTP_201_CREATED)
async def create_customer_interaction(
    customer_id: int,
    interaction_data: CustomerInteractionCreate,
    repository: CustomerRepository = Depends(get_customer_repository)
):
    """Create a new customer interaction"""
    try:
        # Ensure the customer_id in the URL matches the one in the data
        interaction_data.customer_id = customer_id
        
        # Verify customer exists
        customer = repository.get_customer_by_id(customer_id)
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer with ID {customer_id} not found"
            )
        
        db_interaction = repository.create_interaction(interaction_data)
        logger.info(f"Created interaction for customer: {customer_id}")
        return db_interaction
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating customer interaction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create customer interaction"
        )


@router.post("/customers/{customer_id}/business-relationships", response_model=CustomerBusinessRelationshipResponse, status_code=status.HTTP_201_CREATED)
async def create_customer_business_relationship(
    customer_id: int,
    relationship_data: CustomerBusinessRelationshipCreate,
    repository: CustomerRepository = Depends(get_customer_repository)
):
    """Create a customer-business relationship"""
    try:
        # Ensure the customer_id in the URL matches the one in the data
        relationship_data.customer_id = customer_id
        
        # Verify customer exists
        customer = repository.get_customer_by_id(customer_id)
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer with ID {customer_id} not found"
            )
        
        db_relationship = repository.create_business_relationship(relationship_data)
        logger.info(f"Created business relationship for customer: {customer_id}")
        return db_relationship
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating customer business relationship: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create customer business relationship"
        )


@router.get("/leads")
async def get_leads(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    min_score: Optional[float] = Query(None, description="Minimum lead score"),
    max_score: Optional[float] = Query(None, description="Maximum lead score"),
    lead_status: Optional[str] = Query(None, description="Filter by lead status"),
    industry: Optional[str] = Query(None, description="Filter by industry"),
    location: Optional[str] = Query(None, description="Filter by location"),
    repository: CustomerRepository = Depends(get_customer_repository)
):
    """Get qualified leads from business directory data"""
    try:
        filters = LeadSearchFilters(
            min_score=min_score,
            max_score=max_score,
            lead_status=lead_status,
            industry=industry,
            location=location
        )
        
        leads, total = repository.get_leads(filters, skip, limit)
        
        return {
            "leads": leads,
            "total": total,
            "skip": skip,
            "limit": limit,
            "filters": filters.dict()
        }
    except Exception as e:
        logger.error(f"Error retrieving leads: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve leads"
        )


@router.get("/leads/by-location")
async def get_leads_by_location(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    radius: float = Query(10.0, description="Search radius in kilometers"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results"),
    repository: CustomerRepository = Depends(get_customer_repository)
):
    """Get leads within geographic area"""
    try:
        leads = repository.get_leads_by_location(lat, lon, radius, limit)
        
        return {
            "leads": leads,
            "center": {"lat": lat, "lon": lon},
            "radius": radius,
            "total": len(leads)
        }
    except Exception as e:
        logger.error(f"Error retrieving leads by location: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve leads by location"
        )


@router.put("/customers/{customer_id}/lead-score")
async def update_lead_score(
    customer_id: int,
    score: float = Query(..., ge=0, le=100, description="Lead score (0-100)"),
    repository: CustomerRepository = Depends(get_customer_repository)
):
    """Update customer lead score"""
    try:
        success = repository.update_lead_score(customer_id, score)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer with ID {customer_id} not found"
            )
        
        return {"customer_id": customer_id, "lead_score": score, "updated": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating lead score for customer {customer_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update lead score"
        )


@router.get("/customers/statistics")
async def get_customer_statistics(
    repository: CustomerRepository = Depends(get_customer_repository)
):
    """Get customer database statistics"""
    try:
        stats = repository.get_customer_statistics()
        return stats
    except Exception as e:
        logger.error(f"Error retrieving customer statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve customer statistics"
        )
@router.g
et("/leads/by-location/advanced")
async def get_advanced_leads_by_location(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    radius: float = Query(10.0, description="Search radius in kilometers"),
    min_score: Optional[float] = Query(None, description="Minimum lead score"),
    industry: Optional[str] = Query(None, description="Industry filter"),
    customer_type: Optional[str] = Query(None, description="Customer type filter"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results"),
    include_business_context: bool = Query(True, description="Include connected business information"),
    repository: CustomerRepository = Depends(get_customer_repository)
):
    """Get advanced leads within geographic area with business context"""
    try:
        from app.business_directory.models import Business
        from app.customer_360.models import CustomerBusinessRelationship
        from sqlalchemy import text, and_, or_
        
        # Build base query for customers with business relationships in the area
        query = repository.db.query(Customer).join(
            CustomerBusinessRelationship,
            Customer.id == CustomerBusinessRelationship.customer_id
        ).join(
            Business,
            CustomerBusinessRelationship.business_id == Business.id
        ).filter(
            and_(
                Customer.is_active == True,
                Business.is_active == True,
                Business.latitude.isnot(None),
                Business.longitude.isnot(None)
            )
        )
        
        # Apply spatial filter
        spatial_filter = text("""
            ST_DWithin(
                ST_SetSRID(ST_MakePoint(businesses.longitude, businesses.latitude), 4326),
                ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326),
                :radius_meters
            )
        """)
        
        query = query.filter(
            spatial_filter.bindparam(
                longitude=lon,
                latitude=lat,
                radius_meters=radius * 1000
            )
        )
        
        # Apply additional filters
        if min_score is not None:
            query = query.filter(Customer.lead_score >= min_score)
        
        if industry:
            query = query.filter(Customer.industry.ilike(f"%{industry}%"))
        
        if customer_type:
            query = query.filter(Customer.customer_type == customer_type)
        
        # Get distinct customers
        customers = query.distinct().limit(limit).all()
        
        # Enrich with lead information and business context
        enriched_leads = []
        for customer in customers:
            lead_data = repository._enrich_lead_data(customer)
            
            if include_business_context:
                # Get businesses in the area connected to this customer
                connected_businesses = repository.db.query(Business).join(
                    CustomerBusinessRelationship,
                    Business.id == CustomerBusinessRelationship.business_id
                ).filter(
                    and_(
                        CustomerBusinessRelationship.customer_id == customer.id,
                        Business.is_active == True,
                        Business.latitude.isnot(None),
                        Business.longitude.isnot(None),
                        spatial_filter.bindparam(
                            longitude=lon,
                            latitude=lat,
                            radius_meters=radius * 1000
                        )
                    )
                ).all()
                
                lead_data["nearby_businesses"] = [
                    {
                        "id": business.id,
                        "name": business.name,
                        "category": business.category,
                        "address": business.raw_address,
                        "latitude": float(business.latitude) if business.latitude else None,
                        "longitude": float(business.longitude) if business.longitude else None
                    }
                    for business in connected_businesses
                ]
            
            # Add location context
            lead_data["location_context"] = {
                "search_center": {"lat": lat, "lon": lon},
                "search_radius_km": radius,
                "territory": f"Within {radius}km of ({lat:.4f}, {lon:.4f})"
            }
            
            enriched_leads.append(lead_data)
        
        return {
            "leads": enriched_leads,
            "total": len(enriched_leads),
            "search_parameters": {
                "center": {"lat": lat, "lon": lon},
                "radius_km": radius,
                "min_score": min_score,
                "industry": industry,
                "customer_type": customer_type,
                "include_business_context": include_business_context
            }
        }
    except Exception as e:
        logger.error(f"Error retrieving advanced leads by location: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve advanced leads by location"
        )


@router.get("/leads/territory-analysis")
async def get_territory_analysis(
    lat: float = Query(..., description="Territory center latitude"),
    lon: float = Query(..., description="Territory center longitude"),
    radius: float = Query(15.0, description="Territory radius in kilometers"),
    repository: CustomerRepository = Depends(get_customer_repository)
):
    """Get comprehensive territory analysis for sales planning"""
    try:
        from app.business_directory.models import Business
        from app.customer_360.models import CustomerBusinessRelationship, CustomerInteraction
        from sqlalchemy import text, func, and_
        
        # Get all customers in territory
        territory_customers = repository.db.query(Customer).join(
            CustomerBusinessRelationship,
            Customer.id == CustomerBusinessRelationship.customer_id
        ).join(
            Business,
            CustomerBusinessRelationship.business_id == Business.id
        ).filter(
            and_(
                Customer.is_active == True,
                Business.is_active == True,
                Business.latitude.isnot(None),
                Business.longitude.isnot(None),
                text("""
                    ST_DWithin(
                        ST_SetSRID(ST_MakePoint(businesses.longitude, businesses.latitude), 4326),
                        ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326),
                        :radius_meters
                    )
                """).bindparam(
                    longitude=lon,
                    latitude=lat,
                    radius_meters=radius * 1000
                )
            )
        ).distinct().all()
        
        # Calculate territory metrics
        total_customers = len(territory_customers)
        
        # Lead status distribution
        lead_status_dist = {}
        lead_scores = []
        customer_types = {}
        industries = {}
        
        for customer in territory_customers:
            # Lead status
            status = customer.lead_status or 'unknown'
            lead_status_dist[status] = lead_status_dist.get(status, 0) + 1
            
            # Lead scores
            if customer.lead_score:
                lead_scores.append(float(customer.lead_score))
            
            # Customer types
            ctype = customer.customer_type or 'unknown'
            customer_types[ctype] = customer_types.get(ctype, 0) + 1
            
            # Industries
            industry = customer.industry or 'unknown'
            industries[industry] = industries.get(industry, 0) + 1
        
        # Calculate interaction metrics
        customer_ids = [c.id for c in territory_customers]
        total_interactions = repository.db.query(CustomerInteraction).filter(
            CustomerInteraction.customer_id.in_(customer_ids)
        ).count() if customer_ids else 0
        
        # Recent activity (last 30 days)
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_interactions = repository.db.query(CustomerInteraction).filter(
            and_(
                CustomerInteraction.customer_id.in_(customer_ids),
                CustomerInteraction.interaction_date >= thirty_days_ago
            )
        ).count() if customer_ids else 0
        
        # Business density in territory
        territory_businesses = repository.db.query(Business).filter(
            and_(
                Business.is_active == True,
                Business.latitude.isnot(None),
                Business.longitude.isnot(None),
                text("""
                    ST_DWithin(
                        ST_SetSRID(ST_MakePoint(longitude, latitude), 4326),
                        ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326),
                        :radius_meters
                    )
                """).bindparam(
                    longitude=lon,
                    latitude=lat,
                    radius_meters=radius * 1000
                )
            )
        ).count()
        
        # Calculate territory area and density
        territory_area_km2 = 3.14159 * (radius ** 2)  # Approximate circular area
        customer_density = total_customers / territory_area_km2 if territory_area_km2 > 0 else 0
        business_density = territory_businesses / territory_area_km2 if territory_area_km2 > 0 else 0
        
        return {
            "territory_definition": {
                "center": {"lat": lat, "lon": lon},
                "radius_km": radius,
                "area_km2": round(territory_area_km2, 2)
            },
            "customer_metrics": {
                "total_customers": total_customers,
                "customer_density_per_km2": round(customer_density, 2),
                "lead_status_distribution": lead_status_dist,
                "customer_type_distribution": customer_types,
                "industry_distribution": industries,
                "average_lead_score": round(sum(lead_scores) / len(lead_scores), 2) if lead_scores else 0,
                "high_value_leads": len([s for s in lead_scores if s >= 70])
            },
            "activity_metrics": {
                "total_interactions": total_interactions,
                "recent_interactions_30d": recent_interactions,
                "interaction_rate": round(total_interactions / total_customers, 2) if total_customers > 0 else 0
            },
            "market_context": {
                "total_businesses": territory_businesses,
                "business_density_per_km2": round(business_density, 2),
                "market_penetration_rate": round((total_customers / territory_businesses * 100), 2) if territory_businesses > 0 else 0
            },
            "recommendations": [
                "Focus on high-value leads (score >= 70)" if len([s for s in lead_scores if s >= 70]) > 0 else "Develop lead scoring strategy",
                "Increase activity in territory" if recent_interactions < total_customers * 0.1 else "Maintain current activity level",
                "Explore untapped business opportunities" if total_customers < territory_businesses * 0.3 else "Territory well-penetrated"
            ]
        }
    except Exception as e:
        logger.error(f"Error performing territory analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform territory analysis"
        )