# Jamaica Business Directory

A comprehensive data engineering pipeline that extracts business contact and address information from Jamaica Yellow Pages online directories, transforms this raw data into standardized geocoded records, and provides dynamic visualization and customer 360 capabilities.

## Features

- **Web Scraping**: Automated extraction from Jamaica Yellow Pages directories
- **Data Processing**: Address standardization, geocoding, and deduplication
- **Geospatial Integration**: PostGIS-powered location-based queries and mapping
- **Customer 360**: Comprehensive customer profiles and lead generation
- **Real-time Streaming**: Kafka-based event streaming architecture
- **Background Processing**: Celery-powered asynchronous task processing
- **RESTful API**: FastAPI-based endpoints with automatic documentation
- **Multi-database Support**: PostgreSQL for operational data, SQL Server for data warehouse

## Architecture

The system follows a microservices architecture with:

- **Data Acquisition Layer**: Playwright-based web scraping with anti-bot measures
- **Data Processing Layer**: Address parsing, geocoding, and deduplication
- **Storage Layer**: PostgreSQL with PostGIS, Redis caching, SQL Server data warehouse
- **API Layer**: FastAPI with background task processing
- **Streaming Layer**: Apache Kafka for real-time data streams
- **Visualization Layer**: Google Maps integration and export capabilities

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- PostgreSQL with PostGIS
- Redis
- Apache Kafka
- Microsoft SQL Server (optional, for data warehouse)

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd jamaica-business-directory
   ```

2. **Copy environment configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start services with Docker Compose**
   ```bash
   docker-compose up -d
   ```

4. **Install Python dependencies (for local development)**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

6. **Start the application**
   ```bash
   uvicorn app.main:app --reload
   ```

The API will be available at `http://localhost:8000` with automatic documentation at `http://localhost:8000/docs`.

### Production Deployment

For production deployment, use the production Docker Compose configuration:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

## API Endpoints

### Business Directory
- `GET /api/v1/business/businesses` - List businesses with pagination and filtering
- `POST /api/v1/business/businesses` - Create new business record
- `GET /api/v1/business/businesses/{id}` - Get business by ID
- `PUT /api/v1/business/businesses/{id}` - Update business
- `DELETE /api/v1/business/businesses/{id}` - Delete business
- `GET /api/v1/business/businesses/search` - Advanced business search
- `GET /api/v1/business/businesses/nearby` - Location-based search

### Customer 360
- `GET /api/v1/customer/customers` - List customers
- `POST /api/v1/customer/customers` - Create customer profile
- `GET /api/v1/customer/customers/{id}/360-view` - Comprehensive customer view
- `GET /api/v1/customer/leads` - Get qualified leads
- `GET /api/v1/customer/leads/by-location` - Location-based lead generation

## Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# Database
POSTGRES_HOST=localhost
POSTGRES_DB=jamaica_business_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Google APIs
GOOGLE_MAPS_API_KEY=your_api_key
GOOGLE_GEOCODING_API_KEY=your_api_key

# Kafka
KAFKA_BOOTSTRAP_SERVERS=["localhost:9092"]
```

### Database Schemas

The system uses two main schemas:
- `business_data`: Business information and geospatial data
- `customer_data`: Customer profiles, interactions, and relationships

## Background Tasks

Celery workers handle:
- Daily web scraping operations
- Batch geocoding of addresses
- Customer data synchronization
- Lead scoring calculations
- Data quality checks

## Testing

Run the test suite:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov=app
```

## Development

### Code Style

The project uses:
- Black for code formatting
- Flake8 for linting
- MyPy for type checking

Format code:
```bash
black app/
flake8 app/
mypy app/
```

### Database Migrations

Create new migration:
```bash
alembic revision --autogenerate -m "Description of changes"
```

Apply migrations:
```bash
alembic upgrade head
```

## Monitoring

### Health Checks

- Application: `GET /health`
- Business module: `GET /api/v1/business/health`
- Customer module: `GET /api/v1/customer/health`

### Logging

Logs are written to:
- Console output
- `logs/app.log` - Application logs
- `logs/error.log` - Error logs
- `logs/celery.log` - Background task logs

### Development Tools

When running with Docker Compose, additional tools are available:
- Kafka UI: `http://localhost:8080`
- Redis Commander: `http://localhost:8081`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions, please open an issue in the GitHub repository.