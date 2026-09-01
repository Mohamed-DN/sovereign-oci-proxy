# Dockerfile for NeroNet Enterprise Management Console Backend API
FROM node:22-alpine
WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install --omit=dev

# Copy application source
COPY . .

ENV NODE_ENV=production
ENV PORT=8081
ENV HOST=0.0.0.0

EXPOSE 8081
HEALTHCHECK --interval=5s --timeout=3s --retries=5 CMD wget --no-verbose --tries=1 --spider http://127.0.0.1:8081/api/health || exit 1

CMD ["node", "server.js"]
