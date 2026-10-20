# 计划 2：后台文章管理设计

- 日期：2026-10-20
- 状态：已确认
- 分支：`feature/admin-posts`
- 上游设计：`docs/superpowers/specs/2026-10-19-personal-blog-design.md`

## 1. 背景与目标

基础闭环（M1–M3）已完成并合并 `master`。本阶段实现后台文章管理闭环：

- 管理员登录页与后台布局；
- 文章列表、新建、编辑、草稿/发布、删除；
- Markdown 编辑器（左编辑右预览）与正文图片上传；
- 媒体库（列表、上传、删除）；
- 后台接口鉴权、`ADMIN_ENABLED` 开关与 Origin 校验。

完成后，管理员可以在浏览器内完成「登录 → 写文章 → 发布 → 前台可见」的完整流程。

## 2. 范围

### 2.1 包含

- 后端 `/api/admin/posts` CRUD、`/api/admin/tags` 最小集、`/api/admin/uploads`、`/api/admin/media`；
- `media` 表与迁移；
- 前端后台登录、文章列表、新建/编辑、媒体库；
- 公开页头按开关显示后台入口；
- 后端 pytest 与 Playwright 主流程测试。

### 2.2 不包含（留给计划 3/4）

- 后台仪表盘与 `/api/admin/stats`；
- 封面图选择与前台封面展示；
- 项目、评论、搜索、阅读统计；
- 标签管理页（删除/改名）；
- 简历/关于页、SEO、nginx/systemd 部署。

## 3. 总体方案

采用「服务端读 + 客户端写」：

- 后台页面为 Server Component，服务端带 Cookie 请求 FastAPI；
- 登录、编辑器、删除等交互为 Client Component，同源 `fetch('/api/admin/*')`；
- Next.js 不实现业务 API，FastAPI 仍是唯一业务 API 来源。

## 4. 后端设计

### 4.1 鉴权与 Origin 校验

`app/api/deps.py` 新增两个依赖：

- `require_admin`
  - `ADMIN_ENABLED=false` → **404**（不暴露后台存在）；
  - 无 Cookie、无效/过期 Token、用户不存在 → **401**；
  - 与现有 `get_current_user` 的区别：`/api/auth/me` 在关闭后台时仍保持 401。
- `require_same_origin`
  - 只检查 POST/PATCH/PUT/DELETE；
  - 要求 `Origin` 头存在且等于 `SITE_ORIGIN`，否则 **403**；
  - GET 不检查；
  - 比较前统一去掉末尾 `/`，不做通配。

`main.py` 以 `/api/admin` 前缀挂载 admin 路由，并统一附加这两个依赖。测试与 curl 调用写操作时必须显式发送 `Origin`。

### 4.2 文章 API

