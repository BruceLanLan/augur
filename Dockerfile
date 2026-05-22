# Augur - Multi-agent Investment Analysis System
# Docker image for running dashboard, API, bots, and MCP server

# --- Build stage ---
FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir --prefix=/install .

# --- Runtime stage ---
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages
COPY --from=builder /install /usr/local

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY skills/ ./skills/
COPY personas/ ./personas/
COPY dashboard/ ./dashboard/
COPY scanner/ ./scanner/
COPY docs/ ./docs/

# Create augur config directory
RUN mkdir -p /root/.augur

# Environment variables
ENV PYTHONPATH=/app/src
ENV AUGUR_CONFIG=/app/config/agents.yaml

# Expose ports
EXPOSE 8000 8900

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Default: start dashboard
CMD ["augur", "api", "--port", "8000", "--host", "0.0.0.0"]
