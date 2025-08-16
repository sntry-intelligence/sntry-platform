
---
inclusion: always
---

# Development Guardrails

## Bounded Context Enforcement
- Stay within the Operational Business Intelligence domain
- Focus on business directory data processing, customer 360 profiles, and lead generation
- Avoid creating features outside core business value: data extraction, processing, geocoding, and customer insights

## Anti-Overengineering Principles
- **Minimal Viable Implementation**: Create only essential functionality to meet requirements
- **No Speculative Features**: Don't build features "just in case" - implement only what's explicitly needed
- **Reuse Before Create**: Check existing modules before creating new files or functions
- **Single Responsibility**: Each module should have one clear purpose within the business domain

## File Creation Guidelines
- **No Redundant Files**: Before creating new files, verify similar functionality doesn't exist
- **Domain Alignment**: New files must clearly belong to either `business_directory` or `customer_360` domains
- **Standard Patterns**: Follow existing patterns (api.py, models.py, schemas.py, repository.py, tasks.py)
- **Justify Creation**: Each new file should solve a specific business problem

## Code Complexity Limits
- **Function Length**: Keep functions under 50 lines when possible
- **Class Complexity**: Limit classes to single domain concepts
- **Dependency Depth**: Avoid deep dependency chains - prefer composition over inheritance
- **Configuration Simplicity**: Use existing config patterns rather than creating new configuration systems

## Business Domain Boundaries
- **Business Directory**: Web scraping, data processing, geocoding, deduplication
- **Customer 360**: Customer profiles, lead scoring, analytics
- **Core Infrastructure**: Database, caching, messaging, configuration
- **No Cross-Domain Logic**: Keep business logic within appropriate domain boundaries