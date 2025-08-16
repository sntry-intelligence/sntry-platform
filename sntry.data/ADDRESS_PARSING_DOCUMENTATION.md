# Address Parsing Service Documentation

## Overview

The Address Parsing Service provides comprehensive parsing and standardization of Jamaican addresses using Libpostal when available, with a robust fallback implementation for environments where Libpostal is not installed.

## Features

### Core Functionality

1. **Address Parsing**: Extracts structured components from raw address strings
2. **Address Standardization**: Normalizes address formats for consistency
3. **Address Validation**: Validates parsed addresses against Jamaican standards
4. **Completeness Scoring**: Calculates quality scores for parsed addresses
5. **Geocoding Optimization**: Generates multiple address variations for better geocoding success

### Libpostal Integration

When Libpostal is available, the service provides:
- Advanced statistical address parsing using machine learning models
- Address expansion with multiple standardized variations
- Support for international address formats with Jamaican-specific post-processing

### Fallback Implementation

When Libpostal is not available, the service uses:
- Custom regex-based parsing for Jamaican address patterns
- Recognition of Jamaican postal zones, parishes, and cities
- Street type standardization and address component extraction

## Usage

### Basic Address Parsing

```python
from app.business_directory.data_processing import AddressParsingService

service = AddressParsingService()

# Parse a single address
address = "123 Hope Road, Kingston 6, St. Andrew, Jamaica"
parsed = service.parse_address(address)

print(f"House Number: {parsed.house_number}")
print(f"Street Name: {parsed.street_name}")
print(f"City: {parsed.city}")
print(f"Postal Zone: {parsed.postal_zone}")
print(f"Parish: {parsed.parish}")
print(f"Formatted: {parsed.formatted_address}")
```

### Address Validation

```python
# Validate parsed address
is_valid, issues = service.validate_parsed_address(parsed)
print(f"Valid: {is_valid}")
if issues:
    print(f"Issues: {', '.join(issues)}")

# Calculate completeness score
score = service.calculate_completeness_score(parsed)
print(f"Completeness: {score:.3f}")
```

### Batch Processing

```python
# Process multiple addresses
addresses = [
    "123 Main Street, Kingston 10, Jamaica",
    "P.O. Box 1234, Spanish Town 01, Jamaica",
    "456 Hope Road, New Kingston, Jamaica"
]

parsed_addresses = service.standardize_addresses(addresses)
for parsed in parsed_addresses:
    print(f"Formatted: {parsed.formatted_address}")
```

### Geocoding Optimization

```python
# Generate geocoding candidates
candidates = service.standardize_address_for_geocoding(parsed)
print(f"Generated {len(candidates)} geocoding candidates:")
for candidate in candidates:
    print(f"  - {candidate}")
```

### Address Expansion (Libpostal only)

```python
# Generate address variations (requires Libpostal)
if service.use_libpostal:
    variations = service.expand_address_variations(address)
    print(f"Generated {len(variations)} variations:")
    for variation in variations:
        print(f"  - {variation}")
```

## Address Components

### ParsedAddress Schema

```python
class ParsedAddress(BaseModel):
    house_number: Optional[str]      # Building/house number
    street_name: Optional[str]       # Street name
    po_box: Optional[str]           # PO Box number
    postal_zone: Optional[str]      # Jamaican postal zone (e.g., "KINGSTON 10")
    city: str                       # City name (required)
    parish: Optional[str]           # Jamaican parish
    country: str                    # Country (default: "JAMAICA")
    formatted_address: str          # Complete formatted address
```

### Jamaican Address Patterns

#### Postal Zones
- Format: `CITY ##` (e.g., "KINGSTON 10", "SPANISH TOWN 01")
- Used for precise area identification within cities

#### Parishes
Valid Jamaican parishes:
- KINGSTON, ST. ANDREW, ST. THOMAS, PORTLAND, ST. MARY
- ST. ANN, TRELAWNY, ST. JAMES, HANOVER, WESTMORELAND
- ST. ELIZABETH, MANCHESTER, CLARENDON, ST. CATHERINE

#### Cities and Towns
Major recognized cities:
- KINGSTON, SPANISH TOWN, PORTMORE, MONTEGO BAY, MAY PEN
- MANDEVILLE, OLD HARBOUR, SAVANNA-LA-MAR, OCHO RIOS
- PORT ANTONIO, HALF WAY TREE, NEW KINGSTON, etc.

## Validation Rules

### Address Validation

1. **Required Components**: Must have either street address OR PO Box
2. **City Validation**: City must be present and recognized
3. **Postal Zone Format**: Must match pattern `CITY ##` if present
4. **Parish Validation**: Must be valid Jamaican parish if present
5. **Country Validation**: Must be "JAMAICA"
6. **House Number Format**: Must be numeric with optional letter suffix

