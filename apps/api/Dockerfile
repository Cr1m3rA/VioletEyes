# VioletEyes-neo API Dockerfile（修复  §6.1 中危：移除 ||true）

# ── Stage 1: deps + native modules ──
FROM node:20-alpine AS deps
RUN apk add --no-cache python3 make g++ libc6-compat
WORKDIR /app

# 启用 pnpm
RUN corepack enable && corepack prepare pnpm@10.0.0 --activate

# 先复制 workspace 配置以利用缓存
COPY pnpm-workspace.yaml package.json ./
COPY apps/api/package.json apps/api/
COPY packages/shared/package.json packages/shared/
COPY packages/skill-schema/package.json packages/skill-schema/
COPY packages/report-theme/package.json packages/report-theme/

RUN pnpm install --frozen-lockfile

# ── Stage 2: build ──
FROM deps AS build
WORKDIR /app
COPY . .
RUN pnpm --filter @violeteyes/api build

# ── Stage 3: runner ──
FROM node:20-alpine AS runner
RUN apk add --no-cache python3 py3-pip
WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000

# 仅复制生产依赖
COPY --from=build /app /app
RUN corepack enable && corepack prepare pnpm@10.0.0 --activate \
    && pnpm install --prod --frozen-lockfile \
    && pip3 install --break-system-packages jinja2 pyyaml pydantic

# templates 单独挂载（docker-compose 已配）
RUN mkdir -p /app/storage/code-versions /app/storage/skills /app/storage/reports

EXPOSE 3000
CMD ["sh", "-c", "node apps/api/dist/main.js"]