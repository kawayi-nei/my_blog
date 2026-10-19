# 个人博客设计文档

- 日期：2026-10-19
- 状态：已确认
- 项目目录：`Z:\my_blog`

## 1. 目标与范围

### 1.1 目标

构建一个以作品集为主、写作为辅的个人站点，同时作为 Next.js + FastAPI + PostgreSQL + nginx 的全栈学习项目。

### 1.2 成功标准

- 本机可同时运行 Next.js 与 FastAPI，浏览器完成浏览、登录、发文、评论、搜索等主流程。
- 后台可管理文章、项目、标签、评论、图片。
- 站点支持中文/英文界面切换，项目内容双语，文章保留原文语言。
- 可在 Linux VPS 上通过 nginx + systemd 上线。
- 后端核心接口有自动化测试，前端主流程有 Playwright 测试。

### 1.3 非目标

- 多作者、访客注册、复杂权限系统。
- 邮件通知、点赞、收藏、第三方统计。
- 独立的全文搜索引擎（如 Elasticsearch/Meilisearch）。
- Docker 部署（本机 Windows 10 版本较旧，采用原生进程）。
- RSS 订阅（后续可加）。

## 2. 技术栈

| 层 | 选型 |
|---|---|
| 前端 | Next.js（App Router）+ TypeScript + Tailwind CSS |
| 国际化 | next-intl |
| Markdown | react-markdown + remark-gfm + rehype-highlight |
| 表单 | React Hook Form + Zod |
| 后端 | FastAPI + Pydantic v2 |
| ORM/迁移 | SQLAlchemy 2.0（async）+ asyncpg + Alembic |
| 数据库 | PostgreSQL 17 |
| 鉴权 | PyJWT（HS256）+ httpOnly Cookie + Argon2（pwdlib） |
| 图片 | Pillow 校验 + 本地文件存储 |
| 测试 | pytest + pytest-asyncio + httpx；Playwright |

## 3. 总体架构

```
浏览器
  │
  ├── /            → nginx → Next.js :3000（SSR/页面）
  ├── /api/*       → nginx → FastAPI :8000（唯一业务 API）
  └── /uploads/*   → nginx → backend/uploads/（生产）
                     （开发时由 FastAPI 提供）
                     │
                     └── PostgreSQL 17
```

### 3.1 职责边界

- **Next.js**：页面渲染、SSR/SEO、界面交互、国际化文案、简历与站点配置的读取。不实现业务 API，不直接连数据库。
- **FastAPI**：全部业务逻辑、鉴权、数据访问、文件上传、搜索、统计。唯一 API 来源。
- **nginx**：TLS、按路径反向代理、静态图片服务、请求体大小限制。
- **PostgreSQL**：文章、项目、标签、评论、阅读记录、媒体元数据。

### 3.2 开发环境

- Next.js：`http://localhost:3000`
- FastAPI：`http://127.0.0.1:8000`
- Next rewrites 将 `/api/:path*` 与 `/uploads/:path*` 转发到 FastAPI，浏览器始终同源，不启用 CORS。

### 3.3 生产环境

- nginx 监听 80/443，`/api/` 转 FastAPI，`/uploads/` 指向文件目录，其余转 Next。
- FastAPI：uvicorn + systemd，监听 `127.0.0.1:8000`。
- Next：`next build` + `next start` + systemd，监听 `127.0.0.1:3000`。
- HTTPS：certbot + Let's Encrypt。

### 3.4 视觉方向

- 固定深色终端风格，不提供明暗主题切换。
- 背景使用 `#0d1117` 一类的深灰蓝，正文浅灰，强调色使用绿色/青色/紫色。
- 标题和代码使用等宽字体（JetBrains Mono / Geist Mono），中文回退到系统黑体。
- 移动端优先响应式；窄屏下导航折叠为菜单。
- 表单有可见 label，交互元素可键盘操作，图片有 alt 文本。

## 4. 页面结构

### 4.1 公开页面

| 路径 | 说明 |
|---|---|
| `/{locale}` | 首页：终端风格 Hero、精选项目、最新文章、GitHub 入口 |
| `/{locale}/projects` | 作品集列表 |
| `/{locale}/projects/[slug]` | 项目详情（按语言展示对应字段） |
| `/{locale}/posts` | 文章列表，支持标签与语言筛选 |
| `/{locale}/posts/[slug]` | 文章正文、评论、阅读量 |
| `/{locale}/tags/[tag]` | 标签筛选结果 |
| `/{locale}/search` | 站内搜索 |
| `/{locale}/resume` | 简历页，渲染 `resume.zh.md` / `resume.en.md` |
| `/{locale}/about` | 关于我，渲染 `about.zh.md` / `about.en.md` + 站点配置 |

