# 项目交接说明

> 更新时间：2026-10-20
> 目的：给下一个 Claude Code 窗口快速接手。先读本文件，再读 README 和 spec。

## 1. 一句话现状

个人博客的**基础闭环（M1–M3）已完成并合并到 `master`**：

- 当前分支：`master`
- HEAD：`0a2ee4f fix: add localized not-found page`
- 工作树：干净
- 验证：后端 pytest **27 passed**；前端 Playwright **4 passed**；`npm run build` 成功
- 功能分支 `feature/foundation` 已合并并删除

## 2. 项目位置与关键文档

- 代码根目录：`Z:\my_blog`
- 使用说明：`Z:\my_blog\README.md`
- 设计规格：`Z:\my_blog\docs\superpowers\specs\2026-10-19-personal-blog-design.md`
- 基础闭环实施计划：`Z:\my_blog\docs\superpowers\plans\2026-10-19-personal-blog-foundation.md`
- 本交接文档：`Z:\my_blog\HANDOFF.md`
- 自动记忆：`C:\Users\Administrator\.claude\projects\Z--claude-code\memory\project_my-blog.md`

## 3. 本地环境

| 项 | 情况 |
|---|---|
| 系统 | Windows 10，Git Bash |
| Node / npm | Node 24.19.0 / npm 11.17.0 |
| Python | 3.12.8，venv 在 `backend/venv` |
| PostgreSQL | 17，安装在 `Y:\internet_tools\postgreSQL` |
| Windows 服务 | `postgresql-x64-17`（Automatic；曾出现 Stopped，需要时启动） |
| 数据库 | 开发库 `my_blog`，测试库 `my_blog_test`，均启用 `pg_trgm` |
| Playwright | Chromium 已安装 |
| 密码/密钥 | `.env`、`.env.test`、`.env.local` 均已存在且被 gitignore；不要读取/打印/提交 |

管理员用户名是 `admin`，密码在 `backend/.env` 的 `ADMIN_PASSWORD` 中，**不要在对话里输出**。数据库用户是 `blog_user`，密码在 `.env`/`.env.test` 的 `DATABASE_URL` 中。

## 4. 架构与关键约定

```
浏览器
  ├── /          → Next.js :3000（SSR/页面）
  ├── /api/*     → FastAPI :8000（唯一业务 API）
  └── /uploads/* → FastAPI（开发）/ nginx（生产）
                     │
                     └── PostgreSQL 17
```

- **Next.js 只负责页面/SSR/SEO**；所有业务逻辑在 FastAPI，不写 Next API 路由。
- 开发时 Next rewrites 把 `/api/*` 和 `/uploads/*` 代理到 `http://127.0.0.1:8000`。
- 服务端组件通过 `frontend/src/lib/api.ts`（`server-only`）直接请求 `API_BASE_URL`。
- 生产计划：nginx + systemd 原生进程，`/api` 和 `/uploads` 由 nginx 分流。
- 双语路径 `/zh`、`/en`，`localeDetection: false`，`/` 固定跳 `/zh`。
- 界面文案：`frontend/src/messages/{zh,en}.json`
- 站点可变内容：`frontend/src/content/site.ts`（GitHub/email 仍是占位值）
- 深色终端风格：`frontend/src/app/globals.css`，固定深色，不做明暗切换。

## 5. 已完成内容（M1–M3）

### 后端

- FastAPI 骨架、pydantic-settings 配置、健康检查
- SQLAlchemy 2 async + asyncpg + Alembic
- 表：`users`、`posts`、`tags`、`post_tags`
- 迁移 `0001_initial`：CHECK 约束、`pg_trgm` GIN 索引、级联删除
- 管理员种子：`python -m app.scripts.create_admin`
- 认证：
  - Argon2 密码哈希
  - JWT HS256，httpOnly Cookie，SameSite=Lax，7 天
  - 登录失败限流 5 次 / 15 分钟（进程内，单 worker）
  - `ADMIN_ENABLED` 开关
- 公开 API：
  - `GET /api/health`
  - `GET /api/posts`（分页、tag、language 过滤、稳定排序）
  - `GET /api/posts/{slug}`（只返回已发布，草稿 404）
  - `GET /api/tags`（只统计已发布文章）
  - `GET /api/site/config`
  - `POST /api/auth/login`、`POST /api/auth/logout`、`GET /api/auth/me`
- 演示数据：`python -m app.scripts.seed_demo`（upsert `first-post`）

### 前端

