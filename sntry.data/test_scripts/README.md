# Test Scripts

This folder contains standalone test scripts for the Jamaica Business Directory project. These scripts are used for testing specific functionality without requiring the full application setup.

## Scripts

### `test_deduplication_standalone.py`
Basic tests for the deduplication engine functionality that work without external dependencies like RapidFuzz or Libpostal.

**Features tested:**
- Exact duplicate detection using hash comparison
- Business hash generation
- Field normalization for comparison
- Confidence level determination
- Merge priority determination
- Complete deduplication workflow

**Usage:**
```bash
python test_scripts/test_deduplication_standalone.py
```

### `test_deduplication_fuzzy.py`
Advanced tests for fuzzy matching functionality using RapidFuzz library.

**Features tested:**
- Fuzzy duplicate detection with similarity scoring
- Field similarity calculation for different data types
- Merge decision creation with fuzzy matches
- Complete workflow with both exact and fuzzy matching

**Requirements:**
- RapidFuzz library must be installed: `pip install rapidfuzz`

**Usage:**
```bash
python test_scripts/test_deduplication_fuzzy.py
```

### `demo_deduplication.py`
Comprehensive demonstration of the deduplication engine with realistic Jamaican business data.

**Features demonstrated:**
- Complete duplicate detection workflow
- Merge decision creation and prioritization
- Manual review queue management
- End-to-end deduplication process with detailed output

**Usage:**
```bash
python test_scripts/demo_deduplication.py
```

## Running Tests

All scripts can be run independently from the project root directory:

```bash
# Run basic deduplication tests
python test_scripts/test_deduplication_standalone.py

# Run fuzzy matching tests (requires RapidFuzz)
python test_scripts/test_deduplication_fuzzy.py

# Run comprehensive demonstration
python test_scripts/demo_deduplication.py
```

## Notes

- These scripts are designed to work without database connections or external API dependencies
- They use mock data and standalone functionality testing
- For full integration tests, use the test files in the `tests/` directory
- All scripts include detailed output showing the deduplication process in action