`locale` 仅允许 `zh`、`en`。访问 `/` 重定向到 `/zh`；非法 locale 返回 404。

### 4.2 后台页面

统一前缀 `/{locale}/admin`：

- `/login`：登录页
- `/`：仪表盘（文章/项目/评论数量、阅读统计）
- `/posts`、`/posts/new`、`/posts/[id]/edit`
- `/projects`、`/projects/new`、`/projects/[id]/edit`
- `/comments`：评论审核
- `/tags`：标签管理
- `/media`：图片库

后台页面在服务端请求 `/api/auth/me`，未登录重定向到登录页。

## 5. 国际化与可变内容

### 5.1 国际化

- 路径前缀 `/zh`、`/en`。
- 界面文案：`src/messages/zh.json`、`src/messages/en.json`，由 next-intl 加载。
- 项目：数据库保存中英两套字段，公开 API 按 `locale` 返回对应语言；若对应语言的摘要/正文为空，回退到另一语言；标题必须双语。
- 文章：数据库保存 `language` 字段，正文按原文展示；列表显示语言徽标。
- 日期时间：数据库存 UTC，展示时使用 `Asia/Shanghai`。

### 5.2 可变内容不写死

| 文件 | 内容 |
|---|---|
| `src/content/site.ts` | 站点名、简介、GitHub、邮箱、社交链接、导航项 |
| `src/content/resume.zh.md` / `resume.en.md` | 简历正文 |
| `src/content/about.zh.md` / `about.en.md` | 关于页正文 |
| `src/messages/zh.json` / `en.json` | 界面文案 |

组件中不写死上述内容。数据库只存动态业务数据。

## 6. 数据模型

所有时间字段使用 `TIMESTAMPTZ`，默认 `now()`。

### 6.1 users

| 字段 | 类型 | 约束 |
|---|---|---|
| id | BIGSERIAL | PK |
| username | VARCHAR(50) | UNIQUE, NOT NULL |
| password_hash | VARCHAR(255) | NOT NULL |
| created_at | TIMESTAMPTZ | NOT NULL |

单管理员；通过种子脚本创建。

### 6.2 posts

| 字段 | 类型 | 约束 |
|---|---|---|
| id | BIGSERIAL | PK |
| slug | VARCHAR(200) | UNIQUE, NOT NULL, 小写字母/数字/连字符 |
| title | VARCHAR(200) | NOT NULL |
| excerpt | VARCHAR(500) | NOT NULL, 默认空串 |
| content_md | TEXT | NOT NULL |
| cover_url | VARCHAR(500) | NULL |
| language | VARCHAR(5) | NOT NULL, CHECK IN ('zh','en') |
| status | VARCHAR(10) | NOT NULL, CHECK IN ('draft','published') |
| published_at | TIMESTAMPTZ | NULL |
| view_count | INTEGER | NOT NULL, 默认 0 |
| created_at | TIMESTAMPTZ | NOT NULL |
| updated_at | TIMESTAMPTZ | NOT NULL |

索引：

- `UNIQUE (slug)`
- `(status, published_at DESC)`
- GIN trigram 索引：`title`、`excerpt`、`content_md`

规则：发布时若 `published_at` 为空则设为当前时间；撤回草稿保留原 `published_at`。

### 6.3 tags

| 字段 | 类型 | 约束 |
|---|---|---|
| id | BIGSERIAL | PK |
| name | VARCHAR(50) | UNIQUE, NOT NULL |
| slug | VARCHAR(50) | UNIQUE, NOT NULL |

### 6.4 post_tags

| 字段 | 类型 | 约束 |
|---|---|---|
| post_id | BIGINT | FK posts(id) ON DELETE CASCADE |
| tag_id | BIGINT | FK tags(id) ON DELETE CASCADE |

联合主键 `(post_id, tag_id)`。

### 6.5 projects

