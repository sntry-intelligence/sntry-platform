#!/usr/bin/env python3
"""
Unit tests for address parsing functionality without database dependencies.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from business_directory.data_processing import AddressParsingService
from business_directory.schemas import ParsedAddress


def test_address_parsing_service():
    """Test the AddressParsingService functionality."""
    service = AddressParsingService()
    
    # Test 1: Basic address with postal zone
    address = "123 Main Street, Kingston 10, Jamaica"
    parsed = service.parse_address(address)
    
    assert parsed.house_number == "123"
    assert "MAIN STREET" in parsed.street_name
    assert parsed.city == "KINGSTON"
    assert parsed.postal_zone == "KINGSTON 10"
    assert parsed.country == "JAMAICA"
    
    print("✅ Test 1 passed: Basic address parsing")
    
    # Test 2: PO Box address
    address = "P.O. Box 1234, Spanish Town 01, Jamaica"
    parsed = service.parse_address(address)
    
    assert parsed.po_box == "PO BOX 1234"
    assert parsed.city == "SPANISH TOWN"
    assert parsed.postal_zone == "SPANISH TOWN 01"
    assert parsed.country == "JAMAICA"
    
    print("✅ Test 2 passed: PO Box address parsing")
    
    # Test 3: Address with parish
    address = "456 Hope Road, Kingston 6, St. Andrew, Jamaica"
    parsed = service.parse_address(address)
    
    assert parsed.house_number == "456"
    assert "HOPE ROAD" in parsed.street_name
    assert parsed.city == "KINGSTON"
    assert parsed.parish == "ST. ANDREW"
    assert parsed.country == "JAMAICA"
    
    print("✅ Test 3 passed: Address with parish")
    
    # Test 4: Validation
    is_valid, issues = service.validate_parsed_address(parsed)
    assert isinstance(is_valid, bool)
    assert isinstance(issues, list)
    
    print("✅ Test 4 passed: Address validation")
    
    # Test 5: Completeness scoring
    score = service.calculate_completeness_score(parsed)
    assert 0.0 <= score <= 1.0
    
    print("✅ Test 5 passed: Completeness scoring")
    
    # Test 6: Batch processing
    addresses = [
        "123 Main Street, Kingston 10",
        "P.O. Box 456, Spanish Town",
        "Invalid format"
    ]
    
    parsed_addresses = service.standardize_addresses(addresses)
    assert len(parsed_addresses) == 3
    
    # Debug: check what we got
    for i, p in enumerate(parsed_addresses):
        print(f"    Address {i+1}: {type(p)} - {p}")
    
    # Check that all are ParsedAddress instances (using string comparison due to import path issues)
    assert all(type(p).__name__ == 'ParsedAddress' for p in parsed_addresses)
    
    print("✅ Test 6 passed: Batch processing")
    
    # Test 7: Geocoding candidates (fallback method)
    candidates = service.standardize_address_for_geocoding(parsed)
    assert isinstance(candidates, list)
    assert len(candidates) > 0
    
    print("✅ Test 7 passed: Geocoding candidates")
    
    print("\n🎉 All unit tests passed!")


def test_edge_cases():
    """Test edge cases and error handling."""
    service = AddressParsingService()
    
    # Test empty address
    try:
        service.parse_address("")
        assert False, "Should raise ValueError for empty address"
    except ValueError:
        print("✅ Empty address handling works")
    
    # Test minimal address
    parsed = service.parse_address("Kingston")
    assert parsed.city == "KINGSTON"
    assert parsed.country == "JAMAICA"
    
    print("✅ Minimal address handling works")
    
    # Test address with no recognizable components
    parsed = service.parse_address("Some random text")
    assert parsed.city == "UNKNOWN"  # Fallback city
    assert parsed.country == "JAMAICA"
    
    print("✅ Unrecognizable address handling works")


if __name__ == "__main__":
    print("Running Address Parsing Unit Tests")
    print("=" * 50)
    
    test_address_parsing_service()
    print()
    test_edge_cases()
    
    print("\n✅ All tests completed successfully!")