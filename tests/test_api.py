"""Test cases for the LLM Microservice API endpoints."""

from fastapi.testclient import TestClient

from microservice_llm import microservice_llm

client = TestClient(microservice_llm)


def test_root_endpoint():
    """Test the root endpoint returns correct health status."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "LLM Text Generation Microservice"
    }


def test_health_check():
    """Test the health check endpoint returns all component statuses."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "service" in data
    assert "timestamp" in data
    assert "model_status" in data
    assert "consul_status" in data
    assert "metrics_status" in data


def test_metrics_endpoint():
    """Test the metrics endpoint returns Prometheus metrics."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.text  # Should contain Prometheus metrics


def test_generate_text_without_api_key():
    """Test text generation fails gracefully without API key."""
    response = client.post(
        "/generate",
        json={
            "prompt": "Test prompt",
            "max_tokens": 50,
            "temperature": 0.7
        }
    )
    assert response.status_code == 503
    assert "Model service not initialized" in response.json()["detail"]
