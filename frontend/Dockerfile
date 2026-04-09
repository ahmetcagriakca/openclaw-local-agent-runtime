# ============================================================
# Vezir Frontend — Production Multi-Stage Dockerfile
# ============================================================
# Stage 1: Node build (npm ci + vite build)
# Stage 2: Nginx serving static assets
# ============================================================

# --- Stage 1: Build ---
FROM node:20-alpine AS builder

WORKDIR /build

# Install dependencies first (layer caching)
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --ignore-scripts

# Copy source and build
COPY frontend/ ./
RUN npm run build

# --- Stage 2: Nginx Runtime ---
FROM nginx:1.27-alpine AS runtime

LABEL maintainer="AKCA <ahmetcagriakca@gmail.com>"
LABEL description="Vezir Platform Frontend — Production Image"

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Custom nginx config for SPA + API proxy
COPY frontend/nginx.conf /etc/nginx/conf.d/vezir.conf

# Copy built assets from builder
COPY --from=builder /build/dist /usr/share/nginx/html

EXPOSE 4000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1:4000/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
