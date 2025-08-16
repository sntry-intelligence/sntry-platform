-- PostgreSQL initialization script for Jamaica Business Directory

-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Create schemas
CREATE SCHEMA IF NOT EXISTS business_data;
CREATE SCHEMA IF NOT EXISTS customer_data;

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA business_data TO postgres;
GRANT ALL PRIVILEGES ON SCHEMA customer_data TO postgres;

-- Create business_data tables
CREATE TABLE IF NOT EXISTS business_data.businesses (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    raw_address TEXT NOT NULL,
    standardized_address TEXT,
    phone_number VARCHAR(50),
    email VARCHAR(255),
    website VARCHAR(255),
    description TEXT,
    operating_hours TEXT,
    rating NUMERIC(2,1),
    
    -- Geospatial columns
    latitude NUMERIC(10, 7),
    longitude NUMERIC(10, 7),
    geom GEOGRAPHY(Point, 4326),
    google_place_id VARCHAR(255),
    
    -- Metadata
    source_url VARCHAR(255) NOT NULL,
    last_scraped_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_geocoded_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    scrape_status VARCHAR(50) DEFAULT 'pending',
    geocode_status VARCHAR(50) DEFAULT 'pending',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for business_data.businesses
CREATE INDEX IF NOT EXISTS idx_businesses_geom ON business_data.businesses USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_businesses_category ON business_data.businesses (category);
CREATE INDEX IF NOT EXISTS idx_businesses_active ON business_data.businesses (is_active);
CREATE INDEX IF NOT EXISTS idx_businesses_scraped_at ON business_data.businesses (last_scraped_at);
CREATE INDEX IF NOT EXISTS idx_businesses_name ON business_data.businesses (name);
CREATE INDEX IF NOT EXISTS idx_businesses_scrape_status ON business_data.businesses (scrape_status);
CREATE INDEX IF NOT EXISTS idx_businesses_geocode_status ON business_data.businesses (geocode_status);

-- Create customer_data tables
CREATE TABLE IF NOT EXISTS customer_data.customers (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(100) UNIQUE,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(255) UNIQUE,
    phone_number VARCHAR(50),
    address TEXT,
    
    -- Customer segmentation
    customer_type VARCHAR(50),
    industry VARCHAR(100),
    company_name VARCHAR(255),
    
    -- Lead scoring
    lead_score NUMERIC(5, 2) DEFAULT 0,
    lead_status VARCHAR(50) DEFAULT 'new',
    
    -- Metadata
    source_system VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    last_interaction_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for customer_data.customers
CREATE INDEX IF NOT EXISTS idx_customers_email ON customer_data.customers (email);
CREATE INDEX IF NOT EXISTS idx_customers_external_id ON customer_data.customers (external_id);
CREATE INDEX IF NOT EXISTS idx_customers_active ON customer_data.customers (is_active);
CREATE INDEX IF NOT EXISTS idx_customers_lead_score ON customer_data.customers (lead_score);
CREATE INDEX IF NOT EXISTS idx_customers_lead_status ON customer_data.customers (lead_status);
CREATE INDEX IF NOT EXISTS idx_customers_source_system ON customer_data.customers (source_system);

-- Create customer interactions table
CREATE TABLE IF NOT EXISTS customer_data.customer_interactions (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customer_data.customers(id) ON DELETE CASCADE,
    interaction_type VARCHAR(50) NOT NULL,
    interaction_channel VARCHAR(50),
    subject VARCHAR(255),
    description TEXT,
    outcome VARCHAR(100),
    
    -- Interaction metadata
    interaction_date TIMESTAMP WITH TIME ZONE NOT NULL,
    duration_minutes INTEGER,
    created_by VARCHAR(100),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for customer_data.customer_interactions
CREATE INDEX IF NOT EXISTS idx_interactions_customer_id ON customer_data.customer_interactions (customer_id);
CREATE INDEX IF NOT EXISTS idx_interactions_type ON customer_data.customer_interactions (interaction_type);
CREATE INDEX IF NOT EXISTS idx_interactions_date ON customer_data.customer_interactions (interaction_date);
CREATE INDEX IF NOT EXISTS idx_interactions_channel ON customer_data.customer_interactions (interaction_channel);

-- Create customer-business relationships table
CREATE TABLE IF NOT EXISTS customer_data.customer_business_relationships (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customer_data.customers(id) ON DELETE CASCADE,
    business_id INTEGER NOT NULL REFERENCES business_data.businesses(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL,
    relationship_status VARCHAR(50) DEFAULT 'active',
    
    -- Relationship metadata
    start_date TIMESTAMP WITH TIME ZONE,
    end_date TIMESTAMP WITH TIME ZONE,
    notes TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(customer_id, business_id, relationship_type)
);

-- Create indexes for customer_data.customer_business_relationships
CREATE INDEX IF NOT EXISTS idx_relationships_customer_id ON customer_data.customer_business_relationships (customer_id);
CREATE INDEX IF NOT EXISTS idx_relationships_business_id ON customer_data.customer_business_relationships (business_id);
CREATE INDEX IF NOT EXISTS idx_relationships_type ON customer_data.customer_business_relationships (relationship_type);
CREATE INDEX IF NOT EXISTS idx_relationships_status ON customer_data.customer_business_relationships (relationship_status);

-- Create trigger function for updating updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at columns
CREATE TRIGGER update_businesses_updated_at 
    BEFORE UPDATE ON business_data.businesses 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_customers_updated_at 
    BEFORE UPDATE ON customer_data.customers 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_relationships_updated_at 
    BEFORE UPDATE ON customer_data.customer_business_relationships 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert sample data for testing (optional)
-- INSERT INTO business_data.businesses (name, category, raw_address, source_url, last_scraped_at)
-- VALUES ('Sample Business', 'Restaurant', '123 Main Street, Kingston, Jamaica', 'https://example.com', NOW());

-- Grant all necessary permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA business_data TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA customer_data TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA business_data TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA customer_data TO postgres;