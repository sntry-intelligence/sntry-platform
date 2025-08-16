#!/usr/bin/env python3
"""
Test fuzzy matching functionality of the deduplication engine.
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


def test_fuzzy_duplicate_detection():
    """Test fuzzy duplicate detection with RapidFuzz"""
    print("Testing fuzzy duplicate detection...")
    
    engine = DeduplicationEngine(fuzzy_threshold=75.0)
    
    # Create similar but not identical businesses
    businesses = [
        BusinessData(
            name="ABC Restaurant",
            raw_address="123 Main Street, Kingston 10, Jamaica",
            phone_number="(876) 123-4567",
            email="info@abcrestaurant.com",
            source_url="https://findyello.com/abc-restaurant",
            last_scraped_at=datetime.now()
        ),
        BusinessData(
            name="ABC Restaurant Ltd",
            raw_address="123 Main St, Kingston 10, Jamaica",
            phone_number="876-123-4567",
            email="info@abcrestaurant.com",
            source_url="https://workandjam.com/abc-restaurant",
            last_scraped_at=datetime.now()
        ),
        BusinessData(
            name="XYZ Auto Parts",
            raw_address="456 Spanish Town Road, Kingston, Jamaica",
            phone_number="(876) 987-6543",
            source_url="https://findyello.com/xyz-auto",
            last_scraped_at=datetime.now()
        ),
        BusinessData(
            name="XYZ Auto Parts Inc",
            raw_address="456 Spanish Town Rd, Kingston, Jamaica",
            phone_number="876-987-6543",
            email="sales@xyzauto.com",
            source_url="https://workandjam.com/xyz-auto",
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
    
    matches = engine.find_duplicates(businesses)
    
    print(f"Found {len(matches)} duplicate matches")
    
    # Should find fuzzy matches for ABC Restaurant and XYZ Auto Parts
    assert len(matches) >= 2, f"Expected at least 2 matches, got {len(matches)}"
    
    for match in matches:
        print(f"Match: {match.business1.name} <-> {match.business2.name}")
        print(f"  Type: {match.duplicate_type.value}")
        print(f"  Confidence: {match.confidence_score:.2f}")
        print(f"  Level: {match.confidence_level.value}")
        print(f"  Matching fields: {match.matching_fields}")
        print(f"  Similarity scores: {match.similarity_scores}")
        print()
        
        assert match.duplicate_type == DuplicateType.FUZZY
        assert match.confidence_score >= engine.fuzzy_threshold
    
    print("✓ Fuzzy duplicate detection works correctly")


def test_field_similarity_with_rapidfuzz():
    """Test field similarity calculation with RapidFuzz"""
    print("Testing field similarity with RapidFuzz...")
    
    engine = DeduplicationEngine()
    
    # Test name similarity
    name_sim = engine._calculate_field_similarity(
        "ABC Restaurant Ltd", "ABC Restaurant Limited", "name"
    )
    print(f"Name similarity: {name_sim:.2f}")
    assert name_sim > 80.0, f"Expected high similarity, got {name_sim}"
    
    # Test address similarity
    addr_sim = engine._calculate_field_similarity(
        "123 Main Street, Kingston", "123 Main St, Kingston", "address"
    )
    print(f"Address similarity: {addr_sim:.2f}")
    assert addr_sim > 80.0, f"Expected high similarity, got {addr_sim}"
    
    # Test phone similarity
    phone_sim = engine._calculate_field_similarity(
        "(876) 123-4567", "876-123-4567", "phone"
    )
    print(f"Phone similarity: {phone_sim:.2f}")
    assert phone_sim == 100.0, f"Expected perfect match, got {phone_sim}"
    
    # Test email similarity
    email_sim = engine._calculate_field_similarity(
        "test@example.com", "test@example.com", "email"
    )
    print(f"Email similarity: {email_sim:.2f}")
    assert email_sim == 100.0, f"Expected perfect match, got {email_sim}"
    
    # Test website similarity
    website_sim = engine._calculate_field_similarity(
        "https://www.example.com", "http://example.com", "website"
    )
    print(f"Website similarity: {website_sim:.2f}")
    assert website_sim > 90.0, f"Expected high similarity, got {website_sim}"
    
    print("✓ Field similarity calculation works correctly")


def test_merge_decisions_with_fuzzy_matches():
    """Test merge decision creation with fuzzy matches"""
    print("Testing merge decisions with fuzzy matches...")
    
    engine = DeduplicationEngine(fuzzy_threshold=75.0)
    
    businesses = [
        BusinessData(
            name="Complete Restaurant",
            raw_address="123 Main Street, Kingston 10, Jamaica",
            phone_number="(876) 123-4567",
            email="info@complete.com",
            website="https://www.complete.com",
            description="Full service restaurant",
            rating=4.5,
            source_url="https://findyello.com/complete",
            last_scraped_at=datetime.now()
        ),
        BusinessData(
            name="Complete Restaurant Ltd",
            raw_address="123 Main St, Kingston 10, Jamaica",
            phone_number="876-123-4567",
            source_url="https://workandjam.com/complete",
            last_scraped_at=datetime.now()
        )
    ]
    
    matches = engine.find_duplicates(businesses)
    merge_decisions = engine.create_merge_decisions(matches)
    
    print(f"Created {len(merge_decisions)} merge decisions")
    
    assert len(merge_decisions) > 0, "Should create merge decisions"
    
    for decision in merge_decisions:
        print(f"Merge decision:")
        print(f"  Primary: {decision.primary_business.name}")
        print(f"  Secondary: {decision.secondary_business.name}")
        print(f"  Strategy: {decision.merge_strategy}")
        print(f"  Confidence: {decision.confidence_score:.2f}")
        
        # Primary should be the more complete business
        assert decision.primary_business.name == "Complete Restaurant"
        assert decision.secondary_business.name == "Complete Restaurant Ltd"
        
        # Merged data should combine the best of both
        merged = decision.merged_data
        assert merged['name'] == "Complete Restaurant"  # Primary name
        assert merged['phone_number'] == "(876) 123-4567"  # Primary phone
        assert merged['email'] == "info@complete.com"  # Primary email
        assert merged['website'] == "https://www.complete.com"  # Primary website
    
    print("✓ Merge decisions work correctly")


def test_complete_workflow_with_fuzzy():
    """Test complete deduplication workflow with fuzzy matching"""
    print("Testing complete workflow with fuzzy matching...")
    
    engine = DeduplicationEngine(fuzzy_threshold=70.0)
    
    # Create businesses with various types of duplicates
    businesses = [
        # Exact duplicates
        BusinessData(
            name="Exact Match Business",
            raw_address="100 Exact Street, Kingston, Jamaica",
            source_url="https://site1.com/exact",
            last_scraped_at=datetime.now()
        ),
        BusinessData(
            name="Exact Match Business",
            raw_address="100 Exact Street, Kingston, Jamaica",
            source_url="https://site2.com/exact",
            last_scraped_at=datetime.now(),
            phone_number="(876) 111-1111"
        ),
        
        # Fuzzy duplicates
        BusinessData(
            name="Fuzzy Restaurant",
            raw_address="200 Fuzzy Avenue, Kingston 5, Jamaica",
            phone_number="(876) 222-2222",
            source_url="https://site1.com/fuzzy",
            last_scraped_at=datetime.now()
        ),
        BusinessData(
            name="Fuzzy Restaurant Ltd",
            raw_address="200 Fuzzy Ave, Kingston 5, Jamaica",
            phone_number="876-222-2222",
            email="info@fuzzy.com",
            source_url="https://site2.com/fuzzy",
            last_scraped_at=datetime.now()
        ),
        
        # Unique business
        BusinessData(
            name="Unique Business",
            raw_address="300 Unique Road, Spanish Town, Jamaica",
            phone_number="(876) 333-3333",
            source_url="https://site1.com/unique",
            last_scraped_at=datetime.now()
        )
    ]
    
    original_count = len(businesses)
    print(f"Starting with {original_count} businesses")
    
    deduplicated, manual_review = engine.deduplicate_businesses(businesses)
    
    print(f"After deduplication: {len(deduplicated)} businesses")
    print(f"Manual review queue: {len(manual_review)} matches")
    
    # Should have fewer businesses after deduplication
    assert len(deduplicated) < original_count, f"Expected fewer than {original_count}, got {len(deduplicated)}"
    
    # Should have fewer businesses after deduplication
    # Note: Some matches may require manual review and won't be automatically merged
    expected_max = original_count - 1  # At least one merge should happen
    assert len(deduplicated) <= expected_max, f"Expected <= {expected_max} businesses, got {len(deduplicated)}"
    
    # Check that merged businesses have combined data
    business_names = [b.name for b in deduplicated]
    assert "Exact Match Business" in business_names
    assert "Fuzzy Restaurant" in business_names or "Fuzzy Restaurant Ltd" in business_names
    assert "Unique Business" in business_names
    
    print("✓ Complete workflow with fuzzy matching works correctly")


def main():
    """Run all fuzzy matching tests"""
    print("Running fuzzy matching tests...\n")
    
    try:
        test_field_similarity_with_rapidfuzz()
        test_fuzzy_duplicate_detection()
        test_merge_decisions_with_fuzzy_matches()
        test_complete_workflow_with_fuzzy()
        
        print("\n🎉 All fuzzy matching tests passed!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())