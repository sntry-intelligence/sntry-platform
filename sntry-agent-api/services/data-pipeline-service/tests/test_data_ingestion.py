import pytest
import tempfile
import os
import json
from fastapi.testclient import TestClient


class TestDataIngestion:
    """Test data ingestion functionality"""
    
    def test_health_check(self, client: TestClient):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "data-pipeline-service"
    
    def test_ingest_csv_data(self, client: TestClient, sample_csv_data):
        """Test CSV data ingestion"""
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(sample_csv_data)
            csv_path = f.name
        
        try:
            request_data = {
                "source_type": "csv",
                "source_path": csv_path,
                "metadata": {
                    "delimiter": ",",
                    "encoding": "utf-8",
                    "header": 0
                },
                "validation_rules": ["completeness", "uniqueness"]
            }
            
            response = client.post("/data/ingest", json=request_data)
            assert response.status_code == 200
            
            data = response.json()
            assert "job_id" in data
            assert data["status"] == "processing"
            assert data["message"] == "Data ingestion started"
            
        finally:
            os.unlink(csv_path)
    
    def test_ingest_json_data(self, client: TestClient, sample_json_data):
        """Test JSON data ingestion"""
        # Create temporary JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_json_data, f)
            json_path = f.name
        
        try:
            request_data = {
                "source_type": "json",
                "source_path": json_path,
                "metadata": {},
                "validation_rules": ["completeness"]
            }
            
            response = client.post("/data/ingest", json=request_data)
            assert response.status_code == 200
            
            data = response.json()
            assert "job_id" in data
            assert data["status"] == "processing"
            
        finally:
            os.unlink(json_path)
    
    def test_ingest_invalid_source_type(self, client: TestClient):
        """Test ingestion with invalid source type"""
        request_data = {
            "source_type": "invalid_format",
            "source_path": "/path/to/file",
            "metadata": {},
            "validation_rules": []
        }
        
        response = client.post("/data/ingest", json=request_data)
        assert response.status_code == 422  # Validation error
    
    def test_ingest_nonexistent_file(self, client: TestClient):
        """Test ingestion with nonexistent file"""
        request_data = {
            "source_type": "csv",
            "source_path": "/nonexistent/file.csv",
            "metadata": {},
            "validation_rules": []
        }
        
        response = client.post("/data/ingest", json=request_data)
        assert response.status_code == 500
    
    def test_get_job_status(self, client: TestClient, sample_csv_data):
        """Test getting job status"""
        # First create a job
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(sample_csv_data)
            csv_path = f.name
        
        try:
            request_data = {
                "source_type": "csv",
                "source_path": csv_path,
                "metadata": {},
                "validation_rules": []
            }
            
            response = client.post("/data/ingest", json=request_data)
            assert response.status_code == 200
            job_id = response.json()["job_id"]
            
            # Get job status
            status_response = client.get(f"/data/jobs/{job_id}/status")
            assert status_response.status_code == 200
            
            status_data = status_response.json()
            assert status_data["job_id"] == job_id
            assert "status" in status_data
            assert "created_at" in status_data
            
        finally:
            os.unlink(csv_path)
    
    def test_get_nonexistent_job_status(self, client: TestClient):
        """Test getting status for nonexistent job"""
        response = client.get("/data/jobs/nonexistent-job-id/status")
        assert response.status_code == 404
    
    def test_get_supported_formats(self, client: TestClient):
        """Test getting supported data formats"""
        response = client.get("/data/formats")
        assert response.status_code == 200
        
        formats = response.json()
        assert isinstance(formats, list)
        assert "csv" in formats
        assert "json" in formats
        assert "parquet" in formats