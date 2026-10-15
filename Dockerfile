FROM node:22-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM caddy:2.10-alpine

RUN apk add --no-cache python3

COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
COPY analytics /app/analytics

ENV PYTHONUNBUFFERED=1 \
    AURUM_WORKSPACE=/app \
    AURUM_INTERNAL_PORT=8000

EXPOSE 3000

ENTRYPOINT ["python3", "/app/analytics/railway_entrypoint.py"]
