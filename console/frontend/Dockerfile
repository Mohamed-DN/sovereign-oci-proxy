# Multi-Stage Dockerfile for NeroNet Enterprise Management Console Frontend
# Stage 1: Build Vite React SPA
FROM node:22-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Stage 2: Production Nginx Server
FROM nginx:1.27-alpine AS runner
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8443
HEALTHCHECK --interval=10s --timeout=3s --retries=3 CMD wget --no-verbose --tries=1 --spider http://127.0.0.1:8443/ || exit 1
CMD ["nginx", "-g", "daemon off;"]
