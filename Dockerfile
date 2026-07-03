FROM node:22-bookworm AS builder

WORKDIR /app

ENV PATH="/root/.local/bin:${PATH}" \
    UV_LINK_MODE=copy \
    MINTLIFY_TELEMETRY_DISABLED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

COPY pyproject.toml uv.lock package.json package-lock.json README.md ./
COPY pipeline ./pipeline
RUN uv python install 3.13 \
    && uv sync --frozen --all-groups \
    && npm install \
    && npm install -g mint@latest

COPY . .

RUN uv run python -m scripts.zh.overlay build \
    && PYTHONPATH=/app uv run pipeline build --src-dir .generated/zh/src --build-dir build

FROM node:22-slim AS runtime

WORKDIR /site

ENV NODE_ENV=production \
    PORT=3000 \
    MINTLIFY_TELEMETRY_DISABLED=1

RUN npm install -g mint@latest

COPY --from=builder /app/build/ ./

EXPOSE 3000

CMD ["mint", "dev", "--port", "3000", "--no-open"]
