"""Create business data schema with PostGIS support

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create business data schema and tables with PostGIS support"""
    
    # Enable PostGIS extension
    op.execute('CREATE EXTENSION IF NOT EXISTS postgis;')
    
    # Create business_data schema
    op.execute('CREATE SCHEMA IF NOT EXISTS business_data;')
    
    # Create businesses table
    op.create_table(
        'businesses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('raw_address', sa.Text(), nullable=False),
        sa.Column('standardized_address', sa.Text(), nullable=True),
        sa.Column('phone_number', sa.String(length=50), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('website', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('operating_hours', sa.Text(), nullable=True),
        sa.Column('rating', sa.Numeric(precision=2, scale=1), nullable=True),
        
        # Geospatial columns
        sa.Column('latitude', sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column('longitude', sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column('geom', geoalchemy2.Geography(geometry_type='POINT', srid=4326), nullable=True),
        sa.Column('google_place_id', sa.String(length=255), nullable=True),
        
        # Metadata columns
        sa.Column('source_url', sa.String(length=255), nullable=False),
        sa.Column('last_scraped_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_geocoded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('scrape_status', sa.String(length=50), nullable=True, default='pending'),
        sa.Column('geocode_status', sa.String(length=50), nullable=True, default='pending'),
        
        # Audit columns
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        
        sa.PrimaryKeyConstraint('id'),
        schema='business_data'
    )
    
    # Create indexes for efficient querying
    op.create_index('idx_businesses_id', 'businesses', ['id'], unique=False, schema='business_data')
    op.create_index('idx_businesses_name', 'businesses', ['name'], unique=False, schema='business_data')
    op.create_index('idx_businesses_category', 'businesses', ['category'], unique=False, schema='business_data')
    op.create_index('idx_businesses_active', 'businesses', ['is_active'], unique=False, schema='business_data')
    op.create_index('idx_businesses_scraped_at', 'businesses', ['last_scraped_at'], unique=False, schema='business_data')
    
    # Create spatial index for geospatial queries using PostGIS
    op.execute('CREATE INDEX idx_businesses_geom ON business_data.businesses USING GIST (geom);')
    
    # Create composite indexes for common query patterns
    op.create_index('idx_businesses_category_active', 'businesses', ['category', 'is_active'], unique=False, schema='business_data')
    op.create_index('idx_businesses_scrape_status', 'businesses', ['scrape_status'], unique=False, schema='business_data')
    op.create_index('idx_businesses_geocode_status', 'businesses', ['geocode_status'], unique=False, schema='business_data')
    
    # Create trigger to automatically update the updated_at timestamp
    op.execute("""
        CREATE OR REPLACE FUNCTION business_data.update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    op.execute("""
        CREATE TRIGGER update_businesses_updated_at 
        BEFORE UPDATE ON business_data.businesses 
        FOR EACH ROW EXECUTE FUNCTION business_data.update_updated_at_column();
    """)
    
    # Create trigger to automatically update geom column when lat/lng changes
    op.execute("""
        CREATE OR REPLACE FUNCTION business_data.update_geom_from_lat_lng()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.latitude IS NOT NULL AND NEW.longitude IS NOT NULL THEN
                NEW.geom = ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326)::geography;
            ELSE
                NEW.geom = NULL;
            END IF;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    op.execute("""
        CREATE TRIGGER update_businesses_geom 
        BEFORE INSERT OR UPDATE ON business_data.businesses 
        FOR EACH ROW EXECUTE FUNCTION business_data.update_geom_from_lat_lng();
    """)


def downgrade() -> None:
    """Drop business data schema and related objects"""
    
    # Drop triggers
    op.execute('DROP TRIGGER IF EXISTS update_businesses_geom ON business_data.businesses;')
    op.execute('DROP TRIGGER IF EXISTS update_businesses_updated_at ON business_data.businesses;')
    
    # Drop functions
    op.execute('DROP FUNCTION IF EXISTS business_data.update_geom_from_lat_lng();')
    op.execute('DROP FUNCTION IF EXISTS business_data.update_updated_at_column();')
    
    # Drop table (indexes will be dropped automatically)
    op.drop_table('businesses', schema='business_data')
    
    # Drop schema
    op.execute('DROP SCHEMA IF EXISTS business_data CASCADE;')