| 字段 | 类型 | 约束 |
|---|---|---|
| id | BIGSERIAL | PK |
| slug | VARCHAR(200) | UNIQUE, NOT NULL |
| title_zh | VARCHAR(200) | NOT NULL |
| title_en | VARCHAR(200) | NOT NULL |
| summary_zh | VARCHAR(500) | NOT NULL, 默认空串 |
| summary_en | VARCHAR(500) | NOT NULL, 默认空串 |
| content_md_zh | TEXT | NOT NULL, 默认空串 |
| content_md_en | TEXT | NOT NULL, 默认空串 |
| cover_url | VARCHAR(500) | NULL |
| tech_stack | TEXT[] | NOT NULL, 默认空数组 |
| repo_url | VARCHAR(500) | NULL |
| demo_url | VARCHAR(500) | NULL |
| started_on | DATE | NULL |
| ended_on | DATE | NULL |
| featured | BOOLEAN | NOT NULL, 默认 false |
| sort_order | INTEGER | NOT NULL, 默认 0 |
| status | VARCHAR(10) | NOT NULL, CHECK IN ('draft','published') |
| created_at | TIMESTAMPTZ | NOT NULL |
| updated_at | TIMESTAMPTZ | NOT NULL |

索引：

- `UNIQUE (slug)`
- `(status, featured DESC, sort_order ASC, started_on DESC)`

### 6.6 comments

| 字段 | 类型 | 约束 |
|---|---|---|
| id | BIGSERIAL | PK |
| post_id | BIGINT | FK posts(id) ON DELETE CASCADE |
| nickname | VARCHAR(50) | NOT NULL |
| content | VARCHAR(1000) | NOT NULL |
| status | VARCHAR(10) | NOT NULL, CHECK IN ('pending','approved','rejected') |
| ip_hash | VARCHAR(64) | NOT NULL |
| created_at | TIMESTAMPTZ | NOT NULL |

索引：`(post_id, status, created_at DESC)`。

不收集邮箱，不存原始 IP。

### 6.7 post_views

| 字段 | 类型 | 约束 |
|---|---|---|
| id | BIGSERIAL | PK |
| post_id | BIGINT | FK posts(id) ON DELETE CASCADE |
| visitor_hash | VARCHAR(64) | NOT NULL |
| viewed_on | DATE | NOT NULL |
| created_at | TIMESTAMPTZ | NOT NULL |

约束：`UNIQUE (post_id, visitor_hash, viewed_on)`；索引 `(viewed_on)`。

### 6.8 media

| 字段 | 类型 | 约束 |
|---|---|---|
| id | BIGSERIAL | PK |
| filename | VARCHAR(255) | UNIQUE, NOT NULL |
| original_name | VARCHAR(255) | NOT NULL |
| mime | VARCHAR(100) | NOT NULL |
| size_bytes | INTEGER | NOT NULL |
| created_at | TIMESTAMPTZ | NOT NULL |

## 7. API 设计

统一前缀 `/api`。错误响应使用 FastAPI 默认结构：`{"detail": "..."}`。日期为 ISO 8601 UTC。

### 7.1 认证

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/auth/login` | 请求 `{username, password}`；成功设置 `access_token` Cookie |
| POST | `/api/auth/logout` | 清除 Cookie |
| GET | `/api/auth/me` | 返回 `{username}`；未登录 401 |

Cookie 属性：`httpOnly=true`、`SameSite=Lax`、`Path=/`、生产环境 `Secure=true`、有效期 7 天。

### 7.2 公开文章

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/posts` | 查询参数 `page`（默认 1）、`page_size`（默认 10，最大 50）、`tag`（标签 slug）、`language`（`zh`/`en`） |
| GET | `/api/posts/{slug}` | 已发布文章详情，含标签和已审核评论数 |
| POST | `/api/posts/{slug}/view` | 阅读计数；按访客+日期去重 |

列表响应：

```json
{
  "items": [
    {
      "slug": "fastapi-first-api",
      "title": "用 FastAPI 写第一个接口",
      "excerpt": "...",
      "cover_url": null,
      "language": "zh",
      "published_at": "2026-10-19T10:00:00Z",
      "view_count": 12,
      "tags": [{"name": "后端", "slug": "backend"}]
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 10
}
```

仅返回 `status='published'`，按 `published_at DESC` 排序。

### 7.3 标签

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/tags` | 返回 `[{name, slug, post_count}]` |

### 7.4 项目

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/projects` | 查询参数 `featured`、`locale`（默认 `zh`）；仅已发布 |
| GET | `/api/projects/{slug}` | 查询参数 `locale`；返回本地化后的标题/摘要/正文 |

本地化回退：请求语言字段为空时使用另一语言；标题必须双语，不回退。

