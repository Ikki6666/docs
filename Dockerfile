FROM node:22-bookworm

WORKDIR /app

# Environment variables
ENV PATH="/root/.local/bin:${PATH}" \
    UV_LINK_MODE=copy \
    PYTHONPATH=/app \
    MINTLIFY_TELEMETRY_DISABLED=1 \
    BUILD_MODE=dynamic

ARG BUILD_MODE

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl nginx \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Python and Node dependencies first so this layer is cached.
COPY pyproject.toml uv.lock package.json package-lock.json README.md ./
COPY pipeline ./pipeline
RUN uv python install 3.13 \
    && uv sync --frozen --all-groups \
    && npm install \
    && npm install -g mint@latest

# Bring in the source and translation trees needed to build the overlay.
COPY . .

# Copy nginx config (will be used based on BUILD_MODE)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose the mint dev port (mapped to 33030 by docker-compose).
EXPOSE 3000

# Start the Chinese site dynamically: regenerate the overlay, then run
# `docs dev` (pipeline build + file watcher + mint dev on port 3000).
# Mintlify renders every .mdx on disk, including hidden integration pages,
# so no docs.json navigation patching is required.
CMD ["sh", "-c", "if [ \"$BUILD_MODE\" = \"static\" ]; then exec nginx -g 'daemon off;'; else uv run python -m scripts.zh.overlay build && uv run pipeline dev --src-dir .generated/zh/src --build-dir build; fi"]
