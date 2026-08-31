# Multi-stage Dockerfile for NeroNet Sovereign Mesh Enterprise Console

# ------------------------------------------------------------------------------
# Stage 1: Build React Frontend
# ------------------------------------------------------------------------------
FROM node:22-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# ------------------------------------------------------------------------------
# Stage 2: Runtime Production Image
# ------------------------------------------------------------------------------
FROM node:22-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV PORT=8081

# Install lightweight static server or backend
RUN npm install -g serve

# Copy compiled frontend assets
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Copy backend if present
COPY backend /app/backend
COPY data /app/data

# Ensure data directory exists
RUN mkdir -p /app/data

EXPOSE 8081 8082

# Start static frontend server proxying to backend
CMD ["serve", "-s", "/app/frontend/dist", "-l", "8081"]
