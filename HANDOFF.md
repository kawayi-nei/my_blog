# 项目交接说明

> 更新时间：2026-10-22
> 目的：给下一个 Claude Code 窗口快速接手。先读本文件，再读 README、设计 spec 和对应计划。

## 1. 一句话现状

**基础闭环、计划 2（后台管理）、计划 3A（作品集）都已在 `master`**；本地 `master` HEAD `4847d0e`，已推送到 GitHub。线上服务器 `123.206.100.36` 目前只部署到计划 2，**3A 尚未上线**，因为服务器访问 GitHub 443 超时。

- 当前分支：`master`
- HEAD：`4847d0e fix: run e2e db setup before web server`
- 工作树：干净；本地与 `origin/master` 同步
- 验证：后端 pytest **69 passed**；前端 Playwright **6 passed**；`npm run build` 成功
- 已合并并删除的功能分支：`feature/foundation`、`feature/admin-posts`、`feature/projects`

## 2. 项目位置与关键文档

- 代码根目录：`Z:\my_blog`
- 使用说明：`Z:\my_blog\README.md`
- 总体设计：`docs/superpowers/specs/2026-10-19-personal-blog-design.md`
- 基础闭环计划：`docs/superpowers/plans/2026-10-19-personal-blog-foundation.md`
- 后台管理设计/计划：`docs/superpowers/specs/2026-10-20-admin-posts-design.md`、`docs/superpowers/plans/2026-10-20-admin-posts.md`
- 作品集设计/计划：`docs/superpowers/specs/2026-10-21-projects-design.md`、`docs/superpowers/plans/2026-10-21-projects.md`
- 部署指南：`deploy/README.md`
- 本交接文档：`Z:\my_blog\HANDOFF.md`
- 自动记忆：`C:\Users\Administrator\.claude\projects\Z--claude-code\memory\project_my-blog.md`
- 3A 传输 bundle：`Z:\my_blog_transfer\my_blog.bundle`（master `4847d0e`）

## 3. 本地与线上环境

### 本地

| 项 | 情况 |
|---|---|
| 系统 | Windows 10，Git Bash |
| Node / npm | Node 24.19.0 / npm 11.17.0 |
| Python | 3.12.8，venv 在 `backend/venv` |
| PostgreSQL | 17，安装在 `Y:\internet_tools\postgreSQL` |
| Windows 服务 | `postgresql-x64-17`，可能是 Stopped，需 `Start-Service postgresql-x64-17` |
| 数据库 | 开发库 `my_blog`、测试库 `my_blog_test`，均启用 `pg_trgm` |
| Playwright | Chromium 已安装 |

### 线上服务器

| 项 | 情况 |
|---|---|
| IP | `123.206.100.36` |
| 系统 | Ubuntu 24.04 |
| SSH 用户 | `ubuntu`（有 sudo） |
| 应用用户 | `myblog` |
| 应用目录 | `/srv/my_blog` |
| 运行方式 | nginx + systemd：`myblog-api.service`、`myblog-web.service` |
| 数据库 | PostgreSQL 17，本机 `127.0.0.1:5432`，库 `my_blog` |
| 访问地址 | `http://123.206.100.36`（暂无域名，HTTP 临时方案） |
| 后台 | `http://123.206.100.36/zh/admin` |
| 部署阶段 | 计划 2 已上线；计划 3A 待更新 |

密码/密钥只存在于：

- 本地：`backend/.env`、`backend/.env.test`、`frontend/.env.local`
- 服务器：`/srv/my_blog/backend/.env`、`/srv/my_blog/frontend/.env.local`

**不要读取、打印或提交这些文件。**

## 4. 架构与关键约定

```text
浏览器
  └── nginx
        ├── /api/*     → 127.0.0.1:8000  uvicorn (FastAPI)
        ├── /uploads/* → /srv/my_blog/backend/uploads/
        └── /*         → 127.0.0.1:3000  next start (Next.js)
                            └── PostgreSQL 127.0.0.1:5432
```

- Next.js 只负责页面/SSR/SEO；FastAPI 是唯一业务 API，不写 Next API 路由。
- 开发时 Next rewrites 把 `/api/*`、`/uploads/*` 代理到 `http://127.0.0.1:8000`。
- 服务端组件通过 `frontend/src/lib/api.ts`（`server-only`）请求 `API_BASE_URL`。
- 生产由 nginx 分流 `/api` 与 `/uploads`；FastAPI/Next 只监听 `127.0.0.1`。
- 双语路径 `/zh`、`/en`，`localeDetection: false`。
- 界面文案：`frontend/src/messages/{zh,en}.json`。
- 站点可变内容：`frontend/src/content/site.ts`（GitHub 已指向 `kawayi-nei`；email 仍是占位值）。
- 固定深色终端风格，不做明暗主题切换。
- 后台写操作校验 `Origin`；`SITE_ORIGIN` 必须与浏览器实际来源完全一致。
- 字体已改为 `geist` 包本地自托管，构建不依赖 Google Fonts。

