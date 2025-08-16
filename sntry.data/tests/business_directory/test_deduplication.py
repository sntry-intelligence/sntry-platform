"""
Tests for the deduplication engine functionality.
"""
import pytest
from datetime import datetime
from typing import List

from app.business_directory.data_processing import (
    DeduplicationEngine,
    DuplicateType,
    ConfidenceLevel,
    DuplicateMatch,
    MergeDecision
)
from app.business_directory.schemas import BusinessData


class TestDeduplicationEngine:
    """Test cases for the DeduplicationEngine class"""
    
    @pytest.fixture
    def deduplication_engine(self):
        """Create a deduplication engine instance for testing"""
        return DeduplicationEngine(fuzzy_threshold=80.0)
    
    @pytest.fixture
    def sample_businesses(self):
        """Create sample business data for testing"""
        now = datetime.now()
        
        businesses = [
            BusinessData(
                name="ABC Restaurant",
                raw_address="123 Main Street, Kingston 10, Jamaica",
                phone_number="(876) 123-4567",
                email="info@abcrestaurant.com",
                website="https://www.abcrestaurant.com",
                source_url="https://findyello.com/abc-restaurant",
                last_scraped_at=now,
                category="Restaurant"
            ),
            BusinessData(
                name="ABC Restaurant Ltd",
                raw_address="123 Main St, Kingston 10, Jamaica",
                phone_number="876-123-4567",
                email="info@abcrestaurant.com",
                source_url="https://workandjam.com/abc-restaurant",
                last_scraped_at=now,
                category="Restaurant"
            ),
            BusinessData(
                name="XYZ Auto Parts",
                raw_address="456 Spanish Town Road, Kingston, Jamaica",
                phone_number="(876) 987-6543",
                source_url="https://findyello.com/xyz-auto",
                last_scraped_at=now,
                category="Auto Parts"
            ),
            BusinessData(
                name="XYZ Auto Parts Inc",
                raw_address="456 Spanish Town Rd, Kingston, Jamaica",
                phone_number="876-987-6543",
                email="sales@xyzauto.com",
                source_url="https://workandjam.com/xyz-auto",
                last_scraped_at=now,
                category="Auto Parts"
            ),
            BusinessData(
                name="Unique Business",
                raw_address="789 Hope Road, Kingston 6, Jamaica",
                phone_number="(876) 555-1234",
                source_url="https://findyello.com/unique",
                last_scraped_at=now,
                category="Services"
            )
        ]
        
        return businesses
    
    def test_exact_duplicate_detection(self, deduplication_engine, sample_businesses):
        """Test exact duplicate detection using hash comparison"""
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
            phone_number="(876) 123-4567"  # Additional field shouldn't affect exact match
        )
        
        businesses = [business1, business2]
        matches = deduplication_engine.find_duplicates(businesses)
        
        assert len(matches) == 1
        assert matches[0].duplicate_type == DuplicateType.EXACT
        assert matches[0].confidence_score == 100.0
        assert matches[0].confidence_level == ConfidenceLevel.HIGH
    
    def test_fuzzy_duplicate_detection(self, deduplication_engine, sample_businesses):
        """Test fuzzy duplicate detection using RapidFuzz"""
        matches = deduplication_engine.find_duplicates(sample_businesses)
        
        # Should find 2 fuzzy matches (ABC Restaurant pair and XYZ Auto Parts pair)
        assert len(matches) == 2
        
        # Check that all matches are fuzzy type
        for match in matches:
            assert match.duplicate_type == DuplicateType.FUZZY
            assert match.confidence_score >= deduplication_engine.fuzzy_threshold
    
    def test_no_duplicates(self, deduplication_engine):
        """Test that no duplicates are found when businesses are unique"""
        businesses = [
            BusinessData(
                name="Business A",
                raw_address="123 Street A, Kingston, Jamaica",
                source_url="https://test1.com",
                last_scraped_at=datetime.now()
            ),
            BusinessData(
                name="Business B",
                raw_address="456 Street B, Spanish Town, Jamaica",
                source_url="https://test2.com",
                last_scraped_at=datetime.now()
            )
        ]
        
        matches = deduplication_engine.find_duplicates(businesses)
        assert len(matches) == 0
    
    def test_confidence_level_determination(self, deduplication_engine):
        """Test confidence level determination based on similarity scores"""
        assert deduplication_engine._determine_confidence_level(95.0) == ConfidenceLevel.HIGH
        assert deduplication_engine._determine_confidence_level(85.0) == ConfidenceLevel.MEDIUM
        assert deduplication_engine._determine_confidence_level(60.0) == ConfidenceLevel.LOW
        assert deduplication_engine._determine_confidence_level(40.0) == ConfidenceLevel.NONE
    
    def test_business_hash_generation(self, deduplication_engine):
        """Test business hash generation for exact duplicate detection"""
        business1 = BusinessData(
            name="Test Business",
            raw_address="123 Test Street",
            source_url="https://test.com",
            last_scraped_at=datetime.now()
        )
        
        business2 = BusinessData(
            name="Test Business",
            raw_address="123 Test Street",
            source_url="https://test2.com",  # Different source URL
            last_scraped_at=datetime.now(),
            phone_number="123-456-7890"  # Additional field
        )
        
        hash1 = deduplication_engine._generate_business_hash(business1)
        hash2 = deduplication_engine._generate_business_hash(business2)
        
        # Hashes should be the same because they're based on name and address only
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hash length
    
    def test_field_similarity_calculation(self, deduplication_engine):
        """Test similarity calculation for different field types"""
        # Test name similarity
        name_sim = deduplication_engine._calculate_field_similarity(
            "ABC Restaurant Ltd", "ABC Restaurant Limited", "name"
        )
        assert name_sim > 80.0
        
        # Test address similarity
        addr_sim = deduplication_engine._calculate_field_similarity(
            "123 Main Street, Kingston", "123 Main St, Kingston", "address"
        )
        assert addr_sim > 80.0
        
        # Test phone similarity
        phone_sim = deduplication_engine._calculate_field_similarity(
            "(876) 123-4567", "876-123-4567", "phone"
        )
        assert phone_sim == 100.0  # Same digits
        
        # Test email similarity
        email_sim = deduplication_engine._calculate_field_similarity(
            "test@example.com", "test@example.com", "email"
        )
        assert email_sim == 100.0
    
    def test_normalization_for_comparison(self, deduplication_engine):
        """Test field normalization for comparison"""
        # Test name normalization
        normalized_name = deduplication_engine._normalize_for_comparison(
            "ABC Restaurant Ltd.", "name"
        )
        assert "ltd" not in normalized_name
        
        # Test address normalization
        normalized_addr = deduplication_engine._normalize_for_comparison(
            "123 Main St.", "address"
        )
        assert "street" in normalized_addr
        
        # Test phone normalization
        normalized_phone = deduplication_engine._normalize_for_comparison(
            "(876) 123-4567", "phone"
        )
        assert normalized_phone == "8761234567"
        
        # Test website normalization
        normalized_website = deduplication_engine._normalize_for_comparison(
            "https://www.example.com", "website"
        )
        assert normalized_website == "example.com"
    
    def test_merge_priority_determination(self, deduplication_engine):
        """Test determination of merge priority between businesses"""
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
        
        primary, secondary = deduplication_engine._determine_merge_priority(
            complete_business, minimal_business
        )
        
        assert primary == complete_business
        assert secondary == minimal_business
    
    def test_merge_business_data(self, deduplication_engine):
        """Test merging of business data from two sources"""
        primary = BusinessData(
            name="Primary Business",
            raw_address="123 Street, Kingston, Jamaica",
            phone_number="(876) 123-4567",
            email="primary@test.com",
            source_url="https://primary.com",
            last_scraped_at=datetime.now(),
            rating=4.0
        )
        
        secondary = BusinessData(
            name="Secondary Business",
            raw_address="123 Street, Kingston, Jamaica",
            website="https://www.secondary.com",
            description="Secondary description",
            source_url="https://secondary.com",
            last_scraped_at=datetime.now(),
            rating=4.5
        )
        
        # Create a mock match
        match = DuplicateMatch(
            business1=primary,
            business2=secondary,
            duplicate_type=DuplicateType.FUZZY,
            confidence_score=85.0,
            confidence_level=ConfidenceLevel.MEDIUM,
            matching_fields=['name', 'raw_address'],
            similarity_scores={'name': 85.0, 'raw_address': 100.0}
        )
        
        merged_data = deduplication_engine._merge_business_data(primary, secondary, match)
        
        # Should keep primary data where it exists
        assert merged_data['name'] == primary.name
        assert merged_data['phone_number'] == primary.phone_number
        assert merged_data['email'] == primary.email
        
        # Should fill gaps with secondary data
        assert merged_data['website'] == secondary.website
        assert merged_data['description'] == secondary.description
        
        # Should use higher rating
        assert merged_data['rating'] == 4.5
    
    def test_create_merge_decisions(self, deduplication_engine, sample_businesses):
        """Test creation of merge decisions from duplicate matches"""
        matches = deduplication_engine.find_duplicates(sample_businesses)
        merge_decisions = deduplication_engine.create_merge_decisions(matches)
        
        assert len(merge_decisions) > 0
        
        for decision in merge_decisions:
            assert isinstance(decision, MergeDecision)
            assert decision.primary_business is not None
            assert decision.secondary_business is not None
            assert decision.merged_data is not None
            assert decision.merge_strategy in ["automatic", "review_required"]
    
    def test_manual_review_queue(self, deduplication_engine):
        """Test identification of matches requiring manual review"""
        # Create matches with different confidence levels
        high_confidence_match = DuplicateMatch(
            business1=BusinessData(name="Test1", raw_address="Addr1", source_url="url1", last_scraped_at=datetime.now()),
            business2=BusinessData(name="Test2", raw_address="Addr2", source_url="url2", last_scraped_at=datetime.now()),
            duplicate_type=DuplicateType.FUZZY,
            confidence_score=95.0,
            confidence_level=ConfidenceLevel.HIGH,
            matching_fields=['name'],
            similarity_scores={'name': 95.0}
        )
        
        medium_confidence_match = DuplicateMatch(
            business1=BusinessData(name="Test3", raw_address="Addr3", source_url="url3", last_scraped_at=datetime.now()),
            business2=BusinessData(name="Test4", raw_address="Addr4", source_url="url4", last_scraped_at=datetime.now()),
            duplicate_type=DuplicateType.FUZZY,
            confidence_score=75.0,
            confidence_level=ConfidenceLevel.MEDIUM,
            matching_fields=['name'],
            similarity_scores={'name': 75.0}
        )
        
        matches = [high_confidence_match, medium_confidence_match]
        manual_review = deduplication_engine.get_manual_review_queue(matches)
        
        # Only medium confidence should require manual review
        assert len(manual_review) == 1
        assert manual_review[0] == medium_confidence_match
    
    def test_complete_deduplication_workflow(self, deduplication_engine, sample_businesses):
        """Test the complete deduplication workflow"""
        original_count = len(sample_businesses)
        
        deduplicated, manual_review = deduplication_engine.deduplicate_businesses(sample_businesses)
        
        # Should have fewer businesses after deduplication
        assert len(deduplicated) < original_count
        
        # Should have some matches for manual review
        assert isinstance(manual_review, list)
        
        # All businesses in deduplicated list should be unique
        business_hashes = set()
        for business in deduplicated:
            business_hash = deduplication_engine._generate_business_hash(business)
            assert business_hash not in business_hashes
            business_hashes.add(business_hash)
    
    def test_empty_business_list(self, deduplication_engine):
        """Test deduplication with empty business list"""
        matches = deduplication_engine.find_duplicates([])
        assert matches == []
        
        deduplicated, manual_review = deduplication_engine.deduplicate_businesses([])
        assert deduplicated == []
        assert manual_review == []
    
    def test_single_business(self, deduplication_engine):
        """Test deduplication with single business"""
        business = BusinessData(
            name="Single Business",
            raw_address="123 Street, Kingston, Jamaica",
            source_url="https://test.com",
            last_scraped_at=datetime.now()
        )
        
        matches = deduplication_engine.find_duplicates([business])
        assert matches == []
        
        deduplicated, manual_review = deduplication_engine.deduplicate_businesses([business])
        assert len(deduplicated) == 1
        assert deduplicated[0] == business
        assert manual_review == []


