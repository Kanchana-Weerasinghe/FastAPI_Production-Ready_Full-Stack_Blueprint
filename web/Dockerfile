# syntax=docker/dockerfile:1.7
# Static SPA served by unprivileged nginx (UID 101, port 8080), compatible with a read-only root
# filesystem when /tmp and /var/cache/nginx are writable (emptyDir in Kubernetes).

FROM node:22-alpine AS builder

# Same major version as CI (pnpm/action-setup) so the lockfile is read identically.
RUN npm install -g pnpm@10 --no-fund --no-audit

WORKDIR /app

COPY package.json pnpm-lock.yaml ./
RUN --mount=type=cache,target=/root/.local/share/pnpm/store pnpm install --frozen-lockfile

COPY . .

# Vite inlines VITE_* variables at build time; build one image per API origin
# (or serve the API under the same origin and leave it empty).
ARG VITE_API_URL=""
ARG VITE_SENTRY_DSN=""
ARG APP_VERSION=0.0.0-dev
ENV VITE_API_URL=${VITE_API_URL} \
    VITE_SENTRY_DSN=${VITE_SENTRY_DSN} \
    VITE_APP_VERSION=${APP_VERSION}
RUN pnpm build


FROM nginxinc/nginx-unprivileged:1.27-alpine AS runtime

ARG APP_VERSION=0.0.0-dev
LABEL org.opencontainers.image.title="web" org.opencontainers.image.version="${APP_VERSION}"

# Rendered with envsubst at start-up (API_ORIGIN feeds the Content-Security-Policy connect-src).
ENV API_ORIGIN="'self'" \
    API_UPSTREAM="http://server:8000"

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/templates/default.conf.template

EXPOSE 8080
