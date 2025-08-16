"""
Customer 360 Repository Layer with CRUD operations and analytics
"""
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc, asc, text
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta
import logging

from app.customer_360.models import Customer, CustomerInteraction, CustomerBusinessRelationship
from app.business_directory.models import Business
from app.customer_360.schemas import (
    CustomerCreate, CustomerUpdate, CustomerInteractionCreate,
    CustomerBusinessRelationshipCreate, LeadSearchFilters
)

logger = logging.getLogger(__name__)


class CustomerRepository:
    """Repository class for customer 360 data operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_customer(self, customer_data: CustomerCreate) -> Customer:
        """Create a new customer record"""
        try:
            db_customer = Customer(
                external_id=customer_data.external_id,
                first_name=customer_data.first_name,
                last_name=customer_data.last_name,
                email=str(customer_data.email) if customer_data.email else None,
                phone_number=customer_data.phone_number,
                address=customer_data.address,
                customer_type=customer_data.customer_type,
                industry=customer_data.industry,
                company_name=customer_data.company_name,
                source_system=customer_data.source_system,
                is_active=True,
                lead_status='new'
            )
            
            self.db.add(db_customer)
            self.db.commit()
            self.db.refresh(db_customer)
            
            logger.info(f"Created customer record: {db_customer.id} - {db_customer.email}")
            return db_customer
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Error creating customer record: {e}")
            raise
    
    def get_customer_by_id(self, customer_id: int) -> Optional[Customer]:
        """Get customer by ID with relationships"""
        try:
            return self.db.query(Customer).options(
                joinedload(Customer.interactions),
                joinedload(Customer.business_relationships)
            ).filter(Customer.id == customer_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving customer {customer_id}: {e}")
            raise
    
    def get_customer_by_email(self, email: str) -> Optional[Customer]:
        """Get customer by email"""
        try:
            return self.db.query(Customer).filter(Customer.email == email).first()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving customer by email {email}: {e}")
            raise
    
    def update_customer(self, customer_id: int, customer_update: CustomerUpdate) -> Optional[Customer]:
        """Update customer record"""
        try:
            db_customer = self.get_customer_by_id(customer_id)
            if not db_customer:
                return None
            
            # Update only provided fields
            update_data = customer_update.dict(exclude_unset=True)
            for field, value in update_data.items():
                if field == 'email' and value:
                    value = str(value)
                setattr(db_customer, field, value)
            
            self.db.commit()
            self.db.refresh(db_customer)
            
            logger.info(f"Updated customer record: {customer_id}")
            return db_customer
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Error updating customer {customer_id}: {e}")
            raise
    
    def create_interaction(self, interaction_data: CustomerInteractionCreate) -> CustomerInteraction:
        """Create a new customer interaction"""
        try:
            db_interaction = CustomerInteraction(
                customer_id=interaction_data.customer_id,
                interaction_type=interaction_data.interaction_type,
                interaction_channel=interaction_data.interaction_channel,
                subject=interaction_data.subject,
                description=interaction_data.description,
                outcome=interaction_data.outcome,
                interaction_date=interaction_data.interaction_date,
                duration_minutes=interaction_data.duration_minutes,
                created_by=interaction_data.created_by
            )
            
            self.db.add(db_interaction)
            
            # Update customer's last interaction timestamp
            customer = self.get_customer_by_id(interaction_data.customer_id)
            if customer:
                customer.last_interaction_at = interaction_data.interaction_date
            
            self.db.commit()
            self.db.refresh(db_interaction)
            
            logger.info(f"Created interaction for customer {interaction_data.customer_id}")
            return db_interaction
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Error creating customer interaction: {e}")
            raise
    
    def create_business_relationship(
        self, 
        relationship_data: CustomerBusinessRelationshipCreate
    ) -> CustomerBusinessRelationship:
        """Create a customer-business relationship"""
        try:
            db_relationship = CustomerBusinessRelationship(
                customer_id=relationship_data.customer_id,
                business_id=relationship_data.business_id,
                relationship_type=relationship_data.relationship_type,
                relationship_status=relationship_data.relationship_status,
                start_date=relationship_data.start_date,
                end_date=relationship_data.end_date,
                notes=relationship_data.notes
            )
            
            self.db.add(db_relationship)
            self.db.commit()
            self.db.refresh(db_relationship)
            
            logger.info(f"Created business relationship: customer {relationship_data.customer_id} -> business {relationship_data.business_id}")
            return db_relationship
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Error creating business relationship: {e}")
            raise
    
    def get_customer_360_view(self, customer_id: int) -> Optional[Dict[str, Any]]:
        """Get comprehensive 360-degree customer view"""
        try:
            customer = self.get_customer_by_id(customer_id)
            if not customer:
                return None
            
            # Get interactions with aggregations
            interactions = self.db.query(CustomerInteraction).filter(
                CustomerInteraction.customer_id == customer_id
            ).order_by(desc(CustomerInteraction.interaction_date)).all()
            
            # Get business relationships with business details
            relationships = self.db.query(
                CustomerBusinessRelationship, Business
            ).join(
                Business, CustomerBusinessRelationship.business_id == Business.id
            ).filter(
                CustomerBusinessRelationship.customer_id == customer_id
            ).all()
            
            # Calculate metrics
            total_interactions = len(interactions)
            last_interaction_date = interactions[0].interaction_date if interactions else None
            
            # Calculate interaction frequency (interactions per month)
            if total_interactions > 0 and customer.created_at:
                months_since_creation = max(1, (datetime.utcnow() - customer.created_at).days / 30)
                interaction_frequency = total_interactions / months_since_creation
            else:
                interaction_frequency = 0
            
            # Calculate engagement scores (simplified scoring algorithm)
            engagement_score = min(100, total_interactions * 10)  # 10 points per interaction, max 100
            
            # Recency score (higher for more recent interactions)
            if last_interaction_date:
                days_since_last = (datetime.utcnow() - last_interaction_date).days
                recency_score = max(0, 100 - days_since_last)  # 1 point lost per day
            else:
                recency_score = 0
            
            # Frequency score based on interaction frequency
            frequency_score = min(100, interaction_frequency * 20)  # 20 points per interaction/month
            
            return {
                "customer": customer,
                "interactions": interactions,
                "business_relationships": [rel for rel, _ in relationships],
                "connected_businesses": [business for _, business in relationships],
                "total_interactions": total_interactions,
                "last_interaction_date": last_interaction_date,
                "interaction_frequency": round(interaction_frequency, 2),
                "engagement_score": round(engagement_score, 2),
                "recency_score": round(recency_score, 2),
                "frequency_score": round(frequency_score, 2),
                "social_media_presence": {},  # Placeholder for future implementation
                "churn_probability": None,  # Placeholder for ML model
                "lifetime_value_prediction": None,  # Placeholder for ML model
                "next_best_action": self._suggest_next_action(customer, interactions)
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving customer 360 view for {customer_id}: {e}")
            raise
    
    def get_leads(
        self, 
        filters: LeadSearchFilters,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get qualified leads based on filters"""
        try:
            query = self.db.query(Customer)
            
            # Apply filters
            if filters.min_score is not None:
                query = query.filter(Customer.lead_score >= filters.min_score)
            
            if filters.max_score is not None:
                query = query.filter(Customer.lead_score <= filters.max_score)
            
            if filters.lead_status:
                query = query.filter(Customer.lead_status == filters.lead_status)
            
            if filters.industry:
                query = query.filter(Customer.industry.ilike(f"%{filters.industry}%"))
            
            if filters.location:
                query = query.filter(Customer.address.ilike(f"%{filters.location}%"))
            
            # Only active customers
            query = query.filter(Customer.is_active == True)
            
            # Get total count
            total = query.count()
            
            # Apply pagination and ordering
            customers = query.order_by(desc(Customer.lead_score)).offset(skip).limit(limit).all()
            
            # Enrich with lead information
            leads = []
            for customer in customers:
                lead_data = self._enrich_lead_data(customer)
                leads.append(lead_data)
            
            return leads, total
            
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving leads: {e}")
            raise
    
    def get_leads_by_location(
        self, 
        latitude: float, 
        longitude: float, 
        radius_km: float,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get leads within geographic area"""
        try:
            # For now, we'll use a simple text-based location search
            # In a full implementation, we'd geocode customer addresses and use spatial queries
            
            # Get customers with business relationships to geocoded businesses
            leads_query = self.db.query(Customer).join(
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
            
            # Use raw SQL for spatial filtering
            spatial_filter = text("""
                ST_DWithin(
                    ST_SetSRID(ST_MakePoint(businesses.longitude, businesses.latitude), 4326),
                    ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326),
                    :radius_meters
                )
            """)
            
            leads_query = leads_query.filter(
                spatial_filter.bindparam(
                    longitude=longitude,
                    latitude=latitude,
                    radius_meters=radius_km * 1000
                )
            )
            
            customers = leads_query.distinct().limit(limit).all()
            
            # Enrich with lead information
            leads = []
            for customer in customers:
                lead_data = self._enrich_lead_data(customer)
                # Add location information
                lead_data["location"] = {"lat": latitude, "lon": longitude}
                leads.append(lead_data)
            
            return leads
            
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving leads by location: {e}")
            raise
    
    def update_lead_score(self, customer_id: int, score: float) -> bool:
        """Update customer lead score"""
        try:
            customer = self.get_customer_by_id(customer_id)
            if not customer:
                return False
            
            customer.lead_score = score
            self.db.commit()
            
            logger.info(f"Updated lead score for customer {customer_id}: {score}")
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Error updating lead score for customer {customer_id}: {e}")
            raise
    
    def _enrich_lead_data(self, customer: Customer) -> Dict[str, Any]:
        """Enrich customer data with lead-specific information"""
        try:
            # Get interaction count
            interaction_count = self.db.query(CustomerInteraction).filter(
                CustomerInteraction.customer_id == customer.id
            ).count()
            
            # Get business relationships
            relationships = self.db.query(
                CustomerBusinessRelationship, Business
            ).join(
                Business, CustomerBusinessRelationship.business_id == Business.id
            ).filter(
                CustomerBusinessRelationship.customer_id == customer.id
            ).all()
            
            # Generate lead reasons
            lead_reasons = []
            if customer.lead_score > 50:
                lead_reasons.append("High lead score")
            if interaction_count > 5:
                lead_reasons.append("High engagement history")
            if len(relationships) > 0:
                lead_reasons.append("Connected to local businesses")
            if customer.company_name:
                lead_reasons.append("Business customer")
            
            # Generate recommended actions
            recommended_actions = []
            if customer.last_interaction_at:
                days_since_last = (datetime.utcnow() - customer.last_interaction_at).days
                if days_since_last > 30:
                    recommended_actions.append("Follow up - no recent interaction")
            else:
                recommended_actions.append("Initial contact - no previous interactions")
            
            if customer.lead_status == 'new':
                recommended_actions.append("Qualify lead")
            elif customer.lead_status == 'qualified':
                recommended_actions.append("Schedule meeting")
            
            return {
                "customer": customer,
                "lead_score": customer.lead_score,
                "lead_reasons": lead_reasons,
                "business_connections": [
                    {
                        "business_id": business.id,
                        "business_name": business.name,
                        "relationship_type": rel.relationship_type
                    }
                    for rel, business in relationships
                ],
                "recommended_actions": recommended_actions,
                "interaction_count": interaction_count
            }
            
        except Exception as e:
            logger.error(f"Error enriching lead data for customer {customer.id}: {e}")
            return {
                "customer": customer,
                "lead_score": customer.lead_score,
                "lead_reasons": [],
                "business_connections": [],
                "recommended_actions": [],
                "interaction_count": 0
            }
    
    def _suggest_next_action(self, customer: Customer, interactions: List[CustomerInteraction]) -> str:
        """Suggest next best action for customer"""
        if not interactions:
            return "Initial contact and needs assessment"
        
        last_interaction = interactions[0]
        days_since_last = (datetime.utcnow() - last_interaction.interaction_date).days
        
        if days_since_last > 60:
            return "Re-engagement campaign"
        elif days_since_last > 30:
            return "Follow-up contact"
        elif customer.lead_status == 'new':
            return "Lead qualification"
        elif customer.lead_status == 'qualified':
            return "Schedule product demo"
        elif customer.lead_status == 'contacted':
            return "Send proposal"
        else:
            return "Maintain regular contact"
    
    def get_customer_statistics(self) -> Dict[str, Any]:
        """Get customer database statistics"""
        try:
            stats = {}
            
            # Total counts
            stats['total_customers'] = self.db.query(Customer).count()
            stats['active_customers'] = self.db.query(Customer).filter(Customer.is_active == True).count()
            
            # Lead status distribution
            lead_status_counts = self.db.query(
                Customer.lead_status, func.count(Customer.id)
            ).filter(Customer.is_active == True).group_by(Customer.lead_status).all()
            
            stats['lead_status_distribution'] = {status: count for status, count in lead_status_counts}
            
            # Customer type distribution
            customer_type_counts = self.db.query(
                Customer.customer_type, func.count(Customer.id)
            ).filter(
                and_(Customer.is_active == True, Customer.customer_type.isnot(None))
            ).group_by(Customer.customer_type).all()
            
            stats['customer_type_distribution'] = {ctype: count for ctype, count in customer_type_counts}
            
            # Interaction statistics
            stats['total_interactions'] = self.db.query(CustomerInteraction).count()
            
            # Average lead score
            avg_lead_score = self.db.query(func.avg(Customer.lead_score)).filter(
                Customer.is_active == True
            ).scalar()
            stats['average_lead_score'] = float(avg_lead_score) if avg_lead_score else 0
            
            return stats
            
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving customer statistics: {e}")
            raise