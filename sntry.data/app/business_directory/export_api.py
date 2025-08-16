"""
Business Directory Export API endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import logging
import io
import gzip

from app.core.database import get_postgres_db
from app.business_directory.export_service import ExportService
from app.business_directory.schemas import BusinessSearchFilters

logger = logging.getLogger(__name__)

router = APIRouter()


def get_export_service(db: Session = Depends(get_postgres_db)) -> ExportService:
    """Dependency to get export service"""
    return ExportService(db)


@router.get("/export/businesses/csv")
async def export_businesses_csv(
    # Search filters
    query: Optional[str] = Query(None, description="Search query"),
    category: Optional[str] = Query(None, description="Filter by category"),
    location: Optional[str] = Query(None, description="Filter by location"),
    is_active: bool = Query(True, description="Filter by active status"),
    
    # Spatial filters
    latitude: Optional[float] = Query(None, description="Latitude for spatial search"),
    longitude: Optional[float] = Query(None, description="Longitude for spatial search"),
    radius: Optional[float] = Query(None, description="Search radius in kilometers"),
    
    # Response options
    compress: bool = Query(False, description="Enable gzip compression"),
    
    export_service: ExportService = Depends(get_export_service)
):
    """Export businesses to CSV format with filtering and compression"""
    try:
        # Build filters
        filters = BusinessSearchFilters(
            query=query,
            category=category,
            location=location,
            is_active=is_active,
            latitude=latitude,
            longitude=longitude,
            radius=radius
        )
        
        # Generate CSV
        csv_data = export_service.export_to_csv(filters)
        
        # Prepare response
        if compress:
            # Compress the CSV data
            compressed_data = gzip.compress(csv_data.encode('utf-8'))
            return Response(
                content=compressed_data,
                media_type="application/gzip",
                headers={
                    "Content-Disposition": "attachment; filename=businesses_export.csv.gz",
                    "Content-Encoding": "gzip"
                }
            )
        else:
            return Response(
                content=csv_data,
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=businesses_export.csv"}
            )
            
    except Exception as e:
        logger.error(f"Error exporting businesses to CSV: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to export businesses to CSV"
        )@router.
get("/export/businesses/xlsx")
async def export_businesses_excel(
    # Search filters
    query: Optional[str] = Query(None, description="Search query"),
    category: Optional[str] = Query(None, description="Filter by category"),
    location: Optional[str] = Query(None, description="Filter by location"),
    is_active: bool = Query(True, description="Filter by active status"),
    
    # Spatial filters
    latitude: Optional[float] = Query(None, description="Latitude for spatial search"),
    longitude: Optional[float] = Query(None, description="Longitude for spatial search"),
    radius: Optional[float] = Query(None, description="Search radius in kilometers"),
    
    export_service: ExportService = Depends(get_export_service)
):
    """Export businesses to Excel format with multiple sheets"""
    try:
        # Build filters
        filters = BusinessSearchFilters(
            query=query,
            category=category,
            location=location,
            is_active=is_active,
            latitude=latitude,
            longitude=longitude,
            radius=radius
        )
        
        # Generate Excel file
        excel_data = export_service.export_to_excel(filters)
        
        # Create streaming response
        return StreamingResponse(
            io.BytesIO(excel_data),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=businesses_export.xlsx"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting businesses to Excel: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to export businesses to Excel"
        )


@router.get("/export/businesses/geojson")
async def export_businesses_geojson(
    # Search filters
    query: Optional[str] = Query(None, description="Search query"),
    category: Optional[str] = Query(None, description="Filter by category"),
    location: Optional[str] = Query(None, description="Filter by location"),
    is_active: bool = Query(True, description="Filter by active status"),
    
    # Spatial filters
    latitude: Optional[float] = Query(None, description="Latitude for spatial search"),
    longitude: Optional[float] = Query(None, description="Longitude for spatial search"),
    radius: Optional[float] = Query(None, description="Search radius in kilometers"),
    
    export_service: ExportService = Depends(get_export_service)
):
    """Export geocoded businesses to GeoJSON format for mapping"""
    try:
        # Build filters
        filters = BusinessSearchFilters(
            query=query,
            category=category,
            location=location,
            is_active=is_active,
            latitude=latitude,
            longitude=longitude,
            radius=radius
        )
        
        # Generate GeoJSON
        geojson_data = export_service.export_to_geojson(filters)
        
        return geojson_data
        
    except Exception as e:
        logger.error(f"Error exporting businesses to GeoJSON: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to export businesses to GeoJSON"
        )@rou
ter.get("/export/leads/csv")
async def export_leads_csv(
    # Lead qualification filters
    min_lead_score: float = Query(50.0, description="Minimum lead score (0-100)"),
    
    # Search filters
    query: Optional[str] = Query(None, description="Search query"),
    category: Optional[str] = Query(None, description="Filter by category"),
    location: Optional[str] = Query(None, description="Filter by location"),
    
    # Spatial filters
    latitude: Optional[float] = Query(None, description="Latitude for spatial search"),
    longitude: Optional[float] = Query(None, description="Longitude for spatial search"),
    radius: Optional[float] = Query(None, description="Search radius in kilometers"),
    
    # Response options
    compress: bool = Query(False, description="Enable gzip compression"),
    
    export_service: ExportService = Depends(get_export_service)
):
    """Export qualified leads to CSV format with lead scoring"""
    try:
        # Build filters
        filters = BusinessSearchFilters(
            query=query,
            category=category,
            location=location,
            is_active=True,  # Only active businesses for leads
            latitude=latitude,
            longitude=longitude,
            radius=radius
        )
        
        # Generate leads CSV
        csv_data = export_service.export_leads_to_csv(filters, min_lead_score)
        
        # Prepare response
        if compress:
            # Compress the CSV data
            compressed_data = gzip.compress(csv_data.encode('utf-8'))
            return Response(
                content=compressed_data,
                media_type="application/gzip",
                headers={
                    "Content-Disposition": "attachment; filename=qualified_leads.csv.gz",
                    "Content-Encoding": "gzip"
                }
            )
        else:
            return Response(
                content=csv_data,
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=qualified_leads.csv"}
            )
            
    except Exception as e:
        logger.error(f"Error exporting leads to CSV: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to export leads to CSV"
        )@
router.get("/map_data/kml")
async def export_businesses_kml(
    # Search filters
    query: Optional[str] = Query(None, description="Search query"),
    category: Optional[str] = Query(None, description="Filter by category"),
    location: Optional[str] = Query(None, description="Filter by location"),
    is_active: bool = Query(True, description="Filter by active status"),
    
    # Spatial filters
    latitude: Optional[float] = Query(None, description="Latitude for spatial search"),
    longitude: Optional[float] = Query(None, description="Longitude for spatial search"),
    radius: Optional[float] = Query(None, description="Search radius in kilometers"),
    
    export_service: ExportService = Depends(get_export_service)
):
    """Export geocoded businesses to KML format for Google MyMaps"""
    try:
        # Build filters
        filters = BusinessSearchFilters(
            query=query,
            category=category,
            location=location,
            is_active=is_active,
            latitude=latitude,
            longitude=longitude,
            radius=radius
        )
        
        # Generate KML
        kml_data = export_service.export_to_kml(filters)
        
        return Response(
            content=kml_data,
            media_type="application/vnd.google-earth.kml+xml",
            headers={"Content-Disposition": "attachment; filename=jamaica_businesses.kml"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting businesses to KML: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to export businesses to KML"
        )from a
pp.business_directory.mymaps_service import MyMapsService


def get_mymaps_service(db: Session = Depends(get_postgres_db)) -> MyMapsService:
    """Dependency to get MyMaps service"""
    return MyMapsService(db)


@router.post("/mymaps/create")
async def create_mymaps_map(
    title: str = Query(..., description="Map title"),
    description: Optional[str] = Query(None, description="Map description"),
    mymaps_service: MyMapsService = Depends(get_mymaps_service)
):
    """Create a new Google MyMaps map"""
    try:
        map_id = mymaps_service.create_map(title, description)
        
        if not map_id:
            raise HTTPException(
                status_code=503,
                detail="Google MyMaps service unavailable or authentication failed"
            )
        
        return {
            "map_id": map_id,
            "title": title,
            "description": description,
            "status": "created",
            "url": f"https://mymaps.google.com/viewer?mid={map_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating MyMaps map: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create MyMaps map"
        )


@router.post("/mymaps/{map_id}/layers")
async def create_mymaps_layer(
    map_id: str,
    layer_name: str = Query(..., description="Layer name"),
    
    # Search filters for businesses to include
    query: Optional[str] = Query(None, description="Search query"),
    category: Optional[str] = Query(None, description="Filter by category"),
    location: Optional[str] = Query(None, description="Filter by location"),
    
    # Spatial filters
    latitude: Optional[float] = Query(None, description="Latitude for spatial search"),
    longitude: Optional[float] = Query(None, description="Longitude for spatial search"),
    radius: Optional[float] = Query(None, description="Search radius in kilometers"),
    
    mymaps_service: MyMapsService = Depends(get_mymaps_service)
):
    """Create a new layer in a Google MyMaps map with filtered business data"""
    try:
        # Build filters
        filters = BusinessSearchFilters(
            query=query,
            category=category,
            location=location,
            is_active=True,
            latitude=latitude,
            longitude=longitude,
            radius=radius
        )
        
        layer_id = mymaps_service.create_layer(map_id, layer_name, filters)
        
        if not layer_id:
            raise HTTPException(
                status_code=503,
                detail="Failed to create layer - service unavailable or no data found"
            )
        
        return {
            "map_id": map_id,
            "layer_id": layer_id,
            "layer_name": layer_name,
            "status": "created",
            "filters_applied": filters.dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating MyMaps layer: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create MyMaps layer"
        )@
router.put("/mymaps/{map_id}/layers/{layer_id}")
async def update_mymaps_layer(
    map_id: str,
    layer_id: str,
    
    # Search filters for businesses to include
    query: Optional[str] = Query(None, description="Search query"),
    category: Optional[str] = Query(None, description="Filter by category"),
    location: Optional[str] = Query(None, description="Filter by location"),
    
    # Spatial filters
    latitude: Optional[float] = Query(None, description="Latitude for spatial search"),
    longitude: Optional[float] = Query(None, description="Longitude for spatial search"),
    radius: Optional[float] = Query(None, description="Search radius in kilometers"),
    
    mymaps_service: MyMapsService = Depends(get_mymaps_service)
):
    """Update an existing Google MyMaps layer with fresh business data"""
    try:
        # Build filters
        filters = BusinessSearchFilters(
            query=query,
            category=category,
            location=location,
            is_active=True,
            latitude=latitude,
            longitude=longitude,
            radius=radius
        )
        
        success = mymaps_service.update_layer(map_id, layer_id, filters)
        
        if not success:
            raise HTTPException(
                status_code=503,
                detail="Failed to update layer - service unavailable"
            )
        
        return {
            "map_id": map_id,
            "layer_id": layer_id,
            "status": "updated",
            "filters_applied": filters.dict(),
            "updated_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating MyMaps layer: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to update MyMaps layer"
        )


@router.get("/mymaps/{map_id}")
async def get_mymaps_info(
    map_id: str,
    mymaps_service: MyMapsService = Depends(get_mymaps_service)
):
    """Get information about a Google MyMaps map"""
    try:
        map_info = mymaps_service.get_map_info(map_id)
        
        if not map_info:
            raise HTTPException(
                status_code=404,
                detail="Map not found or service unavailable"
            )
        
        return {
            "map_info": map_info,
            "url": f"https://mymaps.google.com/viewer?mid={map_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting MyMaps info: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get MyMaps information"
        )


@router.get("/mymaps/{map_id}/layers")
async def list_mymaps_layers(
    map_id: str,
    mymaps_service: MyMapsService = Depends(get_mymaps_service)
):
    """List all layers in a Google MyMaps map"""
    try:
        layers = mymaps_service.list_layers(map_id)
        
        return {
            "map_id": map_id,
            "layers": layers,
            "total_layers": len(layers)
        }
        
    except Exception as e:
        logger.error(f"Error listing MyMaps layers: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to list MyMaps layers"
        )@
router.get("/export/customer-360/xlsx")
async def export_customer_360_excel(
    customer_ids: Optional[str] = Query(None, description="Comma-separated customer IDs to export"),
    export_service: ExportService = Depends(get_export_service)
):
    """Export comprehensive customer 360 profiles to Excel format"""
    try:
        # Parse customer IDs if provided
        customer_id_list = None
        if customer_ids:
            try:
                customer_id_list = [int(id.strip()) for id in customer_ids.split(',')]
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid customer IDs format. Use comma-separated integers."
                )
        
        # Generate Excel file
        excel_data = export_service.export_customer_360_to_excel(customer_id_list)
        
        # Create streaming response
        return StreamingResponse(
            io.BytesIO(excel_data),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=customer_360_export.xlsx"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting customer 360 to Excel: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to export customer 360 data to Excel"
        )


@router.get("/export/leads/qualified")
async def export_qualified_leads(
    min_score: float = Query(70.0, description="Minimum lead score for qualification"),
    max_results: int = Query(1000, description="Maximum number of leads to export"),
    format: str = Query("csv", regex="^(csv|json)$", description="Export format"),
    compress: bool = Query(False, description="Enable gzip compression for CSV"),
    export_service: ExportService = Depends(get_export_service)
):
    """Export sales-ready qualified leads"""
    try:
        if format == "csv":
            # Generate CSV
            csv_data = export_service.export_qualified_leads_to_csv(min_score, max_results)
            
            # Prepare response
            if compress:
                compressed_data = gzip.compress(csv_data.encode('utf-8'))
                return Response(
                    content=compressed_data,
                    media_type="application/gzip",
                    headers={
                        "Content-Disposition": "attachment; filename=qualified_leads.csv.gz",
                        "Content-Encoding": "gzip"
                    }
                )
            else:
                return Response(
                    content=csv_data,
                    media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=qualified_leads.csv"}
                )
        
        elif format == "json":
            # For JSON format, we'll return the data directly
            from app.customer_360.models import Customer
            
            customer_query = export_service.db.query(Customer).filter(
                Customer.is_active == True,
                Customer.lead_score >= min_score
            ).order_by(Customer.lead_score.desc()).limit(max_results)
            
            customers = customer_query.all()
            
            leads_data = []
            for customer in customers:
                lead_data = {
                    "customer_id": customer.id,
                    "lead_score": float(customer.lead_score) if customer.lead_score else 0,
                    "lead_status": customer.lead_status,
                    "name": f"{customer.first_name or ''} {customer.last_name or ''}".strip(),
                    "email": customer.email,
                    "phone": customer.phone_number,
                    "company": customer.company_name,
                    "industry": customer.industry,
                    "last_interaction": customer.last_interaction_at.isoformat() if customer.last_interaction_at else None,
                    "created_date": customer.created_at.isoformat() if customer.created_at else None
                }
                leads_data.append(lead_data)
            
            return {
                "qualified_leads": leads_data,
                "total_leads": len(leads_data),
                "min_score_threshold": min_score,
                "export_date": datetime.now().isoformat()
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting qualified leads: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to export qualified leads"
        )@router
.get("/export/analytics/dashboard-data")
async def export_dashboard_data(
    format: str = Query("json", regex="^(json|csv)$", description="Export format"),
    export_service: ExportService = Depends(get_export_service)
):
    """Export analytics dashboard data for BI tool integration"""
    try:
        dashboard_data = export_service.export_dashboard_data_to_json()
        
        if format == "json":
            return dashboard_data
        
        elif format == "csv":
            # Convert dashboard data to CSV format
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write metadata
            writer.writerow(["Dashboard Analytics Export"])
            writer.writerow(["Export Date", dashboard_data['export_metadata']['export_date']])
            writer.writerow([])
            
            # Business metrics
            writer.writerow(["Business Metrics"])
            writer.writerow(["Metric", "Value"])
            for key, value in dashboard_data['business_metrics'].items():
                if key != 'category_distribution':
                    writer.writerow([key.replace('_', ' ').title(), value])
            writer.writerow([])
            
            # Category distribution
            writer.writerow(["Business Categories"])
            writer.writerow(["Category", "Count"])
            for category, count in dashboard_data['business_metrics']['category_distribution'].items():
                writer.writerow([category, count])
            writer.writerow([])
            
            # Customer metrics
            writer.writerow(["Customer Metrics"])
            writer.writerow(["Metric", "Value"])
            for key, value in dashboard_data['customer_metrics'].items():
                if key not in ['lead_score_distribution', 'industry_distribution']:
                    writer.writerow([key.replace('_', ' ').title(), value])
            writer.writerow([])
            
            # Lead score distribution
            writer.writerow(["Lead Score Distribution"])
            writer.writerow(["Score Range", "Count"])
            for range_name, count in dashboard_data['customer_metrics']['lead_score_distribution'].items():
                writer.writerow([range_name.replace('_', ' ').title(), count])
            writer.writerow([])
            
            # KPIs
            writer.writerow(["Key Performance Indicators"])
            writer.writerow(["KPI", "Value"])
            for key, value in dashboard_data['kpis'].items():
                writer.writerow([key.replace('_', ' ').title(), f"{value:.2f}%" if isinstance(value, (int, float)) else value])
            
            csv_content = output.getvalue()
            return Response(
                content=csv_content,
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=dashboard_analytics.csv"}
            )
        
    except Exception as e:
        logger.error(f"Error exporting dashboard data: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to export dashboard data"
        )fr
om app.business_directory.scheduled_export_service import ScheduledExportService


def get_scheduled_export_service(db: Session = Depends(get_postgres_db)) -> ScheduledExportService:
    """Dependency to get scheduled export service"""
    return ScheduledExportService(db)


@router.post("/export/reports/daily")
async def generate_daily_report(
    send_email: bool = Query(False, description="Send report via email"),
    recipients: Optional[str] = Query(None, description="Comma-separated email recipients"),
    scheduled_service: ScheduledExportService = Depends(get_scheduled_export_service)
):
    """Generate and optionally email daily business intelligence report"""
    try:
        report = scheduled_service.generate_daily_report()
        
        if send_email and recipients:
            recipient_list = [email.strip() for email in recipients.split(',')]
            scheduled_service.send_report_email(report, recipient_list)
            report['email_sent'] = True
            report['recipients'] = recipient_list
        
        return report
        
    except Exception as e:
        logger.error(f"Error generating daily report: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate daily report"
        )


@router.post("/export/reports/weekly")
async def generate_weekly_report(
    send_email: bool = Query(False, description="Send report via email"),
    recipients: Optional[str] = Query(None, description="Comma-separated email recipients"),
    scheduled_service: ScheduledExportService = Depends(get_scheduled_export_service)
):
    """Generate and optionally email weekly business intelligence report"""
    try:
        report = scheduled_service.generate_weekly_report()
        
        if send_email and recipients:
            recipient_list = [email.strip() for email in recipients.split(',')]
            scheduled_service.send_report_email(report, recipient_list)
            report['email_sent'] = True
            report['recipients'] = recipient_list
        
        return report
        
    except Exception as e:
        logger.error(f"Error generating weekly report: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate weekly report"
        )


@router.post("/export/reports/monthly")
async def generate_monthly_report(
    send_email: bool = Query(False, description="Send report via email"),
    recipients: Optional[str] = Query(None, description="Comma-separated email recipients"),
    scheduled_service: ScheduledExportService = Depends(get_scheduled_export_service)
):
    """Generate and optionally email monthly business intelligence report"""
    try:
        report = scheduled_service.generate_monthly_report()
        
        if send_email and recipients:
            recipient_list = [email.strip() for email in recipients.split(',')]
            scheduled_service.send_report_email(report, recipient_list)
            report['email_sent'] = True
            report['recipients'] = recipient_list
        
        return report
        
    except Exception as e:
        logger.error(f"Error generating monthly report: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate monthly report"
        )