## 5. 已完成内容

### 后端

- FastAPI + SQLAlchemy 2 async + asyncpg + Alembic + PostgreSQL 17
- 表：`users`、`posts`、`tags`、`post_tags`、`media`、`projects`
- 迁移：`0001_initial`、`0002_media`、`0003_projects`
- 管理员种子、Argon2、JWT httpOnly Cookie、登录限流、`ADMIN_ENABLED` 开关
- 公开 API：
  - `GET /api/health`
  - `GET /api/posts`（分页、tag、language、排序）
  - `GET /api/posts/{slug}`（仅已发布）
  - `GET /api/tags`
  - `GET /api/projects`（仅已发布，`featured`、`locale`）
  - `GET /api/projects/{slug}`（本地化标题/摘要/正文；草稿 404）
  - `GET /api/site/config`
  - 登录/登出/me
- 后台 API：
  - 文章 CRUD、项目 CRUD、标签最小集（GET/POST）
  - 图片上传（5 MB、Pillow 复验、尺寸限制）、媒体库列表/删除
  - 所有后台接口继承 `require_admin` + `require_same_origin`

### 前端

- Next.js 16.4.2 App Router + React 19 + Tailwind v4 + next-intl 4
- 公开页：首页、文章列表/详情、作品集列表/详情、404/错误页
- 首页：Hero、精选项目（最多 3 个）、最新文章
- 页头：作品集、文章、后台（按开关）、GitHub、语言切换
- 后台：登录、受保护布局、文章列表/编辑器、媒体库、项目列表/表单
- 项目表单：双语标题/摘要/正文、技术栈、起止日期、Repo/Demo、精选/排序、封面（上传/媒体库选择/清除）
- Markdown：`react-markdown` + `remark-gfm` + `rehype-highlight`，不渲染原始 HTML

### 测试与部署配置

- 后端 pytest：**69 passed**
- Playwright：**6 passed**（公开 4 + 文章后台 1 + 项目后台 1）
- `npm run build`：成功
- `deploy/` 已包含 nginx、两个 systemd 单元、备份脚本、详细上线指南
- 服务器已配置 systemd/nginx/HTTPS 前的 HTTP 访问；`myblog-api.service` 使用 `ProtectHome=read-only`（不能设为 true，否则 asyncpg 探测 `~/.postgresql` 会 EACCES）

## 6. 接下来要做什么

### 先完成 3A 上线

线上服务器无法访问 GitHub（`curl https://github.com` 443 超时），所以不能直接 `git pull`。当前用 bundle 传输：

1. 本地已生成 `Z:\my_blog_transfer\my_blog.bundle`（master `4847d0e`）。
2. 本地 Git Bash：
   ```bash
   scp /z/my_blog_transfer/my_blog.bundle ubuntu@123.206.100.36:/tmp/my_blog.bundle
   ```
3. 服务器：
   ```bash
   sudo -u myblog git -C /srv/my_blog pull --ff-only /tmp/my_blog.bundle master
   sudo -u myblog git -C /srv/my_blog log -1 --oneline   # 4847d0e
   cd /srv/my_blog/backend
   sudo -u myblog venv/bin/alembic upgrade head          # 0003_projects
   sudo -u myblog venv/bin/alembic current
   cd /srv/my_blog/frontend
   sudo -u myblog npm run build                          # 3A 无新依赖，可跳过 npm ci
   sudo systemctl restart myblog-api myblog-web
   ```
4. 验证：
   ```bash
   curl -s http://123.206.100.36/api/health
   curl -s http://123.206.100.36/api/projects
   curl -I http://123.206.100.36/zh/projects
   ```
   然后在后台创建/发布一个精选项目，确认首页与项目详情。

长期解决服务器拉代码：

- **Gitee 镜像（推荐）**：把 GitHub 仓库导入 Gitee，服务器从 Gitee 拉；本地同时 push 两个远端。
- 或配置可用的 GitHub 代理。
- bundle/scp 作为兜底。

### 计划 3B：标签管理与搜索

- 标签管理页（创建/删除/改名）
- 标签筛选 UI（公开文章列表已支持 `tag` 查询参数）
- 站内搜索：`GET /api/search`，文章 + 项目，`pg_trgm`
- 前端搜索页

### 计划 3C：评论

- `comments` 表、公开提交/列表、蜜罐、30 秒频率限制、后台审核

### 计划 3D：阅读统计

- `post_views` 去重、`view_count`、后台统计/仪表盘

### 计划 3E：简历/关于与 SEO

- `resume.zh/en.md`、`about.zh/en.md`
- 双语 metadata、`sitemap.xml`、`robots.txt`、Open Graph

### 其他上线事项

