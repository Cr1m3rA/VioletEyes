# VioletEyes-neo Web Dockerfile

FROM node:20-alpine AS build
RUN corepack enable && corepack prepare pnpm@10.0.0 --activate
WORKDIR /app

COPY pnpm-workspace.yaml package.json ./
COPY apps/web/package.json apps/web/
COPY packages/shared/package.json packages/shared/
COPY packages/report-theme/package.json packages/report-theme/

RUN pnpm install --frozen-lockfile

COPY . .
RUN pnpm --filter @violeteyes/web build

# ── Stage 2: nginx serve ──
FROM nginx:1.27-alpine AS runner
COPY --from=build /app/apps/web/dist /usr/share/nginx/html
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80