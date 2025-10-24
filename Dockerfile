FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy project files (IMPORTANT: config.json with credentials is ignored via .dockerignore)
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src/ src/
COPY config.json.example ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    mkdir -p data && \
    chown -R appuser:appuser /app

# Copy and setup entrypoint
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Switch to non-root user
USER appuser

ENTRYPOINT ["docker-entrypoint.sh"]

# Health check for container monitoring
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080').read()" || exit 1

# Expose web port
EXPOSE 8080

# Run the application
CMD ["uv", "run", "python", "-m", "jira2solidtime.main"]
