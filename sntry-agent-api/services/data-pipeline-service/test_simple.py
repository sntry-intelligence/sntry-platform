#!/usr/bin/env python3
"""
Simple integration test for data pipeline service
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

import tempfile
import json
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    print("✓ Health check passed")

def test_synthetic_data_generation():
    """Test synthetic data generation"""
    request_data = {
        "template_type": "user_profile",
        "num_records": 5,
        "output_format": "json",
        "parameters": {"country": "US"},
        "preserve_privacy": True
    }
    
    response = client.post("/data/synthetic/generate", json=request_data)
    assert response.status_code == 200
    
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "processing"
    print("✓ Synthetic data generation started")
    
    # Check job status
    job_id = data["job_id"]
    status_response = client.get(f"/data/jobs/{job_id}/status")
    assert status_response.status_code == 200
    
    status_data = status_response.json()
    assert status_data["job_id"] == job_id
    print("✓ Job status retrieved")

def test_data_ingestion():
    """Test data ingestion with CSV"""
    # Create a temporary CSV file
    csv_content = """id,name,age,email
1,John Doe,30,john@example.com
2,Jane Smith,25,jane@example.com
3,Bob Johnson,35,bob@example.com"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(csv_content)
        csv_path = f.name
    
    try:
        request_data = {
            "source_type": "csv",
            "source_path": csv_path,
            "metadata": {"delimiter": ",", "encoding": "utf-8"},
            "validation_rules": ["completeness"]
        }
        
        response = client.post("/data/ingest", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "job_id" in data
        print("✓ Data ingestion started")
        
        # Test data cleaning
        job_id = data["job_id"]
        cleaning_request = {
            "job_id": job_id,
            "cleaning_operations": ["normalize_text"],
            "remove_duplicates": True,
            "handle_missing_values": "fill",
            "normalize_text": True
        }
        
        cleaning_response = client.post("/data/clean", json=cleaning_request)
        assert cleaning_response.status_code == 200
        print("✓ Data cleaning completed")
        
    finally:
        os.unlink(csv_path)

def test_get_templates():
    """Test getting synthetic data templates"""
    response = client.get("/data/templates")
    assert response.status_code == 200
    
    templates = response.json()
    assert isinstance(templates, list)
    assert len(templates) > 0
    
    template_names = [t["name"] for t in templates]
    assert "user_profile" in template_names
    assert "transaction" in template_names
    print("✓ Templates retrieved")

def test_get_formats():
    """Test getting supported formats"""
    response = client.get("/data/formats")
    assert response.status_code == 200
    
    formats = response.json()
    assert isinstance(formats, list)
    assert "csv" in formats
    assert "json" in formats
    print("✓ Supported formats retrieved")

if __name__ == "__main__":
    print("Running Data Pipeline Service Integration Tests...")
    
    try:
        test_health_check()
        test_synthetic_data_generation()
        test_data_ingestion()
        test_get_templates()
        test_get_formats()
        
        print("\n🎉 All tests passed! Data Pipeline Service is working correctly.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)