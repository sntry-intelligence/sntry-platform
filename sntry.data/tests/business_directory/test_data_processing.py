"""
Unit tests for data processing and cleaning services.
"""
import pytest
from datetime import datetime
from typing import Dict, Any

from app.business_directory.data_processing import DataCleaningService, AddressParsingService
from app.business_directory.schemas import BusinessData, ParsedAddress


class TestDataCleaningService:
    """Test cases for DataCleaningService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cleaning_service = DataCleaningService()
        self.sample_raw_data = {
            'name': '  JAMAICA  BUSINESS   SOLUTIONS  LTD.  ',
            'category': 'business services',
            'raw_address': '123 Main Street, Kingston 10, Jamaica',
            'phone_number': '876-555-1234',
            'email': 'INFO@JAMAICABUSINESS.COM',
            'website': 'jamaicabusiness.com',
            'description': '  Professional business services  in Jamaica  ',
            'operating_hours': 'Mon-Fri 9AM-5PM',
            'rating': '4.5',
            'source_url': 'https://findyello.com/business/123',
            'last_scraped_at': datetime.now(),
            'scrape_status': 'success',
            'is_active': True
        }
    
    def test_standardize_business_name(self):
        """Test business name standardization."""
        # Test extra spaces removal
        assert self.cleaning_service.standardize_business_name('  Multiple   Spaces  ') == 'Multiple Spaces'
        
        # Test title case conversion
        assert self.cleaning_service.standardize_business_name('jamaica business solutions') == 'Jamaica Business Solutions'
        
        # Test acronym preservation
        assert self.cleaning_service.standardize_business_name('ABC COMPANY ltd') == 'ABC COMPANY LTD'
        
        # Test business suffix standardization
        assert self.cleaning_service.standardize_business_name('Test Company Limited') == 'Test Company LTD'
        assert self.cleaning_service.standardize_business_name('Test Corp.') == 'Test CORP'
        assert self.cleaning_service.standardize_business_name('Test Inc') == 'Test INC'
        
        # Test empty/None input
        assert self.cleaning_service.standardize_business_name('') == ''
        assert self.cleaning_service.standardize_business_name(None) == ''
    
    def test_format_jamaican_phone_number(self):
        """Test Jamaican phone number formatting."""
        # Test 7-digit local number
        assert self.cleaning_service.format_jamaican_phone_number('5551234') == '555-1234'
        assert self.cleaning_service.format_jamaican_phone_number('555-1234') == '555-1234'
        
        # Test 10-digit with area code
        assert self.cleaning_service.format_jamaican_phone_number('8765551234') == '(876) 555-1234'
        assert self.cleaning_service.format_jamaican_phone_number('876-555-1234') == '(876) 555-1234'
        
        # Test 11-digit with country code
        assert self.cleaning_service.format_jamaican_phone_number('18765551234') == '+1 (876) 555-1234'
        assert self.cleaning_service.format_jamaican_phone_number('+1-876-555-1234') == '+1 (876) 555-1234'
        
        # Test invalid formats
        assert self.cleaning_service.format_jamaican_phone_number('123456') is None  # Too short
        assert self.cleaning_service.format_jamaican_phone_number('12345678901') is None  # Too long
        assert self.cleaning_service.format_jamaican_phone_number('5551234567') is None  # Wrong area code
        assert self.cleaning_service.format_jamaican_phone_number('') is None
        assert self.cleaning_service.format_jamaican_phone_number(None) is None
    
    def test_validate_and_normalize_email(self):
        """Test email validation and normalization."""
        # Test valid emails
        assert self.cleaning_service.validate_and_normalize_email('test@example.com') == 'test@example.com'
        assert self.cleaning_service.validate_and_normalize_email('TEST@EXAMPLE.COM') == 'test@example.com'
        assert self.cleaning_service.validate_and_normalize_email('  user@domain.co.uk  ') == 'user@domain.co.uk'
        
        # Test invalid emails
        assert self.cleaning_service.validate_and_normalize_email('invalid-email') is None
        assert self.cleaning_service.validate_and_normalize_email('test@') is None
        assert self.cleaning_service.validate_and_normalize_email('@example.com') is None
        assert self.cleaning_service.validate_and_normalize_email('') is None
        assert self.cleaning_service.validate_and_normalize_email(None) is None
    
    def test_validate_and_normalize_website(self):
        """Test website URL validation and normalization."""
        # Test valid URLs
        assert self.cleaning_service.validate_and_normalize_website('https://example.com') == 'https://example.com'
        assert self.cleaning_service.validate_and_normalize_website('http://example.com') == 'http://example.com'
        assert self.cleaning_service.validate_and_normalize_website('example.com') == 'https://example.com'
        assert self.cleaning_service.validate_and_normalize_website('EXAMPLE.COM') == 'https://example.com'
        
        # Test URLs with paths and queries
        assert self.cleaning_service.validate_and_normalize_website('example.com/path?query=1') == 'https://example.com/path?query=1'
        
        # Test invalid URLs
        assert self.cleaning_service.validate_and_normalize_website('not-a-url') is None
        assert self.cleaning_service.validate_and_normalize_website('') is None
        assert self.cleaning_service.validate_and_normalize_website(None) is None
    
    def test_clean_single_business_valid_data(self):
        """Test cleaning a single valid business record."""
        result = self.cleaning_service._clean_single_business(self.sample_raw_data)
        
        assert result is not None
        assert isinstance(result, BusinessData)
        assert result.name == 'Jamaica Business Solutions LTD'
        assert result.category == 'Business Services'
        assert result.phone_number == '(876) 555-1234'
        assert result.email == 'info@jamaicabusiness.com'
        assert result.website == 'https://jamaicabusiness.com'
        assert result.description == 'Professional business services in Jamaica'
    
    def test_clean_single_business_missing_required_fields(self):
        """Test cleaning business with missing required fields."""
        # Missing name
        invalid_data = self.sample_raw_data.copy()
        invalid_data['name'] = ''
        assert self.cleaning_service._clean_single_business(invalid_data) is None
        
        # Missing address
        invalid_data = self.sample_raw_data.copy()
        invalid_data['raw_address'] = ''
        assert self.cleaning_service._clean_single_business(invalid_data) is None
        
        # Missing source URL
        invalid_data = self.sample_raw_data.copy()
        invalid_data['source_url'] = ''
        assert self.cleaning_service._clean_single_business(invalid_data) is None
    
    def test_clean_business_data_batch(self):
        """Test cleaning multiple business records."""
        raw_data_list = [
            self.sample_raw_data,
            {
                'name': 'Another Business',
                'raw_address': '456 Second Street, Spanish Town',
                'source_url': 'https://workandjam.com/business/456',
                'last_scraped_at': datetime.now(),
                'phone_number': '5551234',  # 7-digit local
                'email': 'contact@another.com'
            },
            {
                'name': '',  # Invalid - empty name
                'raw_address': '789 Third Street',
                'source_url': 'https://example.com/789',
                'last_scraped_at': datetime.now()
            }
        ]
        
        results = self.cleaning_service.clean_business_data(raw_data_list)
        
        # Should return 2 valid businesses (third one is invalid)
        assert len(results) == 2
        assert all(isinstance(business, BusinessData) for business in results)
        assert results[0].name == 'Jamaica Business Solutions LTD'
        assert results[1].name == 'Another Business'
        assert results[1].phone_number == '555-1234'  # Formatted 7-digit
    
    def test_remove_invalid_entries(self):
        """Test removal of invalid business entries."""
        valid_business = BusinessData(
            name='Valid Business',
            raw_address='123 Valid Street, Kingston',
            source_url='https://example.com/valid',
            last_scraped_at=datetime.now(),
            phone_number='(876) 555-1234'
        )
        
        invalid_business_short_name = BusinessData(
            name='A',  # Too short
            raw_address='123 Street',
            source_url='https://example.com/invalid1',
            last_scraped_at=datetime.now()
        )
        
        invalid_business_short_address = BusinessData(
            name='Invalid Business',
            raw_address='123',  # Too short
            source_url='https://example.com/invalid2',
            last_scraped_at=datetime.now()
        )
        
        businesses = [valid_business, invalid_business_short_name, invalid_business_short_address]
        valid_businesses = self.cleaning_service.remove_invalid_entries(businesses)
        
        assert len(valid_businesses) == 1
        assert valid_businesses[0].name == 'Valid Business'
    
    def test_rating_cleaning(self):
        """Test rating value cleaning and validation."""
        # Valid ratings
        assert self.cleaning_service._clean_rating('4.5') == 4.5
        assert self.cleaning_service._clean_rating(3) == 3.0
        assert self.cleaning_service._clean_rating(5.0) == 5.0
        assert self.cleaning_service._clean_rating('0') == 0.0
        
        # Invalid ratings
        assert self.cleaning_service._clean_rating('6.0') is None  # Out of range
        assert self.cleaning_service._clean_rating('-1') is None  # Out of range
        assert self.cleaning_service._clean_rating('invalid') is None  # Not a number
        assert self.cleaning_service._clean_rating('') is None
        assert self.cleaning_service._clean_rating(None) is None
    
    def test_unicode_normalization(self):
        """Test unicode normalization in business names."""
        # Test with accented characters
        name_with_accents = 'Café Résumé'
        normalized = self.cleaning_service.standardize_business_name(name_with_accents)
        assert normalized == 'Café Résumé'  # Should preserve valid unicode
        
        # Test with extra unicode spaces
        name_with_unicode_spaces = 'Business\u2000\u2001Name'  # En quad and em quad
        normalized = self.cleaning_service.standardize_business_name(name_with_unicode_spaces)
        assert normalized == 'Business Name'  # Should normalize to regular space

class TestAddressParsingService:
    """Test cases for AddressParsingService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.address_service = AddressParsingService()
    
    def test_parse_simple_street_address(self):
        """Test parsing a simple street address."""
        address = "123 Main Street, Kingston 10, Jamaica"
        parsed = self.address_service.parse_address(address)
        
        assert parsed.house_number == "123"
        assert parsed.street_name == "MAIN STREET"
        assert parsed.city == "KINGSTON"
        assert parsed.postal_zone == "KINGSTON 10"
        assert parsed.country == "JAMAICA"
    
    def test_parse_po_box_address(self):
        """Test parsing a PO Box address."""
        address = "P.O. Box 1234, Spanish Town 01, Jamaica"
        parsed = self.address_service.parse_address(address)
        
        assert parsed.po_box == "PO BOX 1234"
        assert parsed.city == "SPANISH TOWN"
        assert parsed.postal_zone == "SPANISH TOWN 01"
        assert parsed.country == "JAMAICA"
    
    def test_parse_address_with_parish(self):
        """Test parsing address with parish information."""
        address = "456 Hope Road, Kingston 6, St. Andrew, Jamaica"
        parsed = self.address_service.parse_address(address)
        
        assert parsed.house_number == "456"
        assert parsed.street_name == "HOPE ROAD"
        assert parsed.city == "KINGSTON"
        assert parsed.postal_zone == "KINGSTON 06"
        assert parsed.parish == "ST. ANDREW"
    
    def test_parse_address_with_abbreviations(self):
        """Test parsing address with street type abbreviations."""
        address = "789 Orange St., New Kingston, Jamaica"
        parsed = self.address_service.parse_address(address)
        
        assert parsed.house_number == "789"
        assert parsed.street_name == "ORANGE STREET"
        assert parsed.city == "NEW KINGSTON"
    
    def test_parse_incomplete_address(self):
        """Test parsing an incomplete address."""
        address = "Somewhere in Montego Bay"
        parsed = self.address_service.parse_address(address)
        
        assert parsed.city == "MONTEGO BAY"
        assert parsed.country == "JAMAICA"
        assert parsed.house_number is None
        assert parsed.street_name == "SOMEWHERE IN MONTEGO BAY"
    
    def test_validate_complete_address(self):
        """Test validation of a complete address."""
        parsed = ParsedAddress(
            house_number="123",
            street_name="MAIN STREET",
            city="KINGSTON",
            postal_zone="KINGSTON 10",
            parish="ST. ANDREW",
            country="JAMAICA",
            formatted_address="123 MAIN STREET, KINGSTON 10, ST. ANDREW, JAMAICA"
        )
        
        is_valid, issues = self.address_service.validate_parsed_address(parsed)
        assert is_valid
        assert len(issues) == 0
    
    def test_validate_incomplete_address(self):
        """Test validation of an incomplete address."""
        parsed = ParsedAddress(
            city="UNKNOWN",
            country="JAMAICA",
            formatted_address="Some incomplete address"
        )
        
        is_valid, issues = self.address_service.validate_parsed_address(parsed)
        assert not is_valid
        assert "No street address or PO Box found" in issues
        assert "No city identified" in issues
    
    def test_completeness_score_complete_address(self):
        """Test completeness scoring for a complete address."""
        parsed = ParsedAddress(
            house_number="123",
            street_name="MAIN STREET",
            city="KINGSTON",
            postal_zone="KINGSTON 10",
            parish="ST. ANDREW",
            country="JAMAICA",
            formatted_address="123 MAIN STREET, KINGSTON 10, ST. ANDREW, JAMAICA"
        )
        
        score = self.address_service.calculate_completeness_score(parsed)
        assert score >= 0.9  # Should be nearly complete
    
    def test_completeness_score_minimal_address(self):
        """Test completeness scoring for a minimal address."""
        parsed = ParsedAddress(
            city="KINGSTON",
            country="JAMAICA",
            formatted_address="KINGSTON, JAMAICA"
        )
        
        score = self.address_service.calculate_completeness_score(parsed)
        assert 0.3 <= score <= 0.5  # Should be moderately complete
    
    def test_standardize_multiple_addresses(self):
        """Test standardizing multiple addresses."""
        addresses = [
            "123 Main St, Kingston 10",
            "P.O. Box 456, Spanish Town",
            "789 Hope Rd, New Kingston",
            "Invalid address format"
        ]
        
        parsed_addresses = self.address_service.standardize_addresses(addresses)
        
        assert len(parsed_addresses) == 4
        assert parsed_addresses[0].house_number == "123"
        assert parsed_addresses[1].po_box == "PO BOX 456"
        assert parsed_addresses[2].street_name == "HOPE ROAD"
        assert parsed_addresses[3].city == "UNKNOWN"  # Fallback for invalid address
    
    def test_extract_city_from_context(self):
        """Test city extraction from various contexts."""
        test_cases = [
            ("Located in Montego Bay, Jamaica", "MONTEGO BAY"),
            ("Business in Ocho Rios", "OCHO RIOS"),
            ("Mandeville, Jamaica", "MANDEVILLE"),
            ("Port Antonio 12345", "PORT ANTONIO")
        ]
        
        for address, expected_city in test_cases:
            city = self.address_service._extract_city(address)
            assert city == expected_city, f"Failed to extract '{expected_city}' from '{address}'"
    
    def test_parish_extraction(self):
        """Test parish extraction from addresses."""
        test_cases = [
            ("123 Main St, Kingston, St. Andrew", "ST. ANDREW"),
            ("Business in Westmoreland Parish", "WESTMORELAND"),
            ("Located in St. James", "ST. JAMES"),
            ("No parish mentioned", None)
        ]
        
        for address, expected_parish in test_cases:
            parish = self.address_service._extract_parish(address)
            assert parish == expected_parish, f"Failed to extract parish from '{address}'"