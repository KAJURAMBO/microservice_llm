"""Tests for the LLM Text Generation Microservice API."""

import pytest
import httpx


@pytest.mark.asyncio
async def test_health_check():
    """Test the basic health check endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "LLM Text Generation Microservice"


@pytest.mark.asyncio
async def test_root_endpoint():
    """Test the root endpoint returns correct health status."""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/")
        assert response.status_code == 200
        assert response.json() == {
            "status": "healthy",
            "service": "LLM Text Generation Microservice"
        }


@pytest.mark.asyncio
async def test_metrics():
    """Test the metrics endpoint returns Prometheus metrics."""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/metrics")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; version=0.0.4"


@pytest.mark.asyncio
async def test_generate_text_without_api_key():
    """Test text generation fails gracefully without API key."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/generate",
            json={
                "prompt": "Test prompt",
                "max_tokens": 50,
                "temperature": 0.7
            }
        )
        assert response.status_code == 500  # or 401 depending on your error handling
        assert "error" in response.json()