class TestDeduplicationEngineConfiguration:
    """Test deduplication engine configuration options"""
    
    def test_custom_fuzzy_threshold(self):
        """Test deduplication engine with custom fuzzy threshold"""
        engine = DeduplicationEngine(fuzzy_threshold=90.0)
        assert engine.fuzzy_threshold == 90.0
    
    def test_custom_exact_match_fields(self):
        """Test deduplication engine with custom exact match fields"""
        custom_fields = ['name', 'phone_number']
        engine = DeduplicationEngine(exact_match_fields=custom_fields)
        assert engine.exact_match_fields == custom_fields
    
    def test_field_weights_configuration(self):
        """Test that field weights are properly configured"""
        engine = DeduplicationEngine()
        
        # Check that weights sum to 1.0 (or close to it)
        total_weight = sum(engine.field_weights.values())
        assert abs(total_weight - 1.0) < 0.01
        
        # Check that name has highest weight
        assert engine.field_weights['name'] >= engine.field_weights['raw_address']
        assert engine.field_weights['raw_address'] >= engine.field_weights['phone_number']


class TestDeduplicationWithoutRapidFuzz:
    """Test deduplication behavior when RapidFuzz is not available"""
    
    def test_fuzzy_matching_disabled_without_rapidfuzz(self, monkeypatch):
        """Test that fuzzy matching is disabled when RapidFuzz is not available"""
        # Mock RapidFuzz as unavailable
        monkeypatch.setattr('app.business_directory.data_processing.RAPIDFUZZ_AVAILABLE', False)
        
        engine = DeduplicationEngine()
        assert not engine.use_fuzzy_matching
        
        # Create similar businesses that would normally match with fuzzy logic
        business1 = BusinessData(
            name="ABC Restaurant",
            raw_address="123 Main Street, Kingston, Jamaica",
            source_url="https://test1.com",
            last_scraped_at=datetime.now()
        )
        
        business2 = BusinessData(
            name="ABC Restaurant Ltd",
            raw_address="123 Main St, Kingston, Jamaica",
            source_url="https://test2.com",
            last_scraped_at=datetime.now()
        )
        
        matches = engine.find_duplicates([business1, business2])
        
        # Should not find fuzzy matches when RapidFuzz is unavailable
        assert len(matches) == 0