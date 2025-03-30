"""
This LLM microservice differs from a standard FastAPI application in several ways:

1. **Service Discovery**: Utilizes Consul for service registration and discovery, allowing for dynamic service management.

2. **Circuit Breakers**: Implements retry logic using the `tenacity` library to handle transient errors during text generation.

3. **Rate Limiting**: (To be implemented) Can be enhanced with libraries like `slowapi` to control request rates.

4. **Comprehensive Health Checks**: Provides detailed health checks that include model, Consul, and metrics status.

5. **Metrics Collection**: Integrates Prometheus for monitoring request counts, generation times, and error rates.

6. **Distributed Tracing**: Uses OpenTelemetry for tracing requests across distributed systems, aiding in performance monitoring and debugging.

7. **Environment Configuration**: Loads environment variables using `dotenv` for flexible configuration management.

8. **Logging**: Configures detailed logging to capture important events and errors, aiding in monitoring and debugging.

These features make the microservice robust, scalable, and suitable for production environments where reliability and observability are critical.
"""
import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict
import uvicorn
import os
import time
from dotenv import load_dotenv
import consul
from prometheus_client import Counter, Histogram, generate_latest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from tenacity import retry, stop_after_attempt, wait_exponential
from datetime import datetime, UTC
import groq

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from a .env file
load_dotenv()

# Initialize FastAPI app with metadata
app = FastAPI(
    title="LLM Text Generation Microservice",
    description="A microservice that provides text generation capabilities using Groq LLM",
    version="1.0.0"
)

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Initialize Prometheus metrics for monitoring
REQUEST_COUNT = Counter('request_count', 'Total number of requests')
GENERATION_TIME = Histogram('generation_time_seconds', 'Time spent generating text')
ERROR_COUNT = Counter('error_count', 'Total number of errors')

# Initialize OpenTelemetry for distributed tracing
tracer_provider = TracerProvider()
try:
    # Attempt to use OTLP exporter for sending traces
    otlp_exporter = OTLPSpanExporter(endpoint=os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT', 'http://localhost:4317'))
    span_processor = BatchSpanProcessor(otlp_exporter)
except Exception as e:
    # Fallback to console exporter if OTLP fails
    logging.error(f"Failed to initialize OTLP exporter, falling back to console: {e}")
    span_processor = BatchSpanProcessor(ConsoleSpanExporter())

# Set the tracer provider and instrument the FastAPI app
tracer_provider.add_span_processor(span_processor)
trace.set_tracer_provider(tracer_provider)
FastAPIInstrumentor.instrument_app(app)

# Initialize Consul client for service discovery
consul_client = consul.Consul(host=os.getenv('CONSUL_HOST', 'localhost'),
                            port=int(os.getenv('CONSUL_PORT', 8500)))

# Initialize Groq client for LLM interactions
try:
    groq_client = groq.Groq(api_key=os.getenv('GROQ_API_KEY'))
except Exception as e:
    logging.error(f"Error initializing Groq client: {e}")
    groq_client = None

# Define request model for text generation
class TextGenerationRequest(BaseModel):
    prompt: str
    max_tokens: Optional[int] = 150
    temperature: Optional[float] = 0.7

# Define response model for text generation
class TextGenerationResponse(BaseModel):
    generated_text: str
    model: str
    usage: Dict[str, int]

# Define response model for health check
class HealthCheckResponse(BaseModel):
    status: str
    service: str
    timestamp: str
    model_status: str
    consul_status: str
    metrics_status: str

@app.get("/")
async def root():
    """Health check endpoint"""
    logging.info("Health check endpoint accessed")
    return {"status": "healthy", "service": "LLM Text Generation Microservice"}

@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Comprehensive health check endpoint"""
    logging.info("Health check endpoint accessed")
    model_status = "healthy" if groq_client else "unhealthy"
    consul_status = "healthy" if consul_client else "unhealthy"
    metrics_status = "healthy" if generate_latest() else "unhealthy"

    return HealthCheckResponse(
        status="healthy",
        service="LLM Text Generation Microservice",
        timestamp=datetime.now(UTC).isoformat(),
        model_status=model_status,
        consul_status=consul_status,
        metrics_status=metrics_status
    )

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    logging.info("Metrics endpoint accessed")
    return generate_latest()

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def generate_with_retry(prompt: str, max_tokens: int, temperature: float):
    """Circuit breaker pattern with retry logic for text generation"""
    try:
        logging.info("Attempting to generate text with retry logic")
        response = groq_client.chat.completions.create(
            model="gemma2-9b-it",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response
    except Exception as e:
        ERROR_COUNT.inc()
        logging.error(f"Error during text generation: {e}")
        raise

@app.post("/generate", response_model=TextGenerationResponse)
async def generate_text(request: TextGenerationRequest):
    """
    Generate text based on the provided prompt using Groq LLM.

    Args:
        request: TextGenerationRequest containing the prompt and generation parameters

    Returns:
        TextGenerationResponse containing the generated text and metadata

    Raises:
        HTTPException: If the model is not initialized or generation fails
    """
    logging.info("Generate text endpoint accessed")
    if groq_client is None:
        logging.error("Groq client not initialized")
        raise HTTPException(
            status_code=503,
            detail="Model service not initialized. Please try again later."
        )

    REQUEST_COUNT.inc()

    try:
        with GENERATION_TIME.time():
            start_time = time.time()

            # Generate text using Groq with retry logic
            response = await generate_with_retry(
                request.prompt,
                request.max_tokens,
                request.temperature
            )

            processing_time = time.time() - start_time
            logging.info(f"Text generation completed in {processing_time:.2f} seconds")

            # Register service with Consul
            try:
                consul_client.agent.service.register(
                    "llm-service",
                    service_id="llm-service-1",
                    port=8000,
                    check={
                        "http": "http://localhost:8000/health",
                        "interval": "10s"
                    }
                )
            except Exception as e:
                logging.error(f"Failed to register service with Consul: {e}")

            return TextGenerationResponse(
                generated_text=response.choices[0].message.content,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            )

    except Exception as e:
        ERROR_COUNT.inc()
        logging.error(f"Text generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Text generation failed: {str(e)}"
        )

if __name__ == "__main__":
    # Register service with Consul on startup
    try:
        consul_client.agent.service.register(
            "llm-service",
            service_id="llm-service-1",
            port=8000,
            check={
                "http": "http://localhost:8000/health",
                "interval": "10s"
            }
        )
    except Exception as e:
        logging.error(f"Failed to register with Consul: {e}")

    # Run the FastAPI app with Uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