### Completeness Scoring

The completeness score (0-1) is calculated based on:

| Component | Weight | Bonus Conditions |
|-----------|--------|------------------|
| House Number | 1.0 | - |
| Street Name | 2.0 | +0.5 for length > 5 chars |
| PO Box | 1.5 | - |
| City | 2.0 | +0.5 for recognized city |
| Postal Zone | 1.5 | +0.5 for valid format |
| Parish | 1.0 | +0.5 for valid parish |
| Country | 0.5 | - |
| Street + Postal Zone | +1.0 | Bonus for both present |
| PO Box + Postal Zone | +1.0 | Bonus for both present |

Maximum possible score: 10.0 (normalized to 1.0)

## Configuration

### Environment Variables

```bash
# Optional: Libpostal data directory
LIBPOSTAL_DATA_DIR=/usr/local/share/libpostal

# Optional: Enable/disable Libpostal
USE_LIBPOSTAL=true
```

### Service Configuration

```python
# Initialize with custom settings
service = AddressParsingService()

# Check if Libpostal is available
if service.use_libpostal:
    print("Using Libpostal for advanced parsing")
else:
    print("Using fallback parsing method")
```

## Error Handling

### Common Exceptions

1. **ValueError**: Raised for empty or invalid input addresses
2. **ValidationError**: Raised when parsed components fail Pydantic validation
3. **ImportError**: Handled gracefully when Libpostal is not available

### Error Recovery

```python
try:
    parsed = service.parse_address(address)
except ValueError as e:
    print(f"Invalid address: {e}")
    # Handle invalid address
except Exception as e:
    print(f"Parsing error: {e}")
    # Create minimal ParsedAddress with raw data
    parsed = ParsedAddress(
        city="UNKNOWN",
        country="JAMAICA",
        formatted_address=address
    )
```

## Performance Considerations

### Libpostal Performance
- First run downloads ~2GB of language models
- Subsequent runs are fast (< 10ms per address)
- Memory usage: ~500MB for loaded models

### Fallback Performance
- No external dependencies
- Fast regex-based parsing (< 1ms per address)
- Low memory usage

### Optimization Tips

1. **Batch Processing**: Use `standardize_addresses()` for multiple addresses
2. **Caching**: Cache parsed results for frequently used addresses
3. **Pre-processing**: Clean addresses before parsing to improve success rates
4. **Geocoding**: Use `standardize_address_for_geocoding()` for better geocoding results

## Testing

### Unit Tests

```bash
# Run address parsing unit tests
python test_address_parsing_unit.py

# Run comprehensive integration tests
python test_libpostal_integration.py

# Run standalone tests
python test_address_parsing_standalone.py
```

### Test Coverage

The test suite covers:
- Basic address parsing for various formats
- PO Box handling
- Postal zone extraction
- Parish and city identification
- Address validation and scoring
- Batch processing
- Error handling and edge cases
- Libpostal integration (when available)

## Troubleshooting

### Common Issues

1. **"Libpostal not available"**: Install Libpostal C library and Python bindings
2. **Poor parsing results**: Check address format and consider pre-cleaning
3. **Low completeness scores**: Address may be incomplete or non-standard format
4. **Validation failures**: Address components may not match Jamaican standards

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable debug logging for detailed parsing information
service = AddressParsingService()
parsed = service.parse_address(address)
```

## Integration Examples

### With Geocoding Service

```python
# Generate optimized addresses for geocoding
geocoding_candidates = service.standardize_address_for_geocoding(parsed)

# Try each candidate until successful geocoding
for candidate in geocoding_candidates:
    result = geocoding_service.geocode(candidate)
    if result.status == 'OK':
        break
```

### With Data Cleaning Pipeline

```python
from app.business_directory.data_processing import DataCleaningService

# Combine with data cleaning
cleaning_service = DataCleaningService()
address_service = AddressParsingService()

# Clean raw business data
cleaned_businesses = cleaning_service.clean_business_data(raw_data)

# Parse and standardize addresses
for business in cleaned_businesses:
    parsed = address_service.parse_address(business.raw_address)
    business.standardized_address = parsed.formatted_address
```

## Future Enhancements

### Planned Features

1. **Machine Learning**: Custom ML models trained on Jamaican addresses
2. **Address Correction**: Automatic correction of common address errors
3. **Confidence Scoring**: Confidence levels for parsed components
4. **Multi-language Support**: Support for addresses in multiple languages
5. **Real-time Validation**: Integration with postal service APIs

### Contributing

To contribute to the address parsing functionality:

1. Add test cases for new address formats
2. Improve Jamaican-specific parsing rules
3. Enhance validation logic
4. Optimize performance for large datasets
5. Add support for additional Caribbean address formats