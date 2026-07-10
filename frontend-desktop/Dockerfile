# ╔════════════════════════════════════════════════════════════════════════════╗
# ║       MSA AI Agent — Frontend Dockerfile (React + Vite + Nginx)          ║
# ║       Serves the React web UI on port 10080 inside the container          ║
# ║       Author: Md Sadique Amin (MSA) — V6 Ultra Pro Max                    ║
# ╚════════════════════════════════════════════════════════════════════════════╝
#
# Build context: ./frontend-desktop
# Exposed port:  10080 (mapped to host by docker-compose)
#
# Nginx proxy rules (defined in nginx.conf):
#   /socket.io/ → msa-agent:5000   (Socket.IO WebSocket)
#   /api/       → msa-agent:8000   (FastAPI REST)
#   /career/    → msa-career-api:8082
#   /gateway/   → msa-gateway:8080
#   /           → SPA fallback (index.html)

# ── Stage 1: Node builder ─────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Accept build args for Vite env injection
ARG VITE_API_URL=http://localhost:10500
ARG VITE_FASTAPI_URL=http://localhost:10800
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_FASTAPI_URL=$VITE_FASTAPI_URL

# Install dependencies first (layer cache friendly)
# --legacy-peer-deps: @monaco-editor/react@4.6 requires React 16-18 but project uses React 19
COPY package.json package-lock.json ./
RUN npm ci --legacy-peer-deps

# Copy all source files and build
COPY . .

# Build the Vite React app
RUN npm run build

# ── Stage 2: Nginx production server ─────────────────────────────────────────
FROM nginx:1.25-alpine AS runtime

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# FIX: Copy the full nginx.conf with proxy rules (Socket.IO, API, Career, Gateway)
# Previously was using an inline minimal config that missed all proxy rules.
COPY nginx.conf /etc/nginx/conf.d/msa.conf

# Copy built React app from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 10080

HEALTHCHECK --interval=20s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://localhost:10080/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
