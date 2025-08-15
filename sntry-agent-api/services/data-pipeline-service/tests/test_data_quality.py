import pytest
import tempfile
import os
from fastapi.testclient import TestClient


class TestDataQuality:
    """Test data quality validation functionality"""
    
    def test_validate_data_quality(self, client: TestClient, sample_csv_data):
        """Test data quality validation"""
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
            
            # Validate data quality
            validation_request = {
                "required_columns": ["id", "name", "email"],
                "data_types": {
                    "id": "integer",
                    "name": "string",
                    "age": "integer"
                },
                "value_ranges": {
                    "age": {"min": 0, "max": 120}
                },
                "regex_patterns": {
                    "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                },
                "custom_rules": ["completeness", "uniqueness", "validity"]
            }
            
            response = client.post(
                f"/data/validate?job_id={job_id}",
                json=validation_request
            )
            assert response.status_code == 200
            
            data = response.json()
            assert data["job_id"] == job_id
            assert "total_records" in data
            assert "valid_records" in data
            assert "invalid_records" in data
            assert "quality_score" in data
            assert "issues" in data
            assert "validation_summary" in data
            
            # Quality score should be between 0 and 100
            assert 0 <= data["quality_score"] <= 100
            
        finally:
            os.unlink(csv_path)
    
    def test_validate_nonexistent_job(self, client: TestClient):
        """Test validation for nonexistent job"""
        validation_request = {
            "required_columns": [],
            "data_types": {},
            "value_ranges": {},
            "regex_patterns": {},
            "custom_rules": []
        }
        
        response = client.post(
            "/data/validate?job_id=nonexistent-job-id",
            json=validation_request
        )
        assert response.status_code == 404
    
    def test_get_quality_report(self, client: TestClient, sample_csv_data):
        """Test getting quality report"""
        # Create ingestion job and validate
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
            
            # Validate data quality first
            validation_request = {
                "custom_rules": ["completeness", "uniqueness"]
            }
            
            validate_response = client.post(
                f"/data/validate?job_id={job_id}",
                json=validation_request
            )
            assert validate_response.status_code == 200
            
            # Get quality report
            report_response = client.get(f"/data/quality/{job_id}")
            assert report_response.status_code == 200
            
            report_data = report_response.json()
            assert report_data["job_id"] == job_id
            assert "total_records" in report_data
            assert "quality_score" in report_data
            assert "validation_summary" in report_data
            
        finally:
            os.unlink(csv_path)
    
    def test_get_nonexistent_quality_report(self, client: TestClient):
        """Test getting quality report for nonexistent job"""
        response = client.get("/data/quality/nonexistent-job-id")
        assert response.status_code == 404
    
    def test_validate_with_different_rules(self, client: TestClient, sample_csv_data):
        """Test validation with different rule combinations"""
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
            
            # Test different rule combinations
            rule_combinations = [
                ["completeness"],
                ["uniqueness"],
                ["validity"],
                ["consistency"],
                ["accuracy"],
                ["completeness", "uniqueness", "validity"],
                ["completeness", "uniqueness", "validity", "consistency", "accuracy"]
            ]
            
            for rules in rule_combinations:
                validation_request = {
                    "custom_rules": rules
                }
                
                response = client.post(
                    f"/data/validate?job_id={job_id}",
                    json=validation_request
                )
                assert response.status_code == 200
                
                data = response.json()
                assert "quality_score" in data
                assert isinstance(data["issues"], list)
                
        finally:
            os.unlink(csv_path)
    
    def test_validate_with_constraints(self, client: TestClient, sample_csv_data):
        """Test validation with specific constraints"""
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
            
            # Validate with specific constraints
            validation_request = {
                "required_columns": ["id", "name", "age", "email"],
                "data_types": {
                    "id": "integer",
                    "name": "string",
                    "age": "integer",
                    "email": "string"
                },
                "value_ranges": {
                    "age": {"min": 18, "max": 65},
                    "id": {"min": 1, "max": 1000}
                },
                "regex_patterns": {
                    "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                },
                "custom_rules": ["completeness", "validity"]
            }
            
            response = client.post(
                f"/data/validate?job_id={job_id}",
                json=validation_request
            )
            assert response.status_code == 200
            
            data = response.json()
            validation_summary = data["validation_summary"]
            assert "rules_applied" in validation_summary
            assert validation_summary["rules_applied"] == 2  # completeness + validity
            
        finally:
            os.unlink(csv_path)
    
    def test_validation_request_validation(self, client: TestClient):
        """Test validation request parameter validation"""
        # Test with invalid job_id parameter
        response = client.post("/data/validate", json={})
        assert response.status_code == 422  # Missing job_id parameter
        
        # Test with valid structure but nonexistent job
        validation_request = {
            "required_columns": [],
            "data_types": {},
            "value_ranges": {},
            "regex_patterns": {},
            "custom_rules": []
        }
        
        response = client.post(
            "/data/validate?job_id=test-job",
            json=validation_request
        )
        assert response.status_code == 404  # Job not found