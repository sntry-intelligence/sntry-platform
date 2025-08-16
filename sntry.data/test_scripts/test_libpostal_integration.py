#!/usr/bin/env python3
"""
Test script to verify Libpostal integration for Jamaican address parsing.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from business_directory.data_processing import AddressParsingService, LIBPOSTAL_AVAILABLE


def test_libpostal_availability():
    """Test if Libpostal is properly installed and available."""
    print("Testing Libpostal availability...")
    print(f"Libpostal available: {LIBPOSTAL_AVAILABLE}")
    
    if LIBPOSTAL_AVAILABLE:
        try:
            from postal.parser import parse_address
            from postal.expand import expand_address
            
            # Test basic functionality
            test_address = "123 Main Street, Kingston 10, Jamaica"
            parsed = parse_address(test_address)
            expanded = expand_address(test_address)
            
            print(f"✅ Libpostal is working correctly")
            print(f"   Parsed components: {parsed}")
            print(f"   Expanded variations: {len(expanded)} variations")
            return True
        except Exception as e:
            print(f"❌ Libpostal import failed: {str(e)}")
            return False
    else:
        print("❌ Libpostal not available - using fallback method")
        return False


def test_address_parsing_with_libpostal():
    """Test address parsing service with Libpostal integration."""
    print("\nTesting AddressParsingService with Libpostal...")
    
    service = AddressParsingService()
    print(f"Service using Libpostal: {service.use_libpostal}")
    
    # Test various Jamaican address formats
    test_addresses = [
        "123 Main Street, Kingston 10, Jamaica",
        "P.O. Box 1234, Spanish Town 01, St. Catherine, Jamaica",
        "456 Hope Road, Kingston 6, St. Andrew, Jamaica",
        "789 Orange Street, New Kingston, Jamaica",
        "Unit 5, Sovereign Centre, Hope Road, Kingston 10",
        "Somewhere in Montego Bay, St. James",
        "Located at 321 Half Way Tree Road, Kingston 5",
        "Business Plaza, Ocho Rios, St. Ann, Jamaica",
        "Port Antonio, Portland, Jamaica",
        "15 Barbican Road, Kingston 6, St. Andrew"
    ]
    
    results = []
    
    for i, address in enumerate(test_addresses, 1):
        print(f"\n{i}. Testing: '{address}'")
        try:
            parsed = service.parse_address(address)
            
            print(f"   House Number: {parsed.house_number}")
            print(f"   Street Name: {parsed.street_name}")
            print(f"   PO Box: {parsed.po_box}")
            print(f"   City: {parsed.city}")
            print(f"   Postal Zone: {parsed.postal_zone}")
            print(f"   Parish: {parsed.parish}")
            print(f"   Country: {parsed.country}")
            print(f"   Formatted: {parsed.formatted_address}")
            
            # Test validation
            is_valid, issues = service.validate_parsed_address(parsed)
            print(f"   Valid: {is_valid}")
            if issues:
                print(f"   Issues: {', '.join(issues)}")
            
            # Test completeness score
            score = service.calculate_completeness_score(parsed)
            print(f"   Completeness: {score:.3f}")
            
            # Test address expansion if Libpostal is available
            if service.use_libpostal:
                variations = service.expand_address_variations(address)
                print(f"   Variations: {len(variations)} generated")
                
                # Test geocoding candidates
                candidates = service.standardize_address_for_geocoding(parsed)
                print(f"   Geocoding candidates: {len(candidates)} generated")
            
            results.append({
                'address': address,
                'parsed': parsed,
                'valid': is_valid,
                'score': score,
                'issues': issues
            })
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            results.append({
                'address': address,
                'error': str(e)
            })
    
    return results


def test_address_expansion():
    """Test address expansion functionality."""
    if not LIBPOSTAL_AVAILABLE:
        print("\nSkipping address expansion test - Libpostal not available")
        return
    
    print("\nTesting address expansion...")
    service = AddressParsingService()
    
    test_addresses = [
        "123 Main St, Kingston 10",
        "P.O. Box 456, Spanish Town",
        "Hope Rd, New Kingston",
        "Montego Bay, St. James"
    ]
    
    for address in test_addresses:
        print(f"\nExpanding: '{address}'")
        try:
            variations = service.expand_address_variations(address)
            print(f"Generated {len(variations)} variations:")
            for i, variation in enumerate(variations[:5], 1):  # Show first 5
                print(f"  {i}. {variation}")
            if len(variations) > 5:
                print(f"  ... and {len(variations) - 5} more")
        except Exception as e:
            print(f"Error: {str(e)}")


def test_geocoding_candidates():
    """Test geocoding candidate generation."""
    print("\nTesting geocoding candidate generation...")
    service = AddressParsingService()
    
    test_address = "123 Hope Road, Kingston 6, St. Andrew, Jamaica"
    
    try:
        parsed = service.parse_address(test_address)
        candidates = service.standardize_address_for_geocoding(parsed)
        
        print(f"Original: {test_address}")
        print(f"Generated {len(candidates)} geocoding candidates:")
        for i, candidate in enumerate(candidates, 1):
            print(f"  {i}. {candidate}")
            
    except Exception as e:
        print(f"Error: {str(e)}")


def run_comprehensive_test():
    """Run all tests and provide summary."""
    print("=" * 60)
    print("LIBPOSTAL INTEGRATION TEST SUITE")
    print("=" * 60)
    
    # Test 1: Libpostal availability
    libpostal_working = test_libpostal_availability()
    
    # Test 2: Address parsing
    results = test_address_parsing_with_libpostal()
    
    # Test 3: Address expansion
    test_address_expansion()
    
    # Test 4: Geocoding candidates
    test_geocoding_candidates()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    print(f"Libpostal available: {'✅' if libpostal_working else '❌'}")
    
    successful_parses = len([r for r in results if 'error' not in r])
    total_tests = len(results)
    print(f"Address parsing: {successful_parses}/{total_tests} successful")
    
    valid_addresses = len([r for r in results if 'error' not in r and r.get('valid', False)])
    print(f"Valid addresses: {valid_addresses}/{successful_parses}")
    
    if successful_parses > 0:
        avg_score = sum(r.get('score', 0) for r in results if 'error' not in r) / successful_parses
        print(f"Average completeness score: {avg_score:.3f}")
    
    print("\n✅ All tests completed!")


if __name__ == "__main__":
    run_comprehensive_test()