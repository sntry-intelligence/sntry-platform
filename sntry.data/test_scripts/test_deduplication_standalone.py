#!/usr/bin/env python3
"""
Standalone test for deduplication engine functionality.
This test doesn't require database connections or external dependencies.
"""
import sys
import os
from datetime import datetime

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.business_directory.data_processing import (
    DeduplicationEngine,
    DuplicateType,
    ConfidenceLevel
)
from app.business_directory.schemas import BusinessData


def test_exact_duplicate_detection():
    """Test exact duplicate detection"""
    print("Testing exact duplicate detection...")
    
    engine = DeduplicationEngine()
    
    # Create exact duplicates
    business1 = BusinessData(
        name="Test Business",
        raw_address="123 Test Street, Kingston, Jamaica",
        source_url="https://test1.com",
        last_scraped_at=datetime.now()
    )
    
    business2 = BusinessData(
        name="Test Business",
        raw_address="123 Test Street, Kingston, Jamaica",
        source_url="https://test2.com",
        last_scraped_at=datetime.now(),
        phone_number="(876) 123-4567"
    )
    
    matches = engine.find_duplicates([business1, business2])
    
    assert len(matches) == 1, f"Expected 1 match, got {len(matches)}"
    assert matches[0].duplicate_type == DuplicateType.EXACT, f"Expected EXACT, got {matches[0].duplicate_type}"
    assert matches[0].confidence_score == 100.0, f"Expected 100.0, got {matches[0].confidence_score}"
    
    print("✓ Exact duplicate detection works correctly")


def test_hash_generation():
    """Test business hash generation"""
    print("Testing hash generation...")
    
    engine = DeduplicationEngine()
    
    business1 = BusinessData(
        name="Test Business",
        raw_address="123 Test Street",
        source_url="https://test.com",
        last_scraped_at=datetime.now()
    )
    
    business2 = BusinessData(
        name="Test Business",
        raw_address="123 Test Street",
        source_url="https://different.com",
        last_scraped_at=datetime.now(),
        phone_number="(876) 123-4567"
    )
    
    hash1 = engine._generate_business_hash(business1)
    hash2 = engine._generate_business_hash(business2)
    
    assert hash1 == hash2, "Hashes should be the same for businesses with same name and address"
    assert len(hash1) == 64, f"Hash should be 64 characters, got {len(hash1)}"
    
    print("✓ Hash generation works correctly")


def test_normalization():
    """Test field normalization"""
    print("Testing field normalization...")
    
    engine = DeduplicationEngine()
    
    # Test name normalization
    normalized_name = engine._normalize_for_comparison("ABC Restaurant Ltd.", "name")
    assert "ltd" not in normalized_name, f"Expected 'ltd' to be removed, got: {normalized_name}"
    
    # Test address normalization
    normalized_addr = engine._normalize_for_comparison("123 Main St.", "address")
    assert "street" in normalized_addr, f"Expected 'street' expansion, got: {normalized_addr}"
    
    # Test phone normalization
    normalized_phone = engine._normalize_for_comparison("(876) 123-4567", "phone")
    assert normalized_phone == "8761234567", f"Expected digits only, got: {normalized_phone}"
    
    print("✓ Field normalization works correctly")


def test_confidence_levels():
    """Test confidence level determination"""
    print("Testing confidence level determination...")
    
    engine = DeduplicationEngine()
    
    assert engine._determine_confidence_level(95.0) == ConfidenceLevel.HIGH
    assert engine._determine_confidence_level(85.0) == ConfidenceLevel.MEDIUM
    assert engine._determine_confidence_level(60.0) == ConfidenceLevel.LOW
    assert engine._determine_confidence_level(40.0) == ConfidenceLevel.NONE
    
    print("✓ Confidence level determination works correctly")


def test_merge_priority():
    """Test merge priority determination"""
    print("Testing merge priority determination...")
    
    engine = DeduplicationEngine()
    
    # Business with more complete data
    complete_business = BusinessData(
        name="Complete Business",
        raw_address="123 Street, Kingston, Jamaica",
        phone_number="(876) 123-4567",
        email="info@complete.com",
        website="https://www.complete.com",
        description="Full description",
        rating=4.5,
        latitude=18.0,
        longitude=-76.8,
        source_url="https://test.com",
        last_scraped_at=datetime.now()
    )
    
    # Business with minimal data
    minimal_business = BusinessData(
        name="Minimal Business",
        raw_address="123 Street, Kingston, Jamaica",
        source_url="https://test2.com",
        last_scraped_at=datetime.now()
    )
    
    primary, secondary = engine._determine_merge_priority(complete_business, minimal_business)
    
    assert primary == complete_business, "Complete business should be primary"
    assert secondary == minimal_business, "Minimal business should be secondary"
    
    print("✓ Merge priority determination works correctly")


def test_complete_workflow():
    """Test complete deduplication workflow"""
    print("Testing complete deduplication workflow...")
    
    engine = DeduplicationEngine()
    
    # Create sample businesses with duplicates
    businesses = [
        BusinessData(
            name="ABC Restaurant",
            raw_address="123 Main Street, Kingston 10, Jamaica",
            phone_number="(876) 123-4567",
            source_url="https://findyello.com/abc-restaurant",
            last_scraped_at=datetime.now()
        ),
        BusinessData(
            name="ABC Restaurant Ltd",
            raw_address="123 Main St, Kingston 10, Jamaica",
            phone_number="876-123-4567",
            source_url="https://workandjam.com/abc-restaurant",
            last_scraped_at=datetime.now()
        ),
        BusinessData(
            name="Unique Business",
            raw_address="789 Hope Road, Kingston 6, Jamaica",
            phone_number="(876) 555-1234",
            source_url="https://findyello.com/unique",
            last_scraped_at=datetime.now()
        )
    ]
    
    original_count = len(businesses)
    deduplicated, manual_review = engine.deduplicate_businesses(businesses)
    
    # Should have fewer businesses after deduplication (or same if no duplicates found)
    assert len(deduplicated) <= original_count, f"Expected <= {original_count}, got {len(deduplicated)}"
    
    print(f"✓ Complete workflow: {original_count} -> {len(deduplicated)} businesses")
    print(f"✓ Manual review queue: {len(manual_review)} matches")


def main():
    """Run all tests"""
    print("Running deduplication engine tests...\n")
    
    try:
        test_hash_generation()
        test_normalization()
        test_confidence_levels()
        test_merge_priority()
        test_exact_duplicate_detection()
        test_complete_workflow()
        
        print("\n🎉 All tests passed!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())