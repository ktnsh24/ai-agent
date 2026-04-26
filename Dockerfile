FROM python:3.12-slim

# Install Poetry
RUN pip install --no-cache-dir poetry

WORKDIR /app

# Copy dependency files first (Docker layer caching)
COPY pyproject.toml poetry.lock* README.md ./
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi --no-root

# Copy source code
COPY src/ src/

# Create data directory for SQLite
RUN mkdir -p data

EXPOSE 8200

CMD ["uvicorn", "src.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8200"]
