# ============================================================
# Stage 1: Build Python dependencies
# ============================================================
FROM python:3.12-slim-bookworm AS python-builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ============================================================
# Stage 2: Node.js + Playwright browser (prebuilt Chromium)
# ============================================================
FROM node:18-bookworm-slim AS playwright-base

# Aliyun mirror for Debian
RUN sed -i 's|http://deb.debian.org/debian|http://mirrors.aliyun.com/debian|g' /etc/apt/sources.list.d/debian.sources \
    && sed -i 's|security.debian.org/debian-security|mirrors.aliyun.com/debian-security|g' /etc/apt/sources.list.d/debian.sources

# Install Playwright Chromium system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends --fix-missing \
    curl ca-certificates gnupg \
    libasound2 libatk-bridge2.0-0 libatk1.0-0 libcups2 libdbus-1-3 \
    libdrm2 libgbm1 libglib2.0-0 libnss3 libx11-xcb1 libxcomposite1 libxdamage1 \
    libxrandr2 libxshmfence1 libxkbcommon0 libpango-1.0-0 \
    libcairo2 libxfixes3 libxi6 libxrender1 libxss1 libegl1 \
    fonts-wqy-zenhei fonts-wqy-microhei locales \
    && localedef -i zh_CN -c -f UTF-8 -A /usr/share/locale/locale.alias zh_CN.UTF-8 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

ENV LANG=zh_CN.UTF-8 \
    LANGUAGE=zh_CN:zh \
    LC_ALL=zh_CN.UTF-8

WORKDIR /app
COPY package.json package-lock.json* ./
RUN rm -rf node_modules package-lock.json && npm install playwright@1.50.0 --force

# Install Chromium browser (system deps already installed above)
RUN npx playwright install --with-deps chromium

# ============================================================
# Stage 3: Final image — combine Python + Node/Playwright
# ============================================================
FROM python:3.12-slim-bookworm

LABEL maintainer="hermes-agent"
LABEL description="Web Page PDF & Screenshot Service (PDF/PNG/JPG/WebP)"

# Aliyun mirror
RUN sed -i 's|http://deb.debian.org/debian|http://mirrors.aliyun.com/debian|g' /etc/apt/sources.list.d/debian.sources \
    && sed -i 's|security.debian.org/debian-security|mirrors.aliyun.com/debian-security|g' /etc/apt/sources.list.d/debian.sources

# Copy Node.js + Playwright + Chromium from builder
COPY --from=playwright-base /usr/local/bin/node /usr/local/bin/node
COPY --from=playwright-base /usr/local/bin/npx /usr/local/bin/npx
COPY --from=playwright-base /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY --from=playwright-base /app/node_modules /usr/local/lib/node_modules/playwright/node_modules
COPY --from=playwright-base /root/.cache/ms-playwright /root/.cache/ms-playwright

# Copy Python deps from builder
COPY --from=python-builder /install /usr/local

# CJK fonts for Chinese text rendering + ALL Playwright Chromium system deps
RUN apt-get update && apt-get install -y --no-install-recommends --fix-missing \
    curl ca-certificates \
    libasound2 libatk-bridge2.0-0 libatk1.0-0 libcups2 libdbus-1-3 \
    libdrm2 libgbm1 libglib2.0-0 libnss3 libx11-xcb1 libxcomposite1 libxdamage1 \
    libxrandr2 libxshmfence1 libxkbcommon0 libpango-1.0-0 \
    libcairo2 libxfixes3 libxi6 libxrender1 libxss1 libegl1 \
    fonts-wqy-zenhei fonts-wqy-microhei locales \
    && localedef -i zh_CN -c -f UTF-8 -A /usr/share/locale/locale.alias zh_CN.UTF-8 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

ENV LANG=zh_CN.UTF-8 \
    LANGUAGE=zh_CN:zh \
    LC_ALL=zh_CN.UTF-8

# Create app directory
WORKDIR /app
RUN mkdir -p /app/pdf-service-output

# Copy application code
COPY pdf-service.py .

# Non-root user
RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -m -s /bin/bash appuser && \
    chown -R appuser:appuser /app

# Give appuser access to /root (browsers installed there)
RUN chmod -R 755 /root

# Ensure output directory is writable
RUN chown -R appuser:appuser /app/pdf-service-output

USER appuser

EXPOSE 8912

ENV OUTPUT_DIR=/app/pdf-service-output \
    NODE_PATH=/usr/local/lib/node_modules/playwright:/usr/local/lib/node_modules/playwright/node_modules \
    PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright \
    PATH="/usr/local/bin:${PATH}" \
    PORT=8912 \
    # --- Aliyun OSS Configuration (optional) ---
    OSS_ENABLED=false \
    OSS_ACCESS_KEY_ID="" \
    OSS_ACCESS_KEY_SECRET="" \
    OSS_BUCKET="" \
    OSS_ENDPOINT="oss-cn-shenzhen.aliyuncs.com" \
    OSS_INTERNAL_ENDPOINT="" \
    OSS_PATH_PREFIX="lab/evaluation/export"

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8912/api/health || exit 1

CMD ["python", "pdf-service.py"]
