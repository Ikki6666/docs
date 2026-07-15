FROM node:22-bookworm

WORKDIR /app

# mint dev serves on port 3000; the container is meant to be run dynamically.
ENV PATH="/root/.local/bin:${PATH}" \
    UV_LINK_MODE=copy \
    PYTHONPATH=/app \
    MINTLIFY_TELEMETRY_DISABLED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
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

# Expose the mint dev port (mapped to 33030 by docker-compose).
EXPOSE 3000

# Start the Chinese site dynamically: regenerate the overlay, then run
# `docs dev` (pipeline build + file watcher + mint dev on port 3000).
# mint dev renders every .mdx on disk, including hidden integration pages,
# so no docs.json navigation patching is required.
CMD ["sh", "-c", "uv run python -m scripts.zh.overlay build && uv run pipeline dev --src-dir .generated/zh/src --build-dir build"]
