# Lightweight Docker image for jira2solidtime application only
# No monitoring services - just the core app for production deployment

FROM python:3.12-slim as builder

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock README.md ./
COPY src/ src/

# Install dependencies and build
RUN uv sync --frozen --no-dev --no-install-project
RUN uv build

# Production stage
FROM python:3.12-slim

# Create non-root user
RUN groupadd -r appuser -g 1000 && useradd -r -g appuser -u 1000 appuser

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy built wheel and install
COPY --from=builder /app/dist/*.whl ./
RUN uv pip install --system *.whl && rm *.whl

# Create directories
RUN mkdir -p /app/data /app/logs /app/config && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD jira2solidtime version || exit 1

# Default command
ENTRYPOINT ["jira2solidtime"]
CMD ["--help"]