FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:1.27-alpine

# Cloud Run must override these defaults because the frontend and API run as
# separate services there. Keeping local-friendly fallbacks preserves simple
# container experiments without making cloud behavior implicit.
ENV WORLD_ANALYST_API_UPSTREAM=http://world-analyst-api:8080/api/v1/
ENV WORLD_ANALYST_PROXY_API_KEY=local-dev

COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080
