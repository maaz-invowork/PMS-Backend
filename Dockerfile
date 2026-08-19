FROM python:3.12-slim

# Copy uv binary from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency definition files
COPY pyproject.toml uv.lock README.md* ./

# 1. Install third-party dependencies ONLY (enables Docker layer caching)
RUN uv sync --frozen --no-cache --no-dev --no-install-project

# 2. Copy application source code
COPY src ./src
COPY .env* ./

# 3. Install the root project now that src/ is present
RUN uv sync --frozen --no-cache --no-dev

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "project_management_system.main:app", "--host", "0.0.0.0", "--port", "8000"]