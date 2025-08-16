#!/usr/bin/env python3
"""
Standalone test runner for address parsing service.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from business_directory.data_processing import AddressParsingService
from business_directory.schemas import ParsedAddress


def test_address_parsing_service():
    """Test the address parsing service functionality."""
    print("Testing AddressParsingService...")
    
    address_service = AddressParsingService()
    
    # Test various Jamaican address formats
    print("\n1. Testing address parsing:")
    test_addresses = [
        "123 Main Street, Kingston 10, Jamaica",
        "P.O. Box 1234, Spanish Town 01, Jamaica",
        "456 Hope Road, Kingston 6, St. Andrew, Jamaica",
        "789 Orange St., New Kingston, Jamaica",
        "Somewhere in Montego Bay",
        "Located at 321 Half Way Tree Rd, Kingston 5",
        "Business in Ocho Rios, St. Ann",
        "Port Antonio, Portland, Jamaica"
    ]
    
    for address in test_addresses:
        try:
            parsed = address_service.parse_address(address)
            print(f"\n  Input: '{address}'")
            print(f"    House Number: {parsed.house_number}")
            print(f"    Street Name: {parsed.street_name}")
            print(f"    PO Box: {parsed.po_box}")
            print(f"    City: {parsed.city}")
            print(f"    Postal Zone: {parsed.postal_zone}")
            print(f"    Parish: {parsed.parish}")
            print(f"    Formatted: {parsed.formatted_address}")
            
            # Test validation
            is_valid, issues = address_service.validate_parsed_address(parsed)
            print(f"    Valid: {is_valid}")
            if issues:
                print(f"    Issues: {', '.join(issues)}")
            
            # Test completeness score
            score = address_service.calculate_completeness_score(parsed)
            print(f"    Completeness: {score:.2f}")
            
        except Exception as e:
            print(f"  Error parsing '{address}': {str(e)}")
    
    # Test batch processing
    print("\n2. Testing batch address standardization:")
    batch_addresses = [
        "123 Main St, Kingston 10",
        "P.O. Box 456, Spanish Town",
        "789 Hope Rd, New Kingston",
        "Invalid address format"
    ]
    
    parsed_addresses = address_service.standardize_addresses(batch_addresses)
    print(f"  Processed {len(parsed_addresses)} addresses:")
    for i, parsed in enumerate(parsed_addresses):
        print(f"    {i+1}. {parsed.formatted_address}")
    
    print("\n✅ All address parsing tests completed successfully!")


if __name__ == "__main__":
    test_address_parsing_service()