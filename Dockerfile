# =====================================================
# Stage 1: Build frontend assets (Node.js)
# =====================================================
FROM node:20-alpine AS frontend

WORKDIR /build

COPY package.json package-lock.json ./
RUN npm ci

COPY postcss.config.js ./
COPY src/ ./src/
RUN npm run build

# =====================================================
# Stage 2: Build Rust extension
# =====================================================
FROM python:3.12-slim AS rust-builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cargo \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY rust_predictor/ ./rust_predictor/
RUN pip install --no-cache-dir maturin && \
    cd rust_predictor && maturin develop --release && \
    cd ..

# =====================================================
# Stage 3: Final runtime image
# =====================================================
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --from=frontend /build/static/css/app.css static/css/app.css
COPY --from=frontend /build/static/js/app.js static/js/app.js
COPY --from=frontend /build/static/js/tools.js static/js/tools.js
COPY --from=frontend /build/static/js/tools.utils.js static/js/tools.utils.js

COPY --from=rust-builder /usr/local/lib/python3.12/site-packages/rust_predictor* /usr/local/lib/python3.12/site-packages/
COPY --from=rust-builder /usr/local/lib/python3.12/site-packages/rust_predictor-*.dist-info/ /usr/local/lib/python3.12/site-packages/rust_predictor-*.dist-info/ 2>/dev/null || true

COPY . .

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/healthz')" || exit 1

CMD ["gunicorn", "app.main:app", "-c", "gunicorn_conf.py"]
