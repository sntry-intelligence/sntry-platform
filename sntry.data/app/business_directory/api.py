"""
Business Directory API endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from app.core.database import get_postgres_db
from app.business_directory.repository import BusinessRepository
from app.business_directory.schemas import (
    BusinessCreate, BusinessUpdate, BusinessResponse, 
    BusinessSearchFilters, BusinessSearchResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_business_repository(db: Session = Depends(get_postgres_db)) -> BusinessRepository:
    """Dependency to get business repository"""
    return BusinessRepository(db)


@router.get("/health")
async def business_health():
    """Business directory health check"""
    return {"status": "healthy", "module": "business_directory"}


@router.post("/businesses", response_model=BusinessResponse, status_code=status.HTTP_201_CREATED)
async def create_business(
    business_data: BusinessCreate,
    repository: BusinessRepository = Depends(get_business_repository)
):
    """Create a new business record"""
    try:
        db_business = repository.create(business_data)
        logger.info(f"Created business: {db_business.id} - {db_business.name}")
        return db_business
    except Exception as e:
        logger.error(f"Error creating business: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create business record"
        )


@router.get("/businesses", response_model=BusinessSearchResponse)
async def get_businesses(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    category: Optional[str] = Query(None, description="Filter by business category"),
    location: Optional[str] = Query(None, description="Filter by location"),
    query: Optional[str] = Query(None, description="Search query for name, description, or address"),
    is_active: bool = Query(True, description="Filter by active status"),
    order_by: str = Query("name", description="Field to order by"),
    order_direction: str = Query("asc", regex="^(asc|desc)$", description="Order direction"),
    repository: BusinessRepository = Depends(get_business_repository)
):
    """Get businesses with pagination and filtering"""
    try:
        filters = BusinessSearchFilters(
            query=query,
            category=category,
            location=location,
            is_active=is_active
        )
        
        businesses, total = repository.search(
            filters=filters,
            skip=skip,
            limit=limit,
            order_by=order_by,
            order_direction=order_direction
        )
        
        return BusinessSearchResponse(
            businesses=businesses,
            total=total,
            skip=skip,
            limit=limit,
            filters=filters
        )
    except Exception as e:
        logger.error(f"Error retrieving businesses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve businesses"
        )


@router.get("/businesses/{business_id}", response_model=BusinessResponse)
async def get_business(
    business_id: int,
    repository: BusinessRepository = Depends(get_business_repository)
):
    """Get business by ID"""
    try:
        business = repository.get_by_id(business_id)
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Business with ID {business_id} not found"
            )
        return business
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving business {business_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve business"
        )


@router.put("/businesses/{business_id}", response_model=BusinessResponse)
async def update_business(
    business_id: int,
    business_update: BusinessUpdate,
    repository: BusinessRepository = Depends(get_business_repository)
):
    """Update business by ID"""
    try:
        updated_business = repository.update(business_id, business_update)
        if not updated_business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Business with ID {business_id} not found"
            )
        logger.info(f"Updated business: {business_id}")
        return updated_business
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating business {business_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update business"
        )


@router.patch("/businesses/{business_id}", response_model=BusinessResponse)
async def patch_business(
    business_id: int,
    business_update: BusinessUpdate,
    repository: BusinessRepository = Depends(get_business_repository)
):
    """Partially update business by ID"""
    try:
        updated_business = repository.update(business_id, business_update)
        if not updated_business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Business with ID {business_id} not found"
            )
        logger.info(f"Patched business: {business_id}")
        return updated_business
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error patching business {business_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update business"
        )


@router.delete("/businesses/{business_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_business(
    business_id: int,
    hard_delete: bool = Query(False, description="Perform hard delete instead of soft delete"),
    repository: BusinessRepository = Depends(get_business_repository)
):
    """Delete business by ID (soft delete by default)"""
    try:
        if hard_delete:
            success = repository.hard_delete(business_id)
        else:
            success = repository.soft_delete(business_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Business with ID {business_id} not found"
            )
        
        logger.info(f"{'Hard' if hard_delete else 'Soft'} deleted business: {business_id}")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting business {business_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete business"
        )


@router.get("/businesses/search")
async def search_businesses(
    q: str = Query(..., description="Search query"),
    category: Optional[str] = Query(None, description="Filter by category"),
    radius: Optional[float] = Query(None, description="Search radius in kilometers"),
    lat: Optional[float] = Query(None, description="Latitude for location search"),
    lon: Optional[float] = Query(None, description="Longitude for location search")
):
    """Search businesses with advanced filtering"""
    # Placeholder implementation - will be completed in later tasks
    return {
        "businesses": [],
        "query": q,
        "filters": {
            "category": category,
            "radius": radius,
            "location": {"lat": lat, "lon": lon} if lat and lon else None
        }
    }


@router.get("/businesses/nearby")
async def get_nearby_businesses(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    radius: float = Query(5.0, description="Search radius in kilometers")
):
    """Get businesses within radius of coordinates"""
    # Placeholder implementation - will be completed in later tasks
    return {
        "businesses": [],
        "center": {"lat": lat, "lon": lon},
        "radius": radius
    }

@rout
er.get("/businesses/search")
async def search_businesses(
    q: str = Query(..., description="Search query"),
    category: Optional[str] = Query(None, description="Filter by category"),
    radius: Optional[float] = Query(None, description="Search radius in kilometers"),
    lat: Optional[float] = Query(None, description="Latitude for location search"),
    lon: Optional[float] = Query(None, description="Longitude for location search"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    repository: BusinessRepository = Depends(get_business_repository)
):
    """Search businesses with advanced filtering"""
    try:
        filters = BusinessSearchFilters(
            query=q,
            category=category,
            latitude=lat,
            longitude=lon,
            radius=radius,
            is_active=True
        )
        
        businesses, total = repository.search(
            filters=filters,
            skip=skip,
            limit=limit
        )
        
        return {
            "businesses": businesses,
            "total": total,
            "skip": skip,
            "limit": limit,
            "query": q,
            "filters": {
                "category": category,
                "radius": radius,
                "location": {"lat": lat, "lon": lon} if lat and lon else None
            }
        }
    except Exception as e:
        logger.error(f"Error searching businesses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search businesses"
        )


@router.get("/businesses/nearby")
async def get_nearby_businesses(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    radius: float = Query(5.0, description="Search radius in kilometers"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results"),
    repository: BusinessRepository = Depends(get_business_repository)
):
    """Get businesses within radius of coordinates"""
    try:
        results = repository.find_nearby(
            latitude=lat,
            longitude=lon,
            radius_km=radius,
            category=category,
            limit=limit
        )
        
        # Format results with distance information
        businesses_with_distance = []
        for business, distance_km in results:
            business_dict = BusinessResponse.from_orm(business).dict()
            business_dict["distance_km"] = round(distance_km, 2)
            businesses_with_distance.append(business_dict)
        
        return {
            "businesses": businesses_with_distance,
            "center": {"lat": lat, "lon": lon},
            "radius": radius,
            "total": len(businesses_with_distance)
        }
    except Exception as e:
        logger.error(f"Error finding nearby businesses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to find nearby businesses"
        )


@router.get("/businesses/categories")
async def get_business_categories(
    repository: BusinessRepository = Depends(get_business_repository)
):
    """Get all unique business categories"""
    try:
        categories = repository.get_categories()
        return {
            "categories": sorted(categories),
            "total": len(categories)
        }
    except Exception as e:
        logger.error(f"Error retrieving business categories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve business categories"
        )


@router.get("/businesses/statistics")
async def get_business_statistics(
    repository: BusinessRepository = Depends(get_business_repository)
):
    """Get business database statistics"""
    try:
        stats = repository.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"Error retrieving business statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve business statistics"
        )


@router.post("/businesses/bulk", response_model=List[BusinessResponse], status_code=status.HTTP_201_CREATED)
async def bulk_create_businesses(
    businesses_data: List[BusinessCreate],
    repository: BusinessRepository = Depends(get_business_repository)
):
    """Bulk create multiple business records"""
    try:
        if len(businesses_data) > 1000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create more than 1000 businesses at once"
            )
        
        db_businesses = repository.bulk_create(businesses_data)
        logger.info(f"Bulk created {len(db_businesses)} businesses")
        return db_businesses
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error bulk creating businesses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to bulk create businesses"
        )
@
router.get("/businesses/analytics/market-analysis")
async def get_market_analysis(
    category: Optional[str] = Query(None, description="Business category for analysis"),
    lat: Optional[float] = Query(None, description="Latitude for geographic analysis"),
    lon: Optional[float] = Query(None, description="Longitude for geographic analysis"),
    radius: Optional[float] = Query(None, description="Analysis radius in kilometers"),
    repository: BusinessRepository = Depends(get_business_repository)
):
    """Get market analysis and geospatial analytics"""
    try:
        from sqlalchemy import func, text
        from app.business_directory.models import Business
        
        # Base query for market analysis
        query = repository.db.query(Business).filter(Business.is_active == True)
        
        # Apply category filter
        if category:
            query = query.filter(Business.category.ilike(f"%{category}%"))
        
        # Apply geographic filter if coordinates provided
        if all([lat, lon, radius]):
            point = text(f"ST_SetSRID(ST_MakePoint({lon}, {lat}), 4326)")
            radius_meters = radius * 1000
            query = query.filter(
                text(f"ST_DWithin(geom, {point}, {radius_meters})")
            )
        
        businesses = query.all()
        
        # Calculate analytics
        total_businesses = len(businesses)
        
        # Category distribution
        category_counts = {}
        for business in businesses:
            cat = business.category or "Uncategorized"
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        # Geographic distribution (if coordinates provided)
        geographic_analysis = {}
        if all([lat, lon]) and businesses:
            # Calculate average distance from center point
            distances = []
            for business in businesses:
                if business.latitude and business.longitude:
                    # Simple distance calculation (not precise but good for analysis)
                    lat_diff = float(business.latitude) - lat
                    lon_diff = float(business.longitude) - lon
                    distance = (lat_diff**2 + lon_diff**2)**0.5 * 111  # Rough km conversion
                    distances.append(distance)
            
            if distances:
                geographic_analysis = {
                    "average_distance_km": round(sum(distances) / len(distances), 2),
                    "max_distance_km": round(max(distances), 2),
                    "min_distance_km": round(min(distances), 2),
                    "businesses_with_coordinates": len(distances)
                }
        
        # Geocoding completeness
        geocoded_count = sum(1 for b in businesses if b.latitude and b.longitude)
        geocoding_completeness = (geocoded_count / total_businesses * 100) if total_businesses > 0 else 0
        
        return {
            "analysis_parameters": {
                "category": category,
                "center": {"lat": lat, "lon": lon} if lat and lon else None,
                "radius_km": radius
            },
            "summary": {
                "total_businesses": total_businesses,
                "geocoded_businesses": geocoded_count,
                "geocoding_completeness_percent": round(geocoding_completeness, 2)
            },
            "category_distribution": dict(sorted(category_counts.items(), key=lambda x: x[1], reverse=True)),
            "geographic_analysis": geographic_analysis
        }
    except Exception as e:
        logger.error(f"Error performing market analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform market analysis"
        )


@router.get("/businesses/analytics/density-heatmap")
async def get_business_density_heatmap(
    category: Optional[str] = Query(None, description="Business category filter"),
    grid_size: float = Query(0.01, description="Grid size in degrees (default 0.01 ≈ 1km)"),
    repository: BusinessRepository = Depends(get_business_repository)
):
    """Get business density data for heatmap visualization"""
    try:
        from sqlalchemy import func, text
        from app.business_directory.models import Business
        
        # Build query with spatial aggregation
        query = repository.db.query(
            func.floor(Business.latitude / grid_size).label('lat_grid'),
            func.floor(Business.longitude / grid_size).label('lon_grid'),
            func.count(Business.id).label('business_count'),
            func.avg(Business.latitude).label('avg_lat'),
            func.avg(Business.longitude).label('avg_lon')
        ).filter(
            and_(
                Business.is_active == True,
                Business.latitude.isnot(None),
                Business.longitude.isnot(None)
            )
        )
        
        if category:
            query = query.filter(Business.category.ilike(f"%{category}%"))
        
        # Group by grid cells
        results = query.group_by('lat_grid', 'lon_grid').all()
        
        # Format for heatmap
        heatmap_data = []
        for result in results:
            heatmap_data.append({
                "lat": float(result.avg_lat),
                "lon": float(result.avg_lon),
                "intensity": result.business_count,
                "grid_lat": result.lat_grid,
                "grid_lon": result.lon_grid
            })
        
        return {
            "heatmap_data": heatmap_data,
            "parameters": {
                "category": category,
                "grid_size_degrees": grid_size,
                "total_grid_cells": len(heatmap_data)
            },
            "statistics": {
                "max_density": max([point["intensity"] for point in heatmap_data]) if heatmap_data else 0,
                "total_businesses": sum([point["intensity"] for point in heatmap_data])
            }
        }
    except Exception as e:
        logger.error(f"Error generating density heatmap: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate density heatmap"
        )


@router.get("/businesses/search/advanced")
async def advanced_business_search(
    # Text search parameters
    query: Optional[str] = Query(None, description="Search query"),
    name: Optional[str] = Query(None, description="Business name search"),
    description: Optional[str] = Query(None, description="Description search"),
    
    # Category and classification
    category: Optional[str] = Query(None, description="Category filter"),
    categories: Optional[str] = Query(None, description="Multiple categories (comma-separated)"),
    
    # Location parameters
    address: Optional[str] = Query(None, description="Address search"),
    parish: Optional[str] = Query(None, description="Jamaican parish filter"),
    postal_zone: Optional[str] = Query(None, description="Postal zone filter"),
    
    # Spatial parameters
    lat: Optional[float] = Query(None, description="Latitude for spatial search"),
    lon: Optional[float] = Query(None, description="Longitude for spatial search"),
    radius: Optional[float] = Query(None, description="Search radius in kilometers"),
    
    # Contact information
    has_phone: Optional[bool] = Query(None, description="Filter businesses with phone numbers"),
    has_email: Optional[bool] = Query(None, description="Filter businesses with email addresses"),
    has_website: Optional[bool] = Query(None, description="Filter businesses with websites"),
    
    # Data quality filters
    is_geocoded: Optional[bool] = Query(None, description="Filter geocoded businesses"),
    geocode_status: Optional[str] = Query(None, description="Geocoding status filter"),
    min_rating: Optional[float] = Query(None, description="Minimum rating filter"),
    
    # Pagination and sorting
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    order_by: str = Query("name", description="Field to order by"),
    order_direction: str = Query("asc", regex="^(asc|desc)$", description="Order direction"),
    
    repository: BusinessRepository = Depends(get_business_repository)
):
    """Advanced business search with comprehensive filtering options"""
    try:
        from app.business_directory.models import Business
        
        query_builder = repository.db.query(Business).filter(Business.is_active == True)
        
        # Text search filters
        if query:
            search_term = f"%{query}%"
            query_builder = query_builder.filter(
                or_(
                    Business.name.ilike(search_term),
                    Business.description.ilike(search_term),
                    Business.raw_address.ilike(search_term),
                    Business.standardized_address.ilike(search_term),
                    Business.category.ilike(search_term)
                )
            )
        
        if name:
            query_builder = query_builder.filter(Business.name.ilike(f"%{name}%"))
        
        if description:
            query_builder = query_builder.filter(Business.description.ilike(f"%{description}%"))
        
        # Category filters
        if category:
            query_builder = query_builder.filter(Business.category.ilike(f"%{category}%"))
        
        if categories:
            category_list = [cat.strip() for cat in categories.split(",")]
            category_filters = [Business.category.ilike(f"%{cat}%") for cat in category_list]
            query_builder = query_builder.filter(or_(*category_filters))
        
        # Location filters
        if address:
            address_term = f"%{address}%"
            query_builder = query_builder.filter(
                or_(
                    Business.raw_address.ilike(address_term),
                    Business.standardized_address.ilike(address_term)
                )
            )
        
        if parish:
            query_builder = query_builder.filter(
                or_(
                    Business.raw_address.ilike(f"%{parish}%"),
                    Business.standardized_address.ilike(f"%{parish}%")
                )
            )
        
        if postal_zone:
            query_builder = query_builder.filter(
                or_(
                    Business.raw_address.ilike(f"%{postal_zone}%"),
                    Business.standardized_address.ilike(f"%{postal_zone}%")
                )
            )
        
        # Spatial filtering
        if all([lat, lon, radius]):
            from geoalchemy2.functions import ST_DWithin, ST_MakePoint, ST_SetSRID
            point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)
            radius_meters = radius * 1000
            query_builder = query_builder.filter(ST_DWithin(Business.geom, point, radius_meters))
        
        # Contact information filters
        if has_phone is not None:
            if has_phone:
                query_builder = query_builder.filter(Business.phone_number.isnot(None))
            else:
                query_builder = query_builder.filter(Business.phone_number.is_(None))
        
        if has_email is not None:
            if has_email:
                query_builder = query_builder.filter(Business.email.isnot(None))
            else:
                query_builder = query_builder.filter(Business.email.is_(None))
        
        if has_website is not None:
            if has_website:
                query_builder = query_builder.filter(Business.website.isnot(None))
            else:
                query_builder = query_builder.filter(Business.website.is_(None))
        
        # Data quality filters
        if is_geocoded is not None:
            if is_geocoded:
                query_builder = query_builder.filter(
                    and_(
                        Business.latitude.isnot(None),
                        Business.longitude.isnot(None)
                    )
                )
            else:
                query_builder = query_builder.filter(
                    or_(
                        Business.latitude.is_(None),
                        Business.longitude.is_(None)
                    )
                )
        
        if geocode_status:
            query_builder = query_builder.filter(Business.geocode_status == geocode_status)
        
        if min_rating is not None:
            query_builder = query_builder.filter(Business.rating >= min_rating)
        
        # Get total count before pagination
        total = query_builder.count()
        
        # Apply sorting
        order_column = getattr(Business, order_by, Business.name)
        if order_direction.lower() == "desc":
            query_builder = query_builder.order_by(desc(order_column))
        else:
            query_builder = query_builder.order_by(asc(order_column))
        
        # Apply pagination
        businesses = query_builder.offset(skip).limit(limit).all()
        
        return {
            "businesses": [BusinessResponse.from_orm(business).dict() for business in businesses],
            "total": total,
            "skip": skip,
            "limit": limit,
            "search_parameters": {
                "query": query,
                "name": name,
                "description": description,
                "category": category,
                "categories": categories,
                "address": address,
                "parish": parish,
                "postal_zone": postal_zone,
                "spatial_search": {
                    "lat": lat,
                    "lon": lon,
                    "radius_km": radius
                } if all([lat, lon, radius]) else None,
                "contact_filters": {
                    "has_phone": has_phone,
                    "has_email": has_email,
                    "has_website": has_website
                },
                "quality_filters": {
                    "is_geocoded": is_geocoded,
                    "geocode_status": geocode_status,
                    "min_rating": min_rating
                }
            }
        }
    except Exception as e:
        logger.error(f"Error performing advanced business search: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform advanced search"
        )


@router.get("/businesses/spatial/within-polygon")
async def get_businesses_within_polygon(
    polygon_coords: str = Query(..., description="Polygon coordinates as JSON string: [[lat,lon],[lat,lon],...]"),
    category: Optional[str] = Query(None, description="Category filter"),
    limit: int = Query(1000, ge=1, le=5000, description="Maximum number of results"),
    repository: BusinessRepository = Depends(get_business_repository)
):
    """Get businesses within a custom polygon area"""
    try:
        import json
        from sqlalchemy import text
        
        # Parse polygon coordinates
        try:
            coords = json.loads(polygon_coords)
            if not isinstance(coords, list) or len(coords) < 3:
                raise ValueError("Polygon must have at least 3 coordinates")
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid polygon coordinates: {e}"
            )
        
        # Build PostGIS polygon query
        # Convert coordinates to WKT format
        coord_pairs = [f"{lon} {lat}" for lat, lon in coords]
        # Close the polygon by adding the first point at the end
        if coord_pairs[0] != coord_pairs[-1]:
            coord_pairs.append(coord_pairs[0])
        
        wkt_coords = ", ".join(coord_pairs)
        polygon_wkt = f"POLYGON(({wkt_coords}))"
        
        # Build query
        from app.business_directory.models import Business
        query = repository.db.query(Business).filter(
            and_(
                Business.is_active == True,
                Business.geom.isnot(None),
                text(f"ST_Within(geom, ST_GeomFromText('{polygon_wkt}', 4326))")
            )
        )
        
        if category:
            query = query.filter(Business.category.ilike(f"%{category}%"))
        
        businesses = query.limit(limit).all()
        
        return {
            "businesses": [BusinessResponse.from_orm(business).dict() for business in businesses],
            "total": len(businesses),
            "polygon_coordinates": coords,
            "filters": {
                "category": category
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finding businesses within polygon: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to find businesses within polygon"
        )


@router.get("/businesses/spatial/route-optimization")
async def get_route_optimized_businesses(
    start_lat: float = Query(..., description="Starting latitude"),
    start_lon: float = Query(..., description="Starting longitude"),
    business_ids: str = Query(..., description="Comma-separated business IDs to visit"),
    repository: BusinessRepository = Depends(get_business_repository)
):
    """Get businesses optimized for route planning (simple nearest-neighbor approach)"""
    try:
        # Parse business IDs
        try:
            ids = [int(id.strip()) for id in business_ids.split(",")]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid business IDs format"
            )
        
        # Get businesses
        businesses = repository.get_by_ids(ids)
        
        # Filter out businesses without coordinates
        geocoded_businesses = [
            b for b in businesses 
            if b.latitude and b.longitude
        ]
        
        if not geocoded_businesses:
            return {
                "optimized_route": [],
                "total_businesses": 0,
                "message": "No geocoded businesses found"
            }
        
        # Simple nearest-neighbor route optimization
        route = []
        current_lat, current_lon = start_lat, start_lon
        remaining_businesses = geocoded_businesses.copy()
        
        while remaining_businesses:
            # Find nearest business
            nearest_business = None
            min_distance = float('inf')
            
            for business in remaining_businesses:
                # Simple distance calculation
                lat_diff = float(business.latitude) - current_lat
                lon_diff = float(business.longitude) - current_lon
                distance = (lat_diff**2 + lon_diff**2)**0.5
                
                if distance < min_distance:
                    min_distance = distance
                    nearest_business = business
            
            if nearest_business:
                route.append({
                    "business": BusinessResponse.from_orm(nearest_business).dict(),
                    "order": len(route) + 1,
                    "distance_from_previous": round(min_distance * 111, 2)  # Rough km conversion
                })
                
                current_lat = float(nearest_business.latitude)
                current_lon = float(nearest_business.longitude)
                remaining_businesses.remove(nearest_business)
        
        # Calculate total route distance
        total_distance = sum([stop["distance_from_previous"] for stop in route])
        
        return {
            "optimized_route": route,
            "total_businesses": len(route),
            "total_distance_km": round(total_distance, 2),
            "start_location": {"lat": start_lat, "lon": start_lon},
            "note": "This is a simple nearest-neighbor optimization. For production use, consider more sophisticated algorithms."
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error optimizing business route: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to optimize business route"
        )