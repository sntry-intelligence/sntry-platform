import pytest
import tempfile
import os
from fastapi.testclient import TestClient


class TestDataCleaning:
    """Test data cleaning functionality"""
    
    def test_clean_data_success(self, client: TestClient, sample_csv_data):
        """Test successful data cleaning"""
        # First create an ingestion job
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(sample_csv_data)
            csv_path = f.name
        
        try:
            # Create ingestion job
            ingestion_request = {
                "source_type": "csv",
                "source_path": csv_path,
                "metadata": {},
                "validation_rules": []
            }
            
            ingestion_response = client.post("/data/ingest", json=ingestion_request)
            assert ingestion_response.status_code == 200
            job_id = ingestion_response.json()["job_id"]
            
            # Wait a moment for ingestion to complete (in real scenario)
            # For testing, we'll assume it completes quickly
            
            # Clean the data
            cleaning_request = {
                "job_id": job_id,
                "cleaning_operations": ["remove_outliers", "normalize_text"],
                "remove_duplicates": True,
                "handle_missing_values": "fill",
                "normalize_text": True
            }
            
            response = client.post("/data/clean", json=cleaning_request)
            assert response.status_code == 200
            
            data = response.json()
            assert data["job_id"] == job_id
            assert data["message"] == "Data cleaning completed"
            assert "results" in data
            
            results = data["results"]
            assert "original_records" in results
            assert "operations_applied" in results
            assert "final_records" in results
            
        finally:
            os.unlink(csv_path)
    
    def test_clean_nonexistent_job(self, client: TestClient):
        """Test cleaning data for nonexistent job"""
        cleaning_request = {
            "job_id": "nonexistent-job-id",
            "cleaning_operations": [],
            "remove_duplicates": True,
            "handle_missing_values": "drop",
            "normalize_text": False
        }
        
        response = client.post("/data/clean", json=cleaning_request)
        assert response.status_code == 500
    
    def test_clean_data_with_different_operations(self, client: TestClient, sample_csv_data):
        """Test data cleaning with different operations"""
        # Create ingestion job first
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(sample_csv_data)
            csv_path = f.name
        
        try:
            ingestion_request = {
                "source_type": "csv",
                "source_path": csv_path,
                "metadata": {},
                "validation_rules": []
            }
            
            ingestion_response = client.post("/data/ingest", json=ingestion_request)
            job_id = ingestion_response.json()["job_id"]
            
            # Test different cleaning configurations
            test_cases = [
                {
                    "remove_duplicates": False,
                    "handle_missing_values": "drop",
                    "normalize_text": False
                },
                {
                    "remove_duplicates": True,
                    "handle_missing_values": "interpolate",
                    "normalize_text": True
                }
            ]
            
            for case in test_cases:
                cleaning_request = {
                    "job_id": job_id,
                    "cleaning_operations": ["standardize_formats"],
                    **case
                }
                
                response = client.post("/data/clean", json=cleaning_request)
                assert response.status_code == 200
                
                data = response.json()
                assert "results" in data
                
        finally:
            os.unlink(csv_path)
    
    def test_clean_data_validation(self, client: TestClient):
        """Test data cleaning request validation"""
        # Test missing required fields
        invalid_request = {
            "cleaning_operations": [],
            "remove_duplicates": True
            # Missing job_id
        }
        
        response = client.post("/data/clean", json=invalid_request)
        assert response.status_code == 422  # Validation error
    
    def test_clean_data_with_custom_operations(self, client: TestClient, sample_csv_data):
        """Test data cleaning with custom operations"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(sample_csv_data)
            csv_path = f.name
        
        try:
            # Create ingestion job
            ingestion_request = {
                "source_type": "csv",
                "source_path": csv_path,
                "metadata": {},
                "validation_rules": []
            }
            
            ingestion_response = client.post("/data/ingest", json=ingestion_request)
            job_id = ingestion_response.json()["job_id"]
            
            # Clean with custom operations
            cleaning_request = {
                "job_id": job_id,
                "cleaning_operations": [
                    "remove_duplicates",
                    "handle_missing_values", 
                    "normalize_text",
                    "validate_data_types"
                ],
                "remove_duplicates": True,
                "handle_missing_values": "fill",
                "normalize_text": True
            }
            
            response = client.post("/data/clean", json=cleaning_request)
            assert response.status_code == 200
            
            data = response.json()
            results = data["results"]
            assert len(results["operations_applied"]) > 0
            
        finally:
            os.unlink(csv_path)