- Next.js 16.4.2 App Router + TypeScript + Tailwind v4 + next-intl 4
- `src/proxy.ts`（Next 16 的 middleware 入口）
- `src/app/[locale]/layout.tsx` 作为 root layout
- 页头：文章入口、GitHub、语言切换（保留当前路径）
- 页脚：版权
- 页面：首页、文章列表、文章详情
- Markdown：`react-markdown` + `remark-gfm` + `rehype-highlight`，不渲染原始 HTML
- 错误处理：`error.tsx`、本地化 `not-found.tsx`
- API 客户端：`ApiError`、`getPostOrNull`（只有 404 才返回 null）

### 测试

- 后端：pytest + httpx，27 passed
  - 测试库 `my_blog_test`，每测试 drop/create
  - 迁移冒烟测试检查表/CHECK/索引
  - 有防呆：URL 必须以 `/my_blog_test` 结尾
- 前端：Playwright 4 passed
  - 首页、文章列表+详情、语言切换、404 壳层
  - Playwright 自动启动/复用 FastAPI 与 Next
  - globalSetup 先 `alembic upgrade head` 再 `seed_demo`

## 6. 尚未完成（后续计划）

### 计划 2：后台管理

- 管理员登录页面和后台布局
- 文章 CRUD、草稿/发布、Markdown 编辑器（左编辑右预览）
- 图片上传、媒体库
- 后台入口根据 `/api/site/config` 显示/隐藏
- 后台写操作的 Origin 校验
- 目前 `/api/admin/*` 和后台页面都还不存在

### 计划 3：作品集与互动

- 项目表、双语项目 CRUD、项目列表/详情、首页精选
- 标签管理、标签筛选、站内搜索（`pg_trgm`）
- 评论提交、蜜罐、频率限制、后台审核
- 阅读统计：`post_views` 去重、`view_count`、后台统计
- 简历页、关于页（内容放 `src/content/resume.zh.md` / `about.zh.md` 等）

### 计划 4：完善与上线

- 双语元数据（当前 `/en` 仍是中文 title/description）
- `sitemap.xml`、`robots.txt`、Open Graph
- 窄屏导航折叠
- nginx + systemd 配置、HTTPS、备份
- 生产环境变量、`COOKIE_SECURE=true`
- 评估移除 `@swc/core` override
- 语言切换保留 query/hash（分页页切换语言会回第 1 页）
- 限流 key 清理/多 worker 方案

## 7. 已知问题与注意事项

- `frontend/src/content/site.ts` 的 GitHub/email 是占位值，上线前必须替换。
- E2E 使用**开发库** `my_blog`，并 upsert `first-post`；不要拿它跑重要数据。
- pytest 会删除/重建 `my_blog_test` 的表，测试结束后测试库保持空结构。
- PostgreSQL 服务可能 Stopped，先运行 `Start-Service postgresql-x64-17`。
- `@swc/core` 在 `frontend/package.json` 里被 pin 到 `1.16.0`，是本机 Windows ACL 导致 `ERR_SWC_NATIVE_CACHE` 的 workaround；升级 next-intl 或修复 ACL 后可移除。
- `API_BASE_URL` 被 `next.config.ts` 在 **build 时**读取并固化；`src/lib/api.ts` 在服务端运行时也读取它。
- 限流是进程内实现，生产单 uvicorn worker，nginx `limit_req` 作为兜底。
- 还没有 `deploy/` 目录。
- 还没有后台 UI，`getSiteConfig()` 暂时未被页面使用。

## 8. 常用命令

### 启动 PostgreSQL（PowerShell）

```powershell
Start-Service postgresql-x64-17
```

### 后端

```bash
cd "Z:/my_blog/backend"
"venv/Scripts/python.exe" -m alembic upgrade head
"venv/Scripts/python.exe" -m app.scripts.create_admin
"venv/Scripts/python.exe" -m app.scripts.seed_demo
"venv/Scripts/python.exe" -m uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd "Z:/my_blog/frontend"
npm run dev
```

打开 `http://localhost:3000/zh`。

### 测试

```bash
cd "Z:/my_blog/backend"
"venv/Scripts/python.exe" -m pytest -q

cd "Z:/my_blog/frontend"
npm run build
npm run test:e2e
```

## 9. 建议的接手方式

1. 先读本文件、`README.md`、设计 spec 和基础闭环计划。
2. 新功能先走 brainstorming → 写 spec → 写实施计划，再实现。
3. 实现用子代理驱动，每个任务一个实现子代理 + 规格审查 + 质量审查；用户偏好并行审查/验证，但同一工作树的写操作要串行。
4. 在功能分支上开发，测试通过后再合并 master；不要直接在 master 上改。
5. 每次给用户命令时，附一句用途/原理说明。
6. 不要输出或提交 `.env`、`.env.test`、`.env.local` 里的真实密钥。