路由：`app/api/admin/posts.py`，前缀 `/api/admin/posts`。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/admin/posts` | `status`（draft/published）、`q`（标题/摘要 ILIKE）、`page`、`page_size`（默认 10，最大 50） |
| POST | `/api/admin/posts` | 创建，201 |
| GET | `/api/admin/posts/{id}` | 详情，404 |
| PATCH | `/api/admin/posts/{id}` | 部分更新 |
| DELETE | `/api/admin/posts/{id}` | 硬删除，204 |

列表响应：

```json
{
  "items": [
    {
      "id": 1,
      "slug": "first-post",
      "title": "第一篇测试文章",
      "excerpt": "摘要",
      "language": "zh",
      "status": "published",
      "published_at": "2026-10-20T10:00:00Z",
      "updated_at": "2026-10-20T10:00:00Z",
      "tags": [{"id": 1, "name": "后端", "slug": "backend"}]
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 10
}
```

详情额外包含 `content_md`、`created_at`。

写入字段：

- `slug`：必填，`^[a-z0-9-]+$`，最长 200，唯一；冲突 **409**；格式错误 **422**。
- `title`：1–200 字符。
- `excerpt`：最长 500，默认空串。
- `content_md`：字符串，允许为空（草稿）。
- `language`：`zh` / `en`。
- `status`：`draft` / `published`，默认 `draft`。
- `tag_ids`：整数数组，默认空；任一不存在 → **422**。

发布规则：

- 创建状态为 `published` → `published_at = now()`；
- 创建为 `draft` → `published_at = NULL`；
- `draft → published` 且原值为 `NULL` → 设为 `now()`；
- `published → draft` → 保留原 `published_at`；
- 重复发布不刷新 `published_at`。

列表排序 `updated_at DESC, id DESC`，列表查询 `defer(content_md)`。

### 4.3 标签 API（最小集）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/admin/tags` | 返回 `[{id, name, slug}]`，按名称排序 |
| POST | `/api/admin/tags` | `{name, slug}`，201；名称或 slug 冲突 409 |

slug 规则与文章一致。本阶段不提供改名/删除。

### 4.4 上传与媒体库

新增模型 `app/models/media.py` 与迁移 `0002_media`：

| 字段 | 类型 | 约束 |
|---|---|---|
| id | BIGSERIAL | PK |
| filename | VARCHAR(255) | UNIQUE, NOT NULL（相对路径 `YYYY/MM/<uuid>.<ext>`） |
| original_name | VARCHAR(255) | NOT NULL |
| mime | VARCHAR(100) | NOT NULL |
| size_bytes | INTEGER | NOT NULL |
| created_at | TIMESTAMPTZ | NOT NULL |

接口：

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/admin/uploads` | multipart `file`，返回 `{url, filename, mime, size}` |
| GET | `/api/admin/media` | 分页，按 `created_at DESC, id DESC` |
| DELETE | `/api/admin/media/{id}` | 删除记录与文件，204 |

上传规则：

- 上限 5 MB，超出 **413**；
- 扩展名白名单 jpg/jpeg/png/webp/gif；
- Pillow `verify()` 校验真实图片，格式必须属于白名单，否则 **422**；
- 存储扩展名使用 Pillow 识别出的格式，不信任原始扩展名；
- 文件名 `uuid4 + 扩展名`，目录 `UPLOAD_DIR/YYYY/MM/`，按需创建；
- 写入 `media` 行；返回 URL `/uploads/YYYY/MM/<uuid>.<ext>`；
- 删除前解析目标路径并确认位于 `UPLOAD_DIR` 内；
- Pillow 操作用 `run_in_threadpool` 执行。

`main.py` 启动时确保 `UPLOAD_DIR` 存在，并挂载 `/uploads` 静态目录。开发环境 Next rewrite 已代理 `/uploads/*`。

### 4.5 错误码约定

401 未登录、403 Origin 不匹配、404 资源不存在/后台关闭、409 slug 或标签冲突、413 文件过大、422 参数校验、429 登录限流。

## 5. 前端设计

### 5.1 路由重构

公开页迁入 `(site)` route group，URL 不变：

```text
src/app/[locale]/
├── layout.tsx                 # html/body、字体、NextIntlClientProvider
├── not-found.tsx              # 后台/全局兜底
├── (site)/
│   ├── layout.tsx             # SiteHeader + main + SiteFooter
│   ├── page.tsx
│   ├── error.tsx
│   ├── not-found.tsx          # 公开页 404（保留站点壳）
│   └── posts/
│       ├── page.tsx
│       └── [slug]/page.tsx
└── admin/
    ├── layout.tsx             # 后台外壳（不鉴权）
    ├── login/page.tsx
    └── (protected)/
        ├── layout.tsx         # 鉴权 + 后台导航
        ├── page.tsx           # redirect → posts
        ├── error.tsx
        ├── posts/
        │   ├── page.tsx
        │   ├── new/page.tsx
        │   └── [id]/edit/page.tsx
        └── media/page.tsx
```

### 5.2 后台鉴权与导航

`admin/(protected)/layout.tsx`：

1. 读取 `/api/site/config`；`admin_enabled=false` → `notFound()`；
2. 带 Cookie 请求 `/api/auth/me`；401 → `redirect('/{locale}/admin/login')`；
3. 渲染后台导航：文章、媒体库、返回站点、退出登录。

登录页在受保护布局之外，避免重定向循环；已登录访问登录页则跳转文章列表。

退出登录由客户端按钮调用 `POST /api/auth/logout`，随后跳回登录页并 `router.refresh()`。

### 5.3 页面

- **登录页**：用户名、密码、可见 label；提交中禁用；401/429 显示对应文案；成功跳 `/admin/posts`。
- **文章列表**：状态筛选（全部/草稿/已发布）、关键词搜索、分页；显示标题、状态、语言、更新时间；操作：编辑、删除（确认）。
- **新建/编辑**：React Hook Form + Zod（新增 `react-hook-form`、`zod`、`@hookform/resolvers`）。字段：标题、slug（新建时按 ASCII 标题自动建议、可手改）、语言、状态、摘要、标签、正文。
- **媒体库**：网格缩略图、上传、复制链接、删除（确认）。使用 `<img>` 展示上传文件（不做 next/image 优化）。

### 5.4 Markdown 编辑器

- 左侧 `<textarea>`，右侧实时预览，复用 `src/components/markdown.tsx`；
- 工具栏：加粗、斜体、行内代码、链接、上传图片；
- 图片上传后插入 `![alt](url)`；
- 保存失败：409 提示 slug 冲突；422 显示字段错误；401 跳转登录；其余显示通用错误；
- 新建保存后跳编辑页；编辑保存后停留在当前页并提示成功；
- 不实现自动保存、拖拽上传、封面图。

### 5.5 数据访问

- 新增 `src/lib/admin-api.ts`（`server-only`），读取 `cookies()` 并把 `Cookie` 头转发给 FastAPI；
- 客户端写操作直接 `fetch('/api/...')`，依赖同源与 Cookie；
- 服务端请求保持 `cache: 'no-store'`；
- 复用 `ApiError`，补充 409/422 的解析。

### 5.6 国际化与入口

- `zh.json` / `en.json` 新增 `admin` 命名空间（导航、登录、表单、错误、媒体库）；
- `(site)/layout.tsx` 服务端读取 `getSiteConfig()`，把 `adminEnabled` 传给 `SiteHeader`；
- 开启时页头显示“后台”入口，关闭时隐藏。

## 6. 测试策略

### 6.1 后端 pytest

新增测试覆盖：

- 未登录访问 `/api/admin/*` → 401；
- `ADMIN_ENABLED=false` 时 `/api/admin/*` → 404；
- 写操作缺少 Origin 或 Origin 不匹配 → 403；GET 正常；
- 文章创建（草稿/发布）、列表筛选与分页、详情、更新、删除；
- 发布/撤回时间规则；
- slug 冲突 409、非法 slug 422、无效 tag_ids 422；
- 标签创建与冲突；
- 上传成功（Pillow 生成临时图片）、类型非法、超过 5 MB、媒体列表与删除；
- 迁移冒烟测试加入 `media` 表，测试清理列表同步更新。

测试写操作时统一带 `Origin: <SITE_ORIGIN>`；上传目录在测试中指向临时目录。

### 6.2 Playwright

新增 `e2e/admin.spec.ts`：

1. 公开页出现“后台”入口；
2. 未登录访问 `/zh/admin/posts` 被重定向到登录页；
3. 使用 `.env` 中的管理员账号登录；
4. 新建草稿（唯一 slug）→ 列表可见；
5. 编辑并发布 → 前台 `/zh/posts` 可见；
6. 删除 → 列表消失。

- 测试账号从 `backend/.env` 解析，仅在 Node 测试进程使用，不打印；
- globalSetup 补跑 `create_admin`，确保账号存在；
- 测试使用独立 slug，避免与演示文章冲突。

### 6.3 验证命令

```bash
cd Z:/my_blog/backend
"venv/Scripts/python.exe" -m pytest -q

cd Z:/my_blog/frontend
npm run build
npm run test:e2e
```

## 7. 风险与注意事项

- **Origin 精确匹配**：`SITE_ORIGIN` 必须与浏览器地址栏来源完全一致（`localhost` 与 `127.0.0.1` 不互通）；E2E 使用 `http://localhost:3000`。
- **Cookie 转发**：服务端后台请求必须显式转发 Cookie，否则一律 401。
- **路由迁移**：公开页迁入 `(site)` 后需确认 404 与 error 边界仍保留站点壳。
- **E2E 写开发库**：测试文章会写入 `my_blog`，测试结束通过 UI 删除；失败时可能残留，需手工清理。
- **上传目录**：`backend/uploads/` 已 gitignore；生产由 nginx alias 提供。
- **测试管理员密码会重置**：globalSetup 的 `create_admin` 会用当前 `.env` 密码更新账号。
- **不打印密钥**：`.env` / `.env.test` / `.env.local` 不读取输出、不提交。

## 8. 验收标准

- 管理员可登录/退出，未登录访问后台会跳转登录页；
- `ADMIN_ENABLED=false` 时后台接口 404、后台入口隐藏；
- 文章可新建、编辑、发布、撤回、删除；前台只显示已发布；
- 标签可勾选并可内联新建；
- 图片可上传、插入正文、在媒体库删除；
- 后端 pytest 全部通过；
- `npm run build` 成功；
- Playwright 全部通过（原有 4 条 + 新增后台主流程）。
