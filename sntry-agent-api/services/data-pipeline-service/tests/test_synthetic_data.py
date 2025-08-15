import pytest
from fastapi.testclient import TestClient


class TestSyntheticData:
    """Test synthetic data generation functionality"""
    
    def test_generate_user_profiles(self, client: TestClient):
        """Test generating synthetic user profile data"""
        request_data = {
            "template_type": "user_profile",
            "num_records": 10,
            "output_format": "json",
            "parameters": {
                "country": "US",
                "language": "en"
            },
            "preserve_privacy": True
        }
        
        response = client.post("/data/synthetic/generate", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "processing"
        assert data["message"] == "Synthetic data generation started"
    
    def test_generate_transactions(self, client: TestClient):
        """Test generating synthetic transaction data"""
        request_data = {
            "template_type": "transaction",
            "num_records": 50,
            "output_format": "csv",
            "parameters": {
                "num_users": 10,
                "currency": "USD",
                "country": "US"
            },
            "preserve_privacy": False
        }
        
        response = client.post("/data/synthetic/generate", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "job_id" in data
    
    def test_generate_products(self, client: TestClient):
        """Test generating synthetic product data"""
        request_data = {
            "template_type": "product",
            "num_records": 25,
            "output_format": "json",
            "parameters": {
                "categories": ["Electronics", "Books", "Clothing"],
                "currency": "EUR"
            },
            "preserve_privacy": True
        }
        
        response = client.post("/data/synthetic/generate", json=request_data)
        assert response.status_code == 200
    
    def test_generate_conversations(self, client: TestClient):
        """Test generating synthetic conversation data"""
        request_data = {
            "template_type": "conversation",
            "num_records": 20,
            "output_format": "json",
            "parameters": {
                "language": "en"
            },
            "preserve_privacy": True
        }
        
        response = client.post("/data/synthetic/generate", json=request_data)
        assert response.status_code == 200
    
    def test_generate_documents(self, client: TestClient):
        """Test generating synthetic document data"""
        request_data = {
            "template_type": "document",
            "num_records": 15,
            "output_format": "json",
            "parameters": {
                "document_types": ["article", "report", "manual"],
                "language": "en"
            },
            "preserve_privacy": True
        }
        
        response = client.post("/data/synthetic/generate", json=request_data)
        assert response.status_code == 200
    
    def test_generate_sensor_data(self, client: TestClient):
        """Test generating synthetic sensor data"""
        request_data = {
            "template_type": "sensor_data",
            "num_records": 100,
            "output_format": "csv",
            "parameters": {
                "sensor_types": ["temperature", "humidity", "pressure"],
                "num_devices": 5
            },
            "preserve_privacy": True
        }
        
        response = client.post("/data/synthetic/generate", json=request_data)
        assert response.status_code == 200
    
    def test_generate_invalid_template(self, client: TestClient):
        """Test generating data with invalid template"""
        request_data = {
            "template_type": "invalid_template",
            "num_records": 10,
            "output_format": "json",
            "parameters": {},
            "preserve_privacy": True
        }
        
        response = client.post("/data/synthetic/generate", json=request_data)
        assert response.status_code == 500
    
    def test_generate_with_invalid_num_records(self, client: TestClient):
        """Test generating data with invalid number of records"""
        request_data = {
            "template_type": "user_profile",
            "num_records": 0,  # Invalid: must be > 0
            "output_format": "json",
            "parameters": {},
            "preserve_privacy": True
        }
        
        response = client.post("/data/synthetic/generate", json=request_data)
        assert response.status_code == 422  # Validation error
    
    def test_generate_with_max_records(self, client: TestClient):
        """Test generating data with maximum allowed records"""
        request_data = {
            "template_type": "user_profile",
            "num_records": 100000,  # Maximum allowed
            "output_format": "json",
            "parameters": {},
            "preserve_privacy": True
        }
        
        response = client.post("/data/synthetic/generate", json=request_data)
        assert response.status_code == 200
    
    def test_generate_with_excessive_records(self, client: TestClient):
        """Test generating data with too many records"""
        request_data = {
            "template_type": "user_profile",
            "num_records": 100001,  # Exceeds maximum
            "output_format": "json",
            "parameters": {},
            "preserve_privacy": True
        }
        
        response = client.post("/data/synthetic/generate", json=request_data)
        assert response.status_code == 422  # Validation error
    
    def test_get_synthetic_data_templates(self, client: TestClient):
        """Test getting available synthetic data templates"""
        response = client.get("/data/templates")
        assert response.status_code == 200
        
        templates = response.json()
        assert isinstance(templates, list)
        assert len(templates) > 0
        
        # Check template structure
        for template in templates:
            assert "name" in template
            assert "description" in template
            assert "parameters" in template
        
        # Check specific templates exist
        template_names = [t["name"] for t in templates]
        assert "user_profile" in template_names
        assert "transaction" in template_names
        assert "product" in template_names
        assert "conversation" in template_names
        assert "document" in template_names
        assert "sensor_data" in template_names
    
    def test_get_synthetic_job_status(self, client: TestClient):
        """Test getting synthetic data job status"""
        # First create a synthetic data job
        request_data = {
            "template_type": "user_profile",
            "num_records": 5,
            "output_format": "json",
            "parameters": {},
            "preserve_privacy": True
        }
        
        response = client.post("/data/synthetic/generate", json=request_data)
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        
        # Get job status
        status_response = client.get(f"/data/jobs/{job_id}/status")
        assert status_response.status_code == 200
        
        status_data = status_response.json()
        assert status_data["job_id"] == job_id
        assert "status" in status_data
        assert status_data["message"] == "Synthetic data generation job"