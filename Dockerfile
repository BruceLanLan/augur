# Augur Next — Professional Bloomberg AI Agent System
# Supports: Dashboard · REST API · MCP Server · Telegram · Slack · WeChat · Lark

# --- Build stage ---
FROM python:3.11-slim AS builder

WORKDIR /app
COPY requirements.txt pyproject.toml ./
COPY src/ ./src/
# Install all extras for full functionality
RUN pip install --no-cache-dir --prefix=/install ".[data,mcp,telegram,slack]" 2>/dev/null \
    || pip install --no-cache-dir --prefix=/install ".[data]"

# --- Runtime stage ---
FROM python:3.11-slim

LABEL org.opencontainers.image.title="Augur Next"
LABEL org.opencontainers.image.description="Professional Bloomberg AI Agent — 18 investment masters, committee mode, MCP"
LABEL org.opencontainers.image.source="https://github.com/BruceLanLan/augur-next"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

# Copy installed packages
COPY --from=builder /install /usr/local

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY skills/ ./skills/
COPY personas/ ./personas/
COPY dashboard/ ./dashboard/
COPY scripts/ ./scripts/
COPY docs/ ./docs/

# Create augur data + config directories
RUN mkdir -p /app/.augur /app/.augur/history /app/.augur/personas

# Create non-root user
RUN groupadd -r augur && useradd -r -g augur -d /app -s /sbin/nologin augur \
    && chown -R augur:augur /app

USER augur

# Environment
ENV PYTHONPATH=/app/src
ENV AUGUR_CONFIG=/app/config/agents.yaml
ENV AUGUR_DATA_DIR=/app/.augur

# Ports: 8000=Dashboard, 8900=REST API
EXPOSE 8000 8900

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Default: Dashboard
CMD ["python", "-m", "dashboard.app", "--port", "8000", "--host", "0.0.0.0"]
