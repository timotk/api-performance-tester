FROM python:3.12-slim as builder
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.3.4 /uv /bin/uv

COPY . .

# Install dependencies
RUN uv sync --frozen

CMD ["uv", "run", "streamlit", "run", "src/api_performance_tester/app.py"]
