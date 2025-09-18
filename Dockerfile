FROM python:3.12-slim

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set working directory
WORKDIR /app

# Create non-root user with matching host UID/GID
RUN groupadd -r appuser -g 1000 && useradd -r -g appuser -u 1000 appuser

# Copy dependency files and source structure
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/
COPY config/ ./config/

# Install dependencies
RUN uv sync --frozen --no-dev

# Create required directories and fix permissions
RUN mkdir -p /app/data /app/logs /metrics /home/appuser/.cache && \
    chown -R appuser:appuser /app /metrics /home/appuser

# Switch to non-root user
USER appuser

# Set environment variables
ENV PYTHONPATH=/app/src
ENV METRICS_DIR=/metrics

# Health check - simple check that app can start
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD uv run jira2solidtime --help > /dev/null || exit 1

# Default command - keep container running
CMD ["tail", "-f", "/dev/null"]