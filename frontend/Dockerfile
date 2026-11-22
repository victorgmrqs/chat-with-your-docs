# syntax=docker/dockerfile:1
FROM node:26-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci
# Only what the Vite build reads, so editing docs or the nginx template does not rebuild the bundle.
COPY index.html vite.config.ts tsconfig*.json ./
COPY public ./public
COPY src ./src
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.31-alpine
# Mainline nginx: the 1.30 stable image still ships nginx with open CVEs (CWYD-6). Then the
# security fixes not yet in the base image (musl, zlib, expat...; CI passes a daily UPGRADE_EPOCH
# so the build cache does not keep a stale upgrade layer) and back to its unprivileged user.
ARG UPGRADE_EPOCH
USER root
RUN apk upgrade --no-cache
USER 101
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
