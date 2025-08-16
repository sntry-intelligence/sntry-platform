#!/usr/bin/env python3
"""
Demonstration of the deduplication engine functionality.
Shows how to use the engine to find and merge duplicate business records.
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


def create_sample_data():
    """Create sample business data with various types of duplicates"""
    now = datetime.now()
    
    return [
        # Exact duplicates
        BusinessData(
            name="Kingston Pharmacy",
            raw_address="15 King Street, Kingston, Jamaica",
            phone_number="(876) 922-1234",
            email="info@kingstonpharmacy.com",
            source_url="https://findyello.com/kingston-pharmacy",
            last_scraped_at=now,
            category="Pharmacy"
        ),
        BusinessData(
            name="Kingston Pharmacy",
            raw_address="15 King Street, Kingston, Jamaica",
            phone_number="876-922-1234",
            website="https://www.kingstonpharmacy.com",
            source_url="https://workandjam.com/kingston-pharmacy",
            last_scraped_at=now,
            category="Pharmacy"
        ),
        
        # Fuzzy duplicates - similar names and addresses
        BusinessData(
            name="Bob Marley Museum",
            raw_address="56 Hope Road, Kingston 6, Jamaica",
            phone_number="(876) 927-9152",
            email="info@bobmarleymuseum.com",
            website="https://www.bobmarleymuseum.com",
            description="Official Bob Marley Museum",
            rating=4.8,
            source_url="https://findyello.com/bob-marley-museum",
            last_scraped_at=now,
            category="Museum"
        ),
        BusinessData(
            name="Bob Marley Museum Ltd",
            raw_address="56 Hope Rd, Kingston 6, Jamaica",
            phone_number="876-927-9152",
            description="Home of reggae legend Bob Marley",
            source_url="https://workandjam.com/bob-marley-museum",
            last_scraped_at=now,
            category="Museum"
        ),
        
        # Near duplicates - business name variations
        BusinessData(
            name="Devon House Ice Cream",
            raw_address="26 Hope Road, Kingston 10, Jamaica",
            phone_number="(876) 929-7029",
            email="orders@devonhouse.com",
            source_url="https://findyello.com/devon-house",
            last_scraped_at=now,
            category="Ice Cream Shop"
        ),
        BusinessData(
            name="Devon House I-Scream",
            raw_address="26 Hope Road, Kingston 10, Jamaica",
            phone_number="876-929-7029",
            website="https://www.devonhouseicream.com",
            description="Famous Jamaican ice cream",
            source_url="https://workandjam.com/devon-house-ice-cream",
            last_scraped_at=now,
            category="Ice Cream Shop"
        ),
        
        # Address variations
        BusinessData(
            name="Blue Mountain Coffee Works",
            raw_address="21 Barbican Road, Kingston 6, Jamaica",
            phone_number="(876) 977-8888",
            email="info@bluemountaincoffee.com",
            source_url="https://findyello.com/blue-mountain-coffee",
            last_scraped_at=now,
            category="Coffee Shop"
        ),
        BusinessData(
            name="Blue Mountain Coffee Works Ltd",
            raw_address="21 Barbican Rd, Kingston 6, Jamaica",
            phone_number="876-977-8888",
            website="https://www.bluemountaincoffee.com",
            description="Premium Blue Mountain coffee",
            rating=4.6,
            source_url="https://workandjam.com/blue-mountain-coffee",
            last_scraped_at=now,
            category="Coffee Shop"
        ),
        
        # Unique businesses (no duplicates)
        BusinessData(
            name="Scotiabank Half Way Tree",
            raw_address="2 Half Way Tree Road, Kingston 10, Jamaica",
            phone_number="(876) 922-1000",
            website="https://www.scotiabank.com",
            source_url="https://findyello.com/scotiabank-hwt",
            last_scraped_at=now,
            category="Bank"
        ),
        BusinessData(
            name="University of the West Indies",
            raw_address="Mona Campus, Kingston 7, Jamaica",
            phone_number="(876) 927-1660",
            website="https://www.uwi.edu",
            description="Premier Caribbean university",
            source_url="https://findyello.com/uwi-mona",
            last_scraped_at=now,
            category="University"
        )
    ]


def demonstrate_duplicate_detection():
    """Demonstrate duplicate detection capabilities"""
    print("🔍 DUPLICATE DETECTION DEMONSTRATION")
    print("=" * 50)
    
    # Create deduplication engine
    engine = DeduplicationEngine(fuzzy_threshold=75.0)
    
    # Get sample data
    businesses = create_sample_data()
    print(f"📊 Starting with {len(businesses)} business records\n")
    
    # Find duplicates
    print("🔎 Finding duplicate matches...")
    matches = engine.find_duplicates(businesses)
    
    print(f"Found {len(matches)} potential duplicate matches:\n")
    
    for i, match in enumerate(matches, 1):
        print(f"Match #{i}:")
        print(f"  Business 1: {match.business1.name}")
        print(f"  Business 2: {match.business2.name}")
        print(f"  Type: {match.duplicate_type.value.upper()}")
        print(f"  Confidence: {match.confidence_score:.1f}%")
        print(f"  Level: {match.confidence_level.value.upper()}")
        print(f"  Matching Fields: {', '.join(match.matching_fields)}")
        
        if match.similarity_scores:
            print("  Similarity Scores:")
            for field, score in match.similarity_scores.items():
                if score > 0:
                    print(f"    {field}: {score:.1f}%")
        
        print(f"  Manual Review Required: {'Yes' if match.requires_manual_review else 'No'}")
        print()
    
    return businesses, matches


def demonstrate_merge_decisions():
    """Demonstrate merge decision creation"""
    print("\n📋 MERGE DECISION DEMONSTRATION")
    print("=" * 50)
    
    businesses, matches = demonstrate_duplicate_detection()
    engine = DeduplicationEngine(fuzzy_threshold=75.0)
    
    # Create merge decisions
    print("🤖 Creating merge decisions...")
    merge_decisions = engine.create_merge_decisions(matches)
    
    print(f"Created {len(merge_decisions)} merge decisions:\n")
    
    for i, decision in enumerate(merge_decisions, 1):
        print(f"Merge Decision #{i}:")
        print(f"  Primary Business: {decision.primary_business.name}")
        print(f"  Secondary Business: {decision.secondary_business.name}")
        print(f"  Strategy: {decision.merge_strategy.upper()}")
        print(f"  Confidence: {decision.confidence_score:.1f}%")
        
        print("  Merged Data Preview:")
        merged = decision.merged_data
        print(f"    Name: {merged.get('name', 'N/A')}")
        print(f"    Address: {merged.get('raw_address', 'N/A')}")
        print(f"    Phone: {merged.get('phone_number', 'N/A')}")
        print(f"    Email: {merged.get('email', 'N/A')}")
        print(f"    Website: {merged.get('website', 'N/A')}")
        print()
    
    return businesses, matches, merge_decisions


def demonstrate_manual_review_queue():
    """Demonstrate manual review queue functionality"""
    print("\n👥 MANUAL REVIEW QUEUE DEMONSTRATION")
    print("=" * 50)
    
    businesses, matches, merge_decisions = demonstrate_merge_decisions()
    engine = DeduplicationEngine(fuzzy_threshold=75.0)
    
    # Get manual review queue
    manual_review = engine.get_manual_review_queue(matches)
    
    print(f"📝 {len(manual_review)} matches require manual review:\n")
    
    for i, match in enumerate(manual_review, 1):
        print(f"Manual Review #{i}:")
        print(f"  Business 1: {match.business1.name}")
        print(f"    Address: {match.business1.raw_address}")
        print(f"    Phone: {match.business1.phone_number or 'N/A'}")
        print(f"    Email: {match.business1.email or 'N/A'}")
        
        print(f"  Business 2: {match.business2.name}")
        print(f"    Address: {match.business2.raw_address}")
        print(f"    Phone: {match.business2.phone_number or 'N/A'}")
        print(f"    Email: {match.business2.email or 'N/A'}")
        
        print(f"  Confidence: {match.confidence_score:.1f}%")
        print(f"  Reason for Review: {match.confidence_level.value.upper()} confidence")
        print()
    
    return businesses, matches, merge_decisions, manual_review


def demonstrate_complete_workflow():
    """Demonstrate complete deduplication workflow"""
    print("\n🔄 COMPLETE DEDUPLICATION WORKFLOW")
    print("=" * 50)
    
    businesses, matches, merge_decisions, manual_review = demonstrate_manual_review_queue()
    engine = DeduplicationEngine(fuzzy_threshold=75.0)
    
    # Run complete deduplication
    print("🚀 Running complete deduplication workflow...")
    deduplicated, manual_review_final = engine.deduplicate_businesses(businesses)
    
    print(f"\n📈 RESULTS SUMMARY:")
    print(f"  Original businesses: {len(businesses)}")
    print(f"  After deduplication: {len(deduplicated)}")
    print(f"  Businesses merged: {len(businesses) - len(deduplicated)}")
    print(f"  Manual review required: {len(manual_review_final)}")
    print(f"  Automatic merges: {len(merge_decisions) - len(manual_review_final)}")
    
    print(f"\n📋 Final deduplicated business list:")
    for i, business in enumerate(deduplicated, 1):
        print(f"  {i}. {business.name}")
        print(f"     {business.raw_address}")
        if business.phone_number:
            print(f"     📞 {business.phone_number}")
        if business.email:
            print(f"     📧 {business.email}")
        if business.website:
            print(f"     🌐 {business.website}")
        print()


def main():
    """Run the complete demonstration"""
    print("🎯 BUSINESS DEDUPLICATION ENGINE DEMONSTRATION")
    print("=" * 60)
    print("This demo shows how the deduplication engine identifies and")
    print("merges duplicate business records from web scraping.\n")
    
    try:
        demonstrate_complete_workflow()
        
        print("\n✅ Demonstration completed successfully!")
        print("\nKey Features Demonstrated:")
        print("• Exact duplicate detection using hash comparison")
        print("• Fuzzy duplicate detection using RapidFuzz")
        print("• Confidence scoring and level determination")
        print("• Intelligent merge priority determination")
        print("• Automatic data merging with gap filling")
        print("• Manual review queue for uncertain matches")
        print("• Complete end-to-end deduplication workflow")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Demonstration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())