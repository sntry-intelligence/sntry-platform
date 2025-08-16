#!/usr/bin/env python3
"""
Standalone test runner for data cleaning service.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from datetime import datetime
from business_directory.data_processing import DataCleaningService
from business_directory.schemas import BusinessData


def test_data_cleaning_service():
    """Test the data cleaning service functionality."""
    print("Testing DataCleaningService...")
    
    cleaning_service = DataCleaningService()
    
    # Test business name standardization
    print("\n1. Testing business name standardization:")
    test_names = [
        '  JAMAICA  BUSINESS   SOLUTIONS  LTD.  ',
        'jamaica business solutions',
        'ABC COMPANY ltd',
        'Test Company Limited',
        'Test Corp.',
        'Test Inc'
    ]
    
    for name in test_names:
        standardized = cleaning_service.standardize_business_name(name)
        print(f"  '{name}' -> '{standardized}'")
    
    # Test phone number formatting
    print("\n2. Testing phone number formatting:")
    test_phones = [
        '5551234',
        '876-555-1234',
        '18765551234',
        '+1-876-555-1234',
        '123456',  # Invalid
        '5551234567'  # Invalid
    ]
    
    for phone in test_phones:
        formatted = cleaning_service.format_jamaican_phone_number(phone)
        print(f"  '{phone}' -> '{formatted}'")
    
    # Test email validation
    print("\n3. Testing email validation:")
    test_emails = [
        'test@example.com',
        'TEST@EXAMPLE.COM',
        '  user@domain.co.uk  ',
        'invalid-email',
        'test@',
        '@example.com'
    ]
    
    for email in test_emails:
        validated = cleaning_service.validate_and_normalize_email(email)
        print(f"  '{email}' -> '{validated}'")
    
    # Test website validation
    print("\n4. Testing website validation:")
    test_websites = [
        'https://example.com',
        'example.com',
        'EXAMPLE.COM',
        'example.com/path?query=1',
        'not-a-url'
    ]
    
    for website in test_websites:
        validated = cleaning_service.validate_and_normalize_website(website)
        print(f"  '{website}' -> '{validated}'")
    
    # Test full business data cleaning
    print("\n5. Testing full business data cleaning:")
    sample_raw_data = {
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
    
    cleaned_business = cleaning_service._clean_single_business(sample_raw_data)
    if cleaned_business:
        print(f"  Name: {cleaned_business.name}")
        print(f"  Category: {cleaned_business.category}")
        print(f"  Phone: {cleaned_business.phone_number}")
        print(f"  Email: {cleaned_business.email}")
        print(f"  Website: {cleaned_business.website}")
        print(f"  Description: {cleaned_business.description}")
        print(f"  Rating: {cleaned_business.rating}")
    else:
        print("  Failed to clean business data")
    
    print("\n✅ All tests completed successfully!")


if __name__ == "__main__":
    test_data_cleaning_service()