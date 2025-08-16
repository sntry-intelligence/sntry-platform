#!/usr/bin/env python3
"""
Comprehensive test script for deduplication engine functionality.
This script demonstrates all aspects of the deduplication system including
exact matching, fuzzy matching, confidence scoring, and manual review queue.
"""

import sys
import os
from datetime import datetime, timedelta
from typing import List

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import the deduplication components
from app.business_directory.data_processing import (
    DeduplicationEngine,
    DuplicateType,
    ConfidenceLevel,
    DuplicateMatch,
    MergeDecision
)
from app.business_directory.schemas import BusinessData


def create_comprehensive_test_data() -> List[BusinessData]:
    """Create comprehensive test data with various duplicate scenarios"""
    now = datetime.now()
    
    businesses = [
        # Scenario 1: Exact duplicates (same name and address)
        BusinessData(
            name="Kingston Pharmacy",
            raw_address="45 King Street, Kingston, Jamaica",
            phone_number="(876) 922-1234",
            email="info@kingstonpharmacy.com",
            website="https://www.kingstonpharmacy.com",
            source_url="https://findyello.com/kingston-pharmacy",
            last_scraped_at=now,
            category="Pharmacy",
            rating=4.2
        ),
        BusinessData(
            name="Kingston Pharmacy",
            raw_address="45 King Street, Kingston, Jamaica",
            phone_number="876-922-1234",  # Different format
            source_url="https://workandjam.com/kingston-pharmacy",
            last_scraped_at=now - timedelta(days=1),
            category="Pharmacy",
            description="Full service pharmacy with prescription services"
        ),
        
        # Scenario 2: High confidence fuzzy match (business name variations)
        BusinessData(
            name="Blue Mountain Coffee Company",
            raw_address="123 Hope Road, Kingston 6, Jamaica",
            phone_number="(876) 927-5555",
            email="orders@bluemountain.com",
            source_url="https://findyello.com/blue-mountain-coffee",
            last_scraped_at=now,
            category="Coffee Shop",
            rating=4.8
        ),
        BusinessData(
            name="Blue Mountain Coffee Co.",
            raw_address="123 Hope Road, Kingston 6, Jamaica",
            phone_number="876-927-5555",
            website="https://www.bluemountaincoffee.com",
            source_url="https://workandjam.com/blue-mountain-coffee",
            last_scraped_at=now,
            category="Coffee Shop",
            rating=4.9
        ),
        
        # Scenario 3: Medium confidence fuzzy match (address variations)
        BusinessData(
            name="Tropical Auto Repair",
            raw_address="789 Spanish Town Road, Kingston, Jamaica",
            phone_number="(876) 923-7777",
            source_url="https://findyello.com/tropical-auto",
            last_scraped_at=now,
            category="Auto Repair"
        ),
        BusinessData(
            name="Tropical Auto Repair Shop",
            raw_address="789 Spanish Town Rd, Kingston, Jamaica",
            phone_number="876-923-7777",
            email="service@tropicalauto.com",
            source_url="https://workandjam.com/tropical-auto",
            last_scraped_at=now,
            category="Auto Repair"
        ),
        
        # Scenario 4: Low confidence fuzzy match (similar but different businesses)
        BusinessData(
            name="Island Grill Restaurant",
            raw_address="456 Constant Spring Road, Kingston, Jamaica",
            phone_number="(876) 926-3333",
            source_url="https://findyello.com/island-grill",
            last_scraped_at=now,
            category="Restaurant"
        ),
        BusinessData(
            name="Island Grill & Bar",
            raw_address="458 Constant Spring Road, Kingston, Jamaica",  # Different address number
            phone_number="(876) 926-4444",  # Different phone
            source_url="https://workandjam.com/island-grill-bar",
            last_scraped_at=now,
            category="Restaurant"
        ),
        
        # Scenario 5: Unique businesses (no duplicates)
        BusinessData(
            name="Sunshine Bakery",
            raw_address="321 Orange Street, Kingston, Jamaica",
            phone_number="(876) 948-1111",
            source_url="https://findyello.com/sunshine-bakery",
            last_scraped_at=now,
            category="Bakery"
        ),
        BusinessData(
            name="Tech Solutions Jamaica",
            raw_address="654 New Kingston Plaza, Kingston 5, Jamaica",
            phone_number="(876) 929-8888",
            email="info@techsolutions.jm",
            website="https://www.techsolutions.jm",
            source_url="https://findyello.com/tech-solutions",
            last_scraped_at=now,
            category="Technology"
        ),
        
        # Scenario 6: Complex fuzzy match with multiple variations
        BusinessData(
            name="Dr. Smith Medical Centre",
            raw_address="100 Half Way Tree Road, Kingston 10, Jamaica",
            phone_number="(876) 926-5000",
            source_url="https://findyello.com/dr-smith-medical",
            last_scraped_at=now,
            category="Medical"
        ),
        BusinessData(
            name="Dr. Smith Medical Center",  # Centre vs Center
            raw_address="100 Half Way Tree Rd, Kingston 10, Jamaica",  # Rd vs Road
            phone_number="876-926-5000",
            email="appointments@drsmith.com",
            source_url="https://workandjam.com/dr-smith-medical",
            last_scraped_at=now,
            category="Medical"
        )
    ]
    
    return businesses


