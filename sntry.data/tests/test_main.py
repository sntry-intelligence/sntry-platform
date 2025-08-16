"""
Test main application functionality
"""
import pytest
from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """Test main health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "jamaica-business-directory"


def test_business_health_check(client: TestClient):
    """Test business directory health check"""
    response = client.get("/api/v1/business/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["module"] == "business_directory"


def test_customer_health_check(client: TestClient):
    """Test customer 360 health check"""
    response = client.get("/api/v1/customer/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["module"] == "customer_360"


def test_get_businesses_empty(client: TestClient):
    """Test getting businesses when database is empty"""
    response = client.get("/api/v1/business/businesses")
    assert response.status_code == 200
    data = response.json()
    assert data["businesses"] == []
    assert data["total"] == 0
    assert data["skip"] == 0
    assert data["limit"] == 100


def test_get_customers_empty(client: TestClient):
    """Test getting customers when database is empty"""
    response = client.get("/api/v1/customer/customers")
    assert response.status_code == 200
    data = response.json()
    assert data["customers"] == []
    assert data["total"] == 0
    assert data["skip"] == 0
    assert data["limit"] == 100