FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:1.27-alpine

# The frontend container keeps local-friendly defaults, but the runtime
# validation hook rejects them when WORLD_ANALYST_RUNTIME_ENV is not local.
ENV WORLD_ANALYST_RUNTIME_ENV=local
ENV WORLD_ANALYST_API_UPSTREAM=http://world-analyst-api:8080/api/v1/
ENV WORLD_ANALYST_PROXY_API_KEY=local-dev

COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY docker-entrypoint.d/30-validate-runtime-env.sh /docker-entrypoint.d/30-validate-runtime-env.sh
COPY --from=build /app/dist /usr/share/nginx/html

RUN chmod +x /docker-entrypoint.d/30-validate-runtime-env.sh \
    && sed -i 's/\r$//' /docker-entrypoint.d/30-validate-runtime-env.sh

EXPOSE 8080