def analyze_duplicate_matches(matches: List[DuplicateMatch]):
    """Analyze and display detailed information about duplicate matches"""
    print(f"\n📊 DUPLICATE ANALYSIS")
    print("=" * 50)
    
    if not matches:
        print("No duplicates found.")
        return
    
    # Group by type and confidence
    exact_matches = [m for m in matches if m.duplicate_type == DuplicateType.EXACT]
    fuzzy_matches = [m for m in matches if m.duplicate_type == DuplicateType.FUZZY]
    
    high_confidence = [m for m in matches if m.confidence_level == ConfidenceLevel.HIGH]
    medium_confidence = [m for m in matches if m.confidence_level == ConfidenceLevel.MEDIUM]
    low_confidence = [m for m in matches if m.confidence_level == ConfidenceLevel.LOW]
    
    print(f"Total matches found: {len(matches)}")
    print(f"  - Exact matches: {len(exact_matches)}")
    print(f"  - Fuzzy matches: {len(fuzzy_matches)}")
    print()
    print(f"Confidence distribution:")
    print(f"  - High confidence (≥90%): {len(high_confidence)}")
    print(f"  - Medium confidence (70-89%): {len(medium_confidence)}")
    print(f"  - Low confidence (50-69%): {len(low_confidence)}")
    print()
    
    # Display detailed match information
    for i, match in enumerate(matches, 1):
        print(f"Match #{i}: {match.duplicate_type.value.upper()} - {match.confidence_level.value.upper()}")
        print(f"  Business 1: {match.business1.name}")
        print(f"  Business 2: {match.business2.name}")
        print(f"  Confidence: {match.confidence_score:.1f}%")
        print(f"  Matching fields: {', '.join(match.matching_fields)}")
        print(f"  Requires manual review: {'Yes' if match.requires_manual_review else 'No'}")
        
        # Show similarity breakdown
        if match.similarity_scores:
            print(f"  Similarity breakdown:")
            for field, score in match.similarity_scores.items():
                print(f"    - {field}: {score:.1f}%")
        print()


def analyze_merge_decisions(decisions: List[MergeDecision]):
    """Analyze and display merge decision information"""
    print(f"\n🔄 MERGE DECISIONS")
    print("=" * 50)
    
    if not decisions:
        print("No merge decisions created.")
        return
    
    automatic_merges = [d for d in decisions if d.merge_strategy == "automatic"]
    review_required = [d for d in decisions if d.merge_strategy == "review_required"]
    
    print(f"Total merge decisions: {len(decisions)}")
    print(f"  - Automatic merges: {len(automatic_merges)}")
    print(f"  - Review required: {len(review_required)}")
    print()
    
    for i, decision in enumerate(decisions, 1):
        print(f"Decision #{i}: {decision.merge_strategy.upper()}")
        print(f"  Primary: {decision.primary_business.name}")
        print(f"  Secondary: {decision.secondary_business.name}")
        print(f"  Confidence: {decision.confidence_score:.1f}%")
        
        # Show what data would be merged
        merged_fields = []
        primary_dict = decision.primary_business.model_dump()
        secondary_dict = decision.secondary_business.model_dump()
        
        for field, value in decision.merged_data.items():
            primary_val = primary_dict.get(field)
            secondary_val = secondary_dict.get(field)
            
            if primary_val != value and secondary_val == value:
                merged_fields.append(f"{field} (from secondary)")
            elif primary_val != secondary_val and value:
                merged_fields.append(f"{field} (merged)")
        
        if merged_fields:
            print(f"  Data enhancements: {', '.join(merged_fields)}")
        print()


