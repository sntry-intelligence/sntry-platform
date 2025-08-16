"""
Google MyMaps Integration Service
Handles automated layer updates and map management
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import json

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.business_directory.models import Business
from app.business_directory.schemas import BusinessSearchFilters
from app.business_directory.export_service import ExportService

logger = logging.getLogger(__name__)


class MyMapsService:
    """Service for Google MyMaps integration and automated updates"""
    
    def __init__(self, db: Session):
        self.db = db
        self.export_service = ExportService(db)
        self._service = None
    
    def _get_service(self):
        """Get authenticated Google Maps service"""
        if self._service is None:
            try:
                # Initialize Google API credentials
                # Note: This requires proper OAuth2 setup in production
                creds = None
                
                # Load credentials from settings or token file
                if hasattr(settings, 'GOOGLE_OAUTH_CREDENTIALS'):
                    creds = Credentials.from_authorized_user_info(
                        json.loads(settings.GOOGLE_OAUTH_CREDENTIALS)
                    )
                
                if not creds or not creds.valid:
                    if creds and creds.expired and creds.refresh_token:
                        creds.refresh(Request())
                    else:
                        logger.warning("Google OAuth credentials not available for MyMaps integration")
                        return None
                
                # Build the service
                self._service = build('mymaps', 'v1', credentials=creds)
                
            except Exception as e:
                logger.error(f"Error initializing Google MyMaps service: {e}")
                return None
        
        return self._service
    
    def create_map(self, title: str, description: str = None) -> Optional[str]:
        """Create a new Google MyMap"""
        try:
            service = self._get_service()
            if not service:
                return None
            
            map_data = {
                'title': title,
                'description': description or f"Jamaica Business Directory - Created {datetime.now().strftime('%Y-%m-%d')}"
            }
            
            result = service.maps().create(body=map_data).execute()
            map_id = result.get('id')
            
            logger.info(f"Created Google MyMap: {map_id} - {title}")
            return map_id
            
        except HttpError as e:
            logger.error(f"HTTP error creating MyMap: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating MyMap: {e}")
            return None    def c
reate_layer(self, map_id: str, layer_name: str, 
                    filters: Optional[BusinessSearchFilters] = None) -> Optional[str]:
        """Create a new layer in a Google MyMap with business data"""
        try:
            service = self._get_service()
            if not service:
                return None
            
            # Get businesses for the layer
            query = self.db.query(Business)
            query = self.export_service._apply_filters(query, filters)
            query = query.filter(Business.latitude.isnot(None), Business.longitude.isnot(None))
            businesses = query.all()
            
            if not businesses:
                logger.warning("No geocoded businesses found for layer creation")
                return None
            
            # Create layer
            layer_data = {
                'name': layer_name,
                'description': f"Business layer with {len(businesses)} locations"
            }
            
            layer_result = service.maps().layers().create(
                parent=f"maps/{map_id}",
                body=layer_data
            ).execute()
            
            layer_id = layer_result.get('id')
            
            # Add features (businesses) to the layer
            self._add_businesses_to_layer(map_id, layer_id, businesses)
            
            logger.info(f"Created layer {layer_id} with {len(businesses)} businesses")
            return layer_id
            
        except HttpError as e:
            logger.error(f"HTTP error creating layer: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating layer: {e}")
            return None
    
    def _add_businesses_to_layer(self, map_id: str, layer_id: str, businesses: List[Business]):
        """Add business features to a MyMaps layer"""
        try:
            service = self._get_service()
            if not service:
                return
            
            # Add businesses in batches to avoid API limits
            batch_size = 50
            for i in range(0, len(businesses), batch_size):
                batch = businesses[i:i + batch_size]
                features = []
                
                for business in batch:
                    feature = self._create_feature_from_business(business)
                    features.append(feature)
                
                # Batch create features
                if features:
                    batch_request = {
                        'features': features
                    }
                    
                    service.maps().layers().features().batchCreate(
                        parent=f"maps/{map_id}/layers/{layer_id}",
                        body=batch_request
                    ).execute()
                
                logger.info(f"Added batch of {len(features)} features to layer")
            
        except Exception as e:
            logger.error(f"Error adding businesses to layer: {e}")
    
    def _create_feature_from_business(self, business: Business) -> Dict[str, Any]:
        """Create a MyMaps feature from a business record"""
        # Build properties for the feature
        properties = {
            'name': business.name,
            'category': business.category or 'Uncategorized'
        }
        
        if business.phone_number:
            properties['phone'] = business.phone_number
        if business.email:
            properties['email'] = business.email
        if business.website:
            properties['website'] = business.website
        if business.rating:
            properties['rating'] = str(business.rating)
        
        address = business.standardized_address or business.raw_address
        properties['address'] = address
        
        # Create the feature
        feature = {
            'geometry': {
                'type': 'Point',
                'coordinates': [float(business.longitude), float(business.latitude)]
            },
            'properties': properties
        }
        
        return feature 
   def update_layer(self, map_id: str, layer_id: str, 
                    filters: Optional[BusinessSearchFilters] = None) -> bool:
        """Update an existing layer with fresh business data"""
        try:
            service = self._get_service()
            if not service:
                return False
            
            # Clear existing features in the layer
            self._clear_layer_features(map_id, layer_id)
            
            # Get fresh business data
            query = self.db.query(Business)
            query = self.export_service._apply_filters(query, filters)
            query = query.filter(Business.latitude.isnot(None), Business.longitude.isnot(None))
            businesses = query.all()
            
            # Add updated businesses to the layer
            self._add_businesses_to_layer(map_id, layer_id, businesses)
            
            logger.info(f"Updated layer {layer_id} with {len(businesses)} businesses")
            return True
            
        except Exception as e:
            logger.error(f"Error updating layer: {e}")
            return False
    
    def _clear_layer_features(self, map_id: str, layer_id: str):
        """Clear all features from a layer"""
        try:
            service = self._get_service()
            if not service:
                return
            
            # List all features in the layer
            features_response = service.maps().layers().features().list(
                parent=f"maps/{map_id}/layers/{layer_id}"
            ).execute()
            
            features = features_response.get('features', [])
            
            # Delete features in batches
            batch_size = 50
            for i in range(0, len(features), batch_size):
                batch = features[i:i + batch_size]
                feature_ids = [f.get('id') for f in batch if f.get('id')]
                
                if feature_ids:
                    for feature_id in feature_ids:
                        service.maps().layers().features().delete(
                            name=f"maps/{map_id}/layers/{layer_id}/features/{feature_id}"
                        ).execute()
            
            logger.info(f"Cleared {len(features)} features from layer {layer_id}")
            
        except Exception as e:
            logger.error(f"Error clearing layer features: {e}")
    
    def get_map_info(self, map_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a Google MyMap"""
        try:
            service = self._get_service()
            if not service:
                return None
            
            map_info = service.maps().get(name=f"maps/{map_id}").execute()
            return map_info
            
        except HttpError as e:
            logger.error(f"HTTP error getting map info: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting map info: {e}")
            return None
    
    def list_layers(self, map_id: str) -> List[Dict[str, Any]]:
        """List all layers in a Google MyMap"""
        try:
            service = self._get_service()
            if not service:
                return []
            
            layers_response = service.maps().layers().list(
                parent=f"maps/{map_id}"
            ).execute()
            
            return layers_response.get('layers', [])
            
        except Exception as e:
            logger.error(f"Error listing layers: {e}")
            return []