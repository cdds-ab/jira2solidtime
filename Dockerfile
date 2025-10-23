FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy project files (IMPORTANT: config.json with credentials is ignored via .dockerignore)
COPY pyproject.toml .
COPY src/ src/
COPY config.json.example .

# Install dependencies
RUN uv sync --frozen --no-dev

# Create data directory
RUN mkdir -p data

# Expose web port
EXPOSE 8080

# Run the application
CMD ["uv", "run", "src/jira2solidtime/main.py"]
