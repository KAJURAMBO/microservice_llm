# LLM Microservice with Groq

This microservice provides text generation capabilities using Groq LLM, with service discovery (Consul), distributed tracing (OpenTelemetry), and monitoring (Prometheus).

## Prerequisites

- Docker and Docker Compose
- Groq API key
- Python 3.11+ (for local development)

## Project Structure

```
microservice_llm/
├── microservice_llm.py        # Main FastAPI application
├── micro_service.Dockerfile   # Dockerfile for the service
├── docker-compose-micro.yaml  # Docker compose configuration
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

microservice_llm/
├── microservice_llm.py
├── micro_service.Dockerfile
├── docker-compose-micro.yaml
├── requirements.txt
├── README.md
├── tests/
│   ├── __init__.py
│   └── test_app.py
├── .gitignore
└── .github/
    └── workflows/
        └── ci-cd.yml

## Environment Variables

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your-groq-api-key
CONSUL_HOST=consul
CONSUL_PORT=8500
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
```

## Installation & Running

### Using Docker Compose (Recommended)

1. Clone the repository:
```bash
git clone <repository-url>
cd microservice_llm
```

2. Create `.env` file with your Groq API key:
```bash
echo "GROQ_API_KEY=your-groq-api-key" > .env
```

3. Build and run the services:
"docker pull consul:1.10.0"
```bash
docker-compose -f docker-compose-micro.yaml up --build    #---for builing
docker-compose -f docker-compose-micro.yaml up -d         #--for mking aup and logs also will not come in command prompt
```

### Manual Docker Build

If you prefer to build and run manually:

1. Build the Docker image:
```bash
docker build -t llm-microservice:latest -f micro_service.Dockerfile .
```

2. Create a network:
```bash
docker network create llm-network
```

3. Run the containers:
```bash
# Run Consul
docker run -d \
    --name dev-consul \
    --network llm-network \
    -p 8500:8500 \
    consul:1.10.0 agent -server -ui -node=server-1 -bootstrap-expect=1 -client=0.0.0.0

# Run OpenTelemetry Collector
docker run -d \
    --name otel-collector \
    --network llm-network \
    -p 4317:4317 \
    -p 4318:4318 \
    otel/opentelemetry-collector:latest

# Run LLM Service
docker run -d \
    --name llm-service \
    --network llm-network \
    -p 8000:8000 \
    -e GROQ_API_KEY=your-groq-api-key \
    -e CONSUL_HOST=consul \
    -e CONSUL_PORT=8500 \
    -e OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317 \
    llm-microservice:latest
```

## API Endpoints

- `GET /`: Health check endpoint
- `GET /health`: Detailed health check endpoint
- `GET /metrics`: Prometheus metrics endpoint
- `POST /generate`: Text generation endpoint

### Generate Text Example

```bash
curl -X POST "http://localhost:8000/generate" \
     -H "Content-Type: application/json" \
     -d '{
           "prompt": "Tell me a story",
           "max_tokens": 150,
           "temperature": 0.7
         }'
```

## Monitoring & Management

- Consul UI: http://localhost:8500
- FastAPI Docs: http://localhost:8000/docs
- Metrics: http://localhost:8000/metrics

## Service Components

1. **LLM Service**
   - FastAPI application
   - Groq LLM integration
   - Health checks
   - Prometheus metrics

2. **Consul**
   - Service discovery
   - Health monitoring
   - Service registry

3. **OpenTelemetry Collector**
   - Distributed tracing
   - Metrics collection
   - Observability pipeline

## Development

For local development:

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the service:
```bash
uvicorn microservice_llm:app --reload --host 0.0.0.0 --port 8000
```

## Troubleshooting

1. **Service not starting**
   - Check if all required environment variables are set
   - Verify Groq API key is valid
   - Check Docker logs: `docker logs llm-service`

2. **Consul connection issues**
   - Verify Consul is running: `docker ps`
   - Check Consul logs: `docker logs dev-consul`
   - Ensure network connectivity: `docker network inspect llm-network`

3. **OpenTelemetry issues**
   - Check collector logs: `docker logs otel-collector`
   - Verify endpoint configuration

## License

[Your License]

## Contributing

[Your Contributing Guidelines]

"""
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=your-aws-region
AWS_ACCOUNT_ID=your-aws-account-id
EC2_HOST=your-ec2-public-ip
EC2_USERNAME=ec2-user
EC2_SSH_KEY=your-private-ssh-key
GROQ_API_KEY=your-groq-api-key
CONSUL_HOST=your-consul-host
CONSUL_PORT=your-consul-port
OTEL_ENDPOINT=your-otel-endpoint"""


# Install Docker
sudo yum update -y
sudo yum install -y docker
sudo service docker start
sudo usermod -a -G docker ec2-user

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configure AWS CLI
aws configure

aws ecr create-repository --repository-name llm-microservice

mkdir -p ~/microservice_llm

#!/bin/bash
# ~/microservice_llm/deploy.sh

# Pull the latest image
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com
docker pull ${ECR_REGISTRY}/${ECR_REPOSITORY}:latest

# Stop and remove existing containers
docker-compose -f docker-compose-micro.yaml down

# Start new containers
docker-compose -f docker-compose-micro.yaml up -d

chmod +x ~/microservice_llm/deploy.sh