### 7.5 评论

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/posts/{slug}/comments` | 仅返回 `approved`，按时间正序，最多最近 200 条 |
| POST | `/api/posts/{slug}/comments` | 请求 `{nickname, content, website}`；`website` 为蜜罐字段，非空直接丢弃 |

返回 `201 {"status": "pending"}`。频率限制：同一 IP 30 秒内最多 1 条。

### 7.6 搜索

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/search` | `q` 必填，`type` 为 `posts` 或 `projects`，`locale` 用于项目 |

最多返回 20 条。使用 `ILIKE '%q%'` 结合 `similarity()` 排序；文章按 `published_at DESC`、项目按 `featured DESC, sort_order ASC` 二次排序。

响应结构：

```json
{
  "items": [
    {
      "type": "post",
      "slug": "fastapi-first-api",
      "title": "用 FastAPI 写第一个接口",
      "excerpt": "..."
    }
  ],
  "total": 1
}
```

### 7.7 后台管理（全部需要登录）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/admin/posts` | 支持 `status`、`q`、`page`、`page_size` |
| POST | `/api/admin/posts` | 创建文章 |
| GET | `/api/admin/posts/{id}` | 文章详情 |
| PATCH | `/api/admin/posts/{id}` | 更新文章 |
| DELETE | `/api/admin/posts/{id}` | 删除文章 |
| GET | `/api/admin/projects` | 项目列表 |
| POST | `/api/admin/projects` | 创建项目 |
| GET | `/api/admin/projects/{id}` | 项目详情 |
| PATCH | `/api/admin/projects/{id}` | 更新项目 |
| DELETE | `/api/admin/projects/{id}` | 删除项目 |
| GET | `/api/admin/tags` | 标签列表 |
| POST | `/api/admin/tags` | 创建标签 |
| DELETE | `/api/admin/tags/{id}` | 删除标签（解除文章关联） |
| GET | `/api/admin/comments` | 支持 `status` 过滤 |
| PATCH | `/api/admin/comments/{id}` | 修改状态：approved/rejected |
| DELETE | `/api/admin/comments/{id}` | 删除评论 |
| POST | `/api/admin/uploads` | multipart 文件，返回 `{url, filename, mime, size}` |
| GET | `/api/admin/media` | 图片库列表 |
| DELETE | `/api/admin/media/{id}` | 删除记录与文件 |
| GET | `/api/admin/stats` | 汇总统计 |

统计响应：

```json
{
  "total_posts": 10,
  "total_projects": 4,
  "pending_comments": 2,
  "total_views": 1234,
  "top_posts": [{"slug": "...", "title": "...", "view_count": 320}],
  "views_last_30_days": [{"date": "2026-10-01", "views": 12}]
}
```

`top_posts` 返回阅读量最高的 5 篇；`views_last_30_days` 固定返回 30 个日期，缺少数据的日期补 0。后台图表用简单 SVG/CSS 绘制，不引入图表库。

## 8. 关键流程

### 8.1 登录

1. 前端提交用户名密码到 `POST /api/auth/login`。
2. 后端查询 `users`，用 Argon2 校验密码。
3. 成功签发 JWT（`sub=user_id`、`exp=7 天`），写入 httpOnly Cookie。
4. 后台页面服务端带 Cookie 请求 `/api/auth/me`；401 时重定向登录页。
5. 所有后台写操作校验登录态，并检查 `Origin` 与站点同源。

登录失败限制：同一 IP 15 分钟内最多 5 次，超出返回 429。实现为进程内计数（单 worker），生产 nginx 再加 `limit_req` 兜底。

### 8.2 密码与管理员种子

- 密码哈希：Argon2（pwdlib）。
- 种子脚本：`python -m app.scripts.create_admin`，从环境变量读取 `ADMIN_USERNAME`、`ADMIN_PASSWORD`；已存在则更新密码。
- 不提供注册接口。

### 8.3 图片上传

1. 前端选择文件，`POST /api/admin/uploads`。
2. 后端校验扩展名与 MIME，使用 Pillow 验证真实图片格式。
3. 限制 5 MB；允许 jpg/jpeg/png/webp/gif。
4. 使用 UUID 生成文件名，保存到 `uploads/YYYY/MM/`。
5. 写入 `media` 表，返回 `/uploads/YYYY/MM/<uuid>.<ext>`。
6. 开发环境由 FastAPI 挂载 `/uploads`；生产由 nginx `alias` 提供并设置缓存头。

### 8.4 评论

1. 访客提交昵称、内容、蜜罐字段。
2. 蜜罐非空直接返回 201 但不入库。
3. 计算 `ip_hash = sha256(ip + IP_HASH_SALT)`。
4. 频率限制通过后写入 `comments`，状态 `pending`。
5. 后台审核为 `approved` 或 `rejected`。
6. 公开接口只返回 `approved`。