- 拿到域名后切 HTTPS：`COOKIE_SECURE=true`、`SITE_ORIGIN=https://...`、`NEXT_PUBLIC_SITE_URL=https://...`、重新 build
- 备份 cron、nginx 安全头/HSTS、监控日志
- 窄屏导航折叠
- 语言切换保留 query/hash

## 7. 已知问题与注意事项

- **服务器无法访问 GitHub**：443 超时；用 bundle/scp 或 Gitee 镜像。
- **当前是 HTTP**：`COOKIE_SECURE=false`；管理员登录不要在不安全网络进行；尽快上域名/HTTPS。
- **服务器拉代码要用 `myblog` 用户**：`sudo -u myblog git ...`；直接以 `ubuntu` 运行会报 dubious ownership，且可能产生错误属主文件。
- E2E 使用开发库 `my_blog`，会执行迁移、`seed_demo`、重置管理员密码；**不要在生产库运行 pytest/E2E**。
- Playwright 启动后端前会先 `alembic upgrade head`、`seed_demo`、`create_admin`；全新库也能跑。
- `backend/uploads/` 已 gitignore；生产由 nginx `alias` 提供。
- 上传限制：5 MB；单边 ≤ 12000、总像素 ≤ 4000 万。
- 媒体删除是“先 DB 后文件”，极端情况下可能留下孤儿文件。
- 未登录访问后台会先在服务端打印一条 `API 401` 日志，随后正常重定向；不影响功能。
- 公开页/后台尚未各自加 `error.tsx`；运行时错误会退到 locale 级错误页。
- `API_BASE_URL` 在 build 时固化；`NEXT_PUBLIC_SITE_URL` 在 build 时内联；改地址/域名必须重新 build。
- 限流是进程内实现，生产保持单 uvicorn worker；nginx `limit_req` 兜底。
- 最终审查留了几条非阻塞建议：项目 E2E 失败残留清理、`sort_order` 空值错误提示、Repo/Demo URL scheme 校验、只有结束日期时的展示、项目卡片标题层级。

## 8. 常用命令

### 本地启动

```bash
# PostgreSQL（PowerShell）
Start-Service postgresql-x64-17

cd Z:/my_blog/backend
venv/Scripts/python.exe -m alembic upgrade head
venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000

cd Z:/my_blog/frontend
npm run dev
```

- 站点：`http://localhost:3000/zh`
- 后台：`http://localhost:3000/zh/admin`

### 测试

```bash
cd Z:/my_blog/backend
"venv/Scripts/python.exe" -m pytest -q

cd Z:/my_blog/frontend
npm run build
npm run test:e2e
```

### 服务器状态/日志

```bash
sudo systemctl status myblog-api myblog-web nginx postgresql --no-pager
sudo journalctl -u myblog-api -f
sudo journalctl -u myblog-web -f
```

### 服务器更新（有 GitHub 访问后）

```bash
sudo -u myblog git -C /srv/my_blog pull --ff-only
cd /srv/my_blog/backend
sudo -u myblog venv/bin/pip install -r requirements.txt
sudo -u myblog venv/bin/alembic upgrade head
cd /srv/my_blog/frontend
sudo -u myblog npm ci
sudo -u myblog npm run build
sudo systemctl restart myblog-api myblog-web
```

## 9. 建议的接手方式

1. 先读本文件、`README.md`、总体设计 spec 和当前阶段计划。
2. 新功能先走 brainstorming → 写 spec → 写实施计划，再实现。
3. 实现用子代理驱动：每个任务一个实现子代理 + 规格审查 + 质量审查；同一工作树的写操作串行。
4. 在功能分支上开发，测试通过后再合并 master；不要直接在 master 上改。
5. 每次给用户命令时，附一句用途/原理说明。
6. 不读取、不打印、不提交 `.env`、`.env.test`、`.env.local`。

## 10. 新窗口开场输入（可直接粘贴）

```text
继续 Z:\my_blog 个人博客项目。先读 HANDOFF.md、README.md 和
docs/superpowers/specs/2026-10-19-personal-blog-design.md。

当前状态：master 4847d0e，基础闭环、计划 2 后台管理、计划 3A 作品集已合并；
后端 pytest 69 passed、Playwright 6 passed、build 成功。
线上服务器 123.206.100.36（Ubuntu 24.04，HTTP，无域名）已部署计划 2，
3A 尚未上线；服务器访问 GitHub 443 超时，需要按 HANDOFF 第 6 节用
git bundle + scp 更新，bundle 在 Z:\my_blog_transfer\my_blog.bundle。

接下来：先把 3A 部署到服务器（bundle → alembic upgrade head → npm run build
→ restart → 验证 /api/projects 和 /zh/projects），然后开始计划 3B
（标签管理与站内搜索），先 brainstorming → spec → plan，再实现。

约束：不要在 master 上直接开发，用功能分支；不要读取/打印/提交 .env
文件；实现用子代理驱动和两阶段审查。
```