def demonstrate_manual_review_queue(engine: DeduplicationEngine, matches: List[DuplicateMatch]):
    """Demonstrate the manual review queue functionality"""
    print(f"\n👥 MANUAL REVIEW QUEUE")
    print("=" * 50)
    
    manual_review = engine.get_manual_review_queue(matches)
    
    if not manual_review:
        print("No matches require manual review.")
        return
    
    print(f"Matches requiring manual review: {len(manual_review)}")
    print("(Sorted by confidence score, highest first)")
    print()
    
    for i, match in enumerate(manual_review, 1):
        print(f"Review Item #{i}:")
        print(f"  Business 1: {match.business1.name}")
        print(f"    Address: {match.business1.raw_address}")
        print(f"    Phone: {match.business1.phone_number or 'N/A'}")
        print(f"    Email: {match.business1.email or 'N/A'}")
        print(f"    Source: {match.business1.source_url}")
        print()
        print(f"  Business 2: {match.business2.name}")
        print(f"    Address: {match.business2.raw_address}")
        print(f"    Phone: {match.business2.phone_number or 'N/A'}")
        print(f"    Email: {match.business2.email or 'N/A'}")
        print(f"    Source: {match.business2.source_url}")
        print()
        print(f"  Match Details:")
        print(f"    Confidence: {match.confidence_score:.1f}% ({match.confidence_level.value})")
        print(f"    Type: {match.duplicate_type.value}")
        print(f"    Matching fields: {', '.join(match.matching_fields)}")
        print()
        print(f"  Recommendation: {'MERGE' if match.confidence_score > 75 else 'REVIEW CAREFULLY'}")
        print("-" * 50)


def main():
    """Run comprehensive deduplication demonstration"""
    print("🔍 COMPREHENSIVE DEDUPLICATION ENGINE DEMONSTRATION")
    print("=" * 60)
    
    # Create test data
    businesses = create_comprehensive_test_data()
    print(f"\nCreated {len(businesses)} test businesses with various duplicate scenarios")
    
    # Initialize deduplication engine
    engine = DeduplicationEngine(fuzzy_threshold=75.0)  # Lower threshold to catch more matches
    print(f"Initialized deduplication engine with {engine.fuzzy_threshold}% fuzzy threshold")
    
    # Find duplicates
    print(f"\n🔍 FINDING DUPLICATES...")
    matches = engine.find_duplicates(businesses)
    
    # Analyze matches
    analyze_duplicate_matches(matches)
    
    # Create merge decisions
    print(f"\n🔄 CREATING MERGE DECISIONS...")
    merge_decisions = engine.create_merge_decisions(matches)
    analyze_merge_decisions(merge_decisions)
    
    # Demonstrate manual review queue
    demonstrate_manual_review_queue(engine, matches)
    
    # Run complete deduplication workflow
    print(f"\n⚙️ COMPLETE DEDUPLICATION WORKFLOW")
    print("=" * 50)
    
    original_count = len(businesses)
    deduplicated, manual_review = engine.deduplicate_businesses(businesses)
    
    print(f"Original businesses: {original_count}")
    print(f"After deduplication: {len(deduplicated)}")
    print(f"Businesses removed: {original_count - len(deduplicated)}")
    print(f"Manual review items: {len(manual_review)}")
    
    # Calculate deduplication statistics
    exact_duplicates_removed = len([m for m in matches if m.duplicate_type == DuplicateType.EXACT and m.confidence_level == ConfidenceLevel.HIGH])
    fuzzy_duplicates_removed = len([d for d in merge_decisions if d.merge_strategy == "automatic" and d.confidence_score < 100])
    
    print(f"\nDeduplication Statistics:")
    print(f"  - Exact duplicates automatically merged: {exact_duplicates_removed}")
    print(f"  - High-confidence fuzzy duplicates merged: {fuzzy_duplicates_removed}")
    print(f"  - Items flagged for manual review: {len(manual_review)}")
    
    # Show final deduplicated list
    print(f"\n📋 FINAL DEDUPLICATED BUSINESS LIST")
    print("=" * 50)
    
    for i, business in enumerate(deduplicated, 1):
        print(f"{i:2d}. {business.name}")
        print(f"     {business.raw_address}")
        if business.phone_number:
            print(f"     📞 {business.phone_number}")
        if business.email:
            print(f"     📧 {business.email}")
        print()
    
    print("=" * 60)
    print("✅ DEDUPLICATION DEMONSTRATION COMPLETE")
    print("=" * 60)
    
    print("\n🎯 KEY FEATURES DEMONSTRATED:")
    print("✓ Exact duplicate detection using business name and address hashing")
    print("✓ Fuzzy string matching using RapidFuzz for near-duplicate detection")
    print("✓ Confidence scoring with HIGH/MEDIUM/LOW levels")
    print("✓ Business rules for merging duplicate records")
    print("✓ Manual review queue for uncertain matches")
    print("✓ Complete deduplication workflow with automatic and manual processes")
    print("✓ Data preservation and enhancement during merging")
    print("✓ Comprehensive similarity analysis across multiple fields")


if __name__ == "__main__":
    main()