### 8.5 阅读统计

1. 文章详情页加载后，前端调用 `POST /api/posts/{slug}/view`。
2. 若请求没有 `visitor_id` Cookie，后端生成 UUID 并设置（httpOnly、1 年）。
3. 计算 `visitor_hash = sha256(visitor_id + IP_HASH_SALT)`；Cookie 不可用时回退为 IP+UA 哈希。
4. 尝试插入 `post_views`；命中唯一约束则视为重复，不再累加。
5. 插入成功时执行 `posts.view_count = view_count + 1`。
6. 后台统计按 `viewed_on` 聚合近 30 天。

### 8.6 搜索

- 文章：匹配 `title`、`excerpt`、`content_md`。
- 项目：按 `locale` 匹配对应语言的 `title`、`summary`、`content_md`。
- 查询词去除首尾空白，长度 1–100；空查询返回空结果。
- 使用参数化查询，禁止拼接 SQL。

### 8.7 Markdown

- 后端只存 Markdown 原文，不做 HTML 渲染。
- 前端使用 `react-markdown` + `remark-gfm` + `rehype-highlight`。
- 不启用 `rehype-raw`，原始 HTML 不渲染，避免 XSS。
- 后台编辑器：左 textarea、右实时预览；工具栏提供图片上传并插入 `![alt](url)`。

## 9. 错误处理、安全与 SEO

### 9.1 错误处理

- 后端：401 未登录、403 无权限、404 不存在、409 冲突（slug 重复）、422 参数校验、429 频率限制、500 未预期错误。
- 前端：全局 error boundary、404 页面、加载态、空状态；表单展示 422 字段错误；写操作失败显示 toast。

### 9.2 安全

- 所有查询使用 SQLAlchemy 参数化。
- 密码 Argon2；JWT 密钥从环境变量读取，不写死。
- Cookie httpOnly + SameSite=Lax + 生产 Secure。
- 后台写操作校验 Origin。
- 上传文件重命名、限制类型与大小、Pillow 复验。
- Markdown 不渲染原始 HTML。
- 不在日志中记录密码、Cookie、原始 IP。
- `.env` 不入库；提供 `.env.example`。

### 9.3 SEO

- 每个页面通过 Next Metadata API 输出 title、description、Open Graph。
- 文章/项目详情页输出 canonical URL。
- 生成 `sitemap.xml` 与 `robots.txt`。
- 公开页面服务端渲染，保证可抓取。

## 10. 测试策略

### 10.1 后端

- 使用独立数据库 `my_blog_test`，每个测试在事务中执行并回滚。
- pytest + pytest-asyncio + httpx AsyncClient。
- 覆盖：
  - 健康检查
  - 登录成功/失败、未登录访问后台
  - 文章 CRUD、slug 冲突、发布/草稿过滤
  - 项目 CRUD 与本地化回退
  - 标签关联
  - 评论提交、蜜罐、审核后可见
  - 阅读去重
  - 搜索
  - 上传类型/大小校验

### 10.2 前端

- Playwright 覆盖四条主流程：
  1. 浏览首页 → 项目详情
  2. 浏览文章列表 → 文章详情
  3. 登录后台 → 创建并发布文章 → 前台可见
  4. 提交评论 → 后台审核 → 前台可见
- 测试数据通过后端种子脚本或 API 准备。

### 10.3 手工验收

- 本机同时启动前后端，按第 15 节清单逐项检查。

## 11. 部署方案

### 11.1 服务器

- Ubuntu 22.04/24.04 VPS，1–2 GB 内存。
- Node.js 22 LTS、Python 3.12、PostgreSQL 17、nginx、certbot。

### 11.2 进程

- `myblog-api.service`：uvicorn，`--host 127.0.0.1 --port 8000 --workers 1`。
- `myblog-web.service`：`npm run start -- -p 3000`，绑定 127.0.0.1。
- 单 worker 与进程内频率限制一致；如需多 worker，需把限流迁移到 nginx 或数据库。

### 11.3 nginx

- `location /api/` → `http://127.0.0.1:8000`
- `location /uploads/` → `alias /srv/my_blog/backend/uploads/;`
- `location /` → `http://127.0.0.1:3000`
- `client_max_body_size 6m;`
- 对 `/api/auth/login` 与评论接口加 `limit_req`。
- certbot 自动配置 HTTPS 与跳转。

### 11.4 配置与备份

