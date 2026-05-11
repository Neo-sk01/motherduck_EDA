FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System deps for any wheels that need a compiler. Slim should already cover most.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy only what's needed to install
COPY pyproject.toml ./
COPY pipeline ./pipeline
COPY README.md ./

RUN pip install -e .

# Default DATA_DIR inside the container (ephemeral)
ENV DATA_DIR=/data
RUN mkdir -p /data/reports

ENTRYPOINT ["python", "-m", "pipeline.azure_run"]
