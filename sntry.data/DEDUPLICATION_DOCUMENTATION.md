# Deduplication Engine Documentation

## Overview

The Jamaica Business Directory includes a sophisticated deduplication engine that identifies and merges duplicate business records using both exact matching and fuzzy string matching techniques. The engine is designed to handle the common data quality issues found when scraping business information from multiple sources.

## Features

### 1. Exact Duplicate Detection
- Uses SHA-256 hashing of normalized business name and address
- Provides 100% confidence matches for identical records
- Automatically merges exact duplicates without manual review

### 2. Fuzzy String Matching
- Powered by RapidFuzz library for high-performance fuzzy matching
- Supports multiple matching strategies:
  - Token sort ratio for business names (handles word order variations)
  - Token set ratio for addresses (handles formatting differences)
  - Digit-only comparison for phone numbers
  - Simple ratio for emails and websites

### 3. Confidence Scoring
- **HIGH (≥90%)**: Automatic merge candidates
- **MEDIUM (70-89%)**: Manual review recommended
- **LOW (50-69%)**: Manual review required
- **NONE (<50%)**: Not considered duplicates

### 4. Intelligent Merging
- Prioritizes records with more complete data
- Preserves all available information during merging
- Uses business rules for field-specific merging:
  - Higher ratings are preferred
  - More recent scraping dates are preferred
  - Descriptions are combined when different
  - Contact information is preserved from both sources

### 5. Manual Review Queue
- Flags uncertain matches for human review
- Provides detailed similarity breakdowns
- Sorts by confidence score for prioritization
- Includes merge recommendations

## Usage

### Basic Deduplication

```python
from app.business_directory.data_processing import DeduplicationEngine
from app.business_directory.schemas import BusinessData

# Initialize the engine
engine = DeduplicationEngine(fuzzy_threshold=80.0)

# Your business data list
businesses = [...]  # List of BusinessData objects

# Run complete deduplication workflow
deduplicated_businesses, manual_review_items = engine.deduplicate_businesses(businesses)

print(f"Original: {len(businesses)} businesses")
print(f"After deduplication: {len(deduplicated_businesses)} businesses")
print(f"Manual review required: {len(manual_review_items)} items")
```

### Advanced Usage

```python
# Find duplicates without merging
matches = engine.find_duplicates(businesses)

# Create merge decisions
merge_decisions = engine.create_merge_decisions(matches)

# Get manual review queue
manual_review = engine.get_manual_review_queue(matches)

# Process manual review items
for match in manual_review:
    print(f"Confidence: {match.confidence_score:.1f}%")
    print(f"Business 1: {match.business1.name}")
    print(f"Business 2: {match.business2.name}")
    print(f"Matching fields: {match.matching_fields}")
    print(f"Similarity scores: {match.similarity_scores}")
```

### Configuration Options

```python
# Custom fuzzy threshold
engine = DeduplicationEngine(fuzzy_threshold=75.0)

# Custom exact match fields
engine = DeduplicationEngine(exact_match_fields=['name', 'phone_number'])

# Field weights for similarity calculation
engine.field_weights = {
    'name': 0.5,           # Business name (most important)
    'raw_address': 0.3,    # Address
    'phone_number': 0.15,  # Phone number
    'email': 0.05,         # Email address
    'website': 0.0         # Website (least important)
}
```

## Data Quality Improvements

The deduplication engine provides several data quality benefits:

1. **Eliminates Redundancy**: Removes duplicate entries from multiple sources
2. **Data Enrichment**: Combines information from multiple sources
3. **Standardization**: Normalizes data formats during comparison
4. **Quality Scoring**: Provides confidence metrics for data reliability

## Performance Considerations

- **RapidFuzz Dependency**: Fuzzy matching requires the RapidFuzz library
- **Memory Usage**: Scales quadratically with the number of businesses (O(n²))
- **Processing Time**: Approximately 1-2 seconds per 1000 business comparisons
- **Caching**: Results can be cached to avoid reprocessing

## Integration with Business Directory

The deduplication engine is integrated into the main data processing pipeline:

1. **After Scraping**: Raw scraped data is deduplicated before storage
2. **During Import**: Batch imports are deduplicated against existing data
3. **Maintenance**: Periodic deduplication runs clean up accumulated duplicates
4. **API Integration**: Real-time deduplication for new business submissions

## Testing

Run the comprehensive test suite to verify functionality:

```bash
python test_scripts/test_deduplication_comprehensive.py
```

This test demonstrates all features including:
- Exact and fuzzy matching
- Confidence scoring
- Manual review queue
- Complete workflow
- Data merging strategies

## Error Handling

The engine gracefully handles various error conditions:

- **Missing RapidFuzz**: Falls back to exact matching only
- **Invalid Data**: Skips malformed business records
- **Memory Constraints**: Processes data in batches for large datasets
- **Network Issues**: Continues processing despite individual failures

## Future Enhancements

Planned improvements include:

1. **Machine Learning**: ML-based duplicate detection
2. **Clustering**: Group similar businesses for batch review
3. **Active Learning**: Learn from manual review decisions
4. **Performance**: Optimize for larger datasets
5. **Integration**: Direct database integration for real-time processing