- 后端 `.env`：`DATABASE_URL`、`JWT_SECRET`、`JWT_EXPIRE_DAYS`、`ADMIN_USERNAME`、`ADMIN_PASSWORD`、`UPLOAD_DIR`、`IP_HASH_SALT`、`COOKIE_SECURE`、`SITE_ORIGIN`。
- 前端 `.env.local`：`API_BASE_URL`（服务端请求）、`NEXT_PUBLIC_SITE_URL`。
- 数据库备份：`pg_dump` 每日 cron，保留 7 天。
- 图片备份：同步 `backend/uploads/`。

## 12. 目录结构

```
my_blog/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/            # 配置、安全
│   │   ├── db/              # 引擎、会话、Base
│   │   ├── models/          # SQLAlchemy 模型
│   │   ├── schemas/         # Pydantic 模型
│   │   ├── api/             # public/、admin/、deps.py
│   │   ├── services/        # 业务逻辑
│   │   └── scripts/         # 种子脚本
│   ├── alembic/
│   ├── tests/
│   ├── uploads/
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/[locale]/    # 公开页面与 admin
│   │   ├── components/
│   │   ├── lib/             # API 封装、工具
│   │   ├── content/         # site.ts、简历、关于
│   │   └── messages/        # zh.json、en.json
│   ├── e2e/
│   ├── .env.local.example
│   └── package.json
├── deploy/
│   ├── nginx.conf
│   ├── myblog-api.service
│   ├── myblog-web.service
│   └── README.md
├── docs/superpowers/specs/
└── README.md
```

## 13. 实施顺序

1. **后端骨架**：配置、数据库会话、健康检查、Alembic 初始迁移（users/posts/tags/post_tags）。
2. **认证**：管理员种子脚本、登录/登出/me、Cookie 鉴权。
3. **文章只读闭环**：公开列表/详情 API + Next 脚手架 + 深色站点壳 + 首页/文章页。
4. **后台文章管理**：CRUD、Markdown 编辑器、图片上传。
5. **作品集**：项目 CRUD、双语字段、列表/详情页、首页精选。
6. **标签与搜索**：标签管理、筛选、pg_trgm 搜索页。
7. **评论**：提交、蜜罐、频率限制、后台审核、前台展示。
8. **阅读统计**：去重计数、后台仪表盘图表。
9. **双语完善**：所有界面文案、简历页、关于页、SEO 元数据。
10. **测试与部署**：pytest、Playwright、nginx/systemd 配置、上线文档。

每个阶段完成后运行对应测试并手工验证，再进入下一阶段。

## 14. 风险与应对

| 风险 | 应对 |
|---|---|
| Windows 开发环境与 Linux 生产路径不同 | 所有路径走环境变量；上传目录可配置；部署文档注明 Linux 路径 |
| Y 盘安装 PostgreSQL，服务账户权限异常 | 已确认 Y 盘为本地 NTFS；若服务启动失败，将数据目录迁到 C 盘 |
| 中文全文搜索效果有限 | v1 使用 pg_trgm + ILIKE；数据量增大后再评估 Meilisearch |
| 匿名评论垃圾信息 | 蜜罐 + 频率限制 + 默认待审核 + nginx 限流 |
| 进程内限流在重启后清零 | 单 worker 场景可接受；生产 nginx 兜底 |
| Next/FastAPI 版本升级带来破坏性变更 | 锁定 `package-lock.json` 与 `requirements.txt` 版本；升级前跑测试 |
| 图片占用磁盘 | 限制 5 MB，后台可删除；后续可接对象存储 |

## 15. 验收清单

- [ ] 本机 `http://localhost:3000` 可访问首页、作品集、文章、简历、关于、搜索。
- [ ] 中英文界面切换正常，项目内容随语言切换。
- [ ] 后台登录成功/失败提示正确，未登录访问后台会跳转登录页。
- [ ] 文章可创建、编辑、发布、撤回、删除；前台只显示已发布。
- [ ] 项目可创建双语内容并展示。
- [ ] 标签可管理，文章可按标签筛选。
- [ ] 搜索能返回文章与项目结果。
- [ ] 评论提交后为待审核，审核通过后前台可见。
- [ ] 同一访客同一天重复阅读只计一次。
- [ ] 图片可上传、插入文章、在媒体库删除。
- [ ] 后端 pytest 全部通过。
- [ ] Playwright 四条主流程通过。
- [ ] nginx + systemd 配置可在 VPS 上启动并通过 HTTPS 访问。
