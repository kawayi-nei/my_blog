# My Blog

个人站点：作品集 + 技术写作。前端使用 Next.js，后端使用 FastAPI，数据存储使用 PostgreSQL。

计划 2 已完成后台登录、文章 CRUD、Markdown 编辑器、图片上传与媒体库；计划 3A 已完成双语作品集（项目表与 CRUD、公开列表/详情、首页精选、后台项目管理）。剩余标签管理页与搜索、评论、阅读统计、简历/关于、SEO 与部署（见文末文档）。

## 技术栈

| 层 | 选型 |
|---|---|
| 前端 | Next.js 16（App Router）、React 19、TypeScript、Tailwind CSS 4 |
| 国际化 | next-intl（`/zh`、`/en`） |
| Markdown | react-markdown、remark-gfm、rehype-highlight |
| 后端 | FastAPI、Pydantic v2、Uvicorn |
| 数据库 | PostgreSQL 17、SQLAlchemy 2（async）、asyncpg、Alembic |
| 鉴权 | PyJWT（HS256）+ httpOnly Cookie + Argon2（pwdlib） |
| 测试 | pytest、pytest-asyncio、httpx；Playwright |

## 目录结构

```text
my_blog/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── public/     # auth、site、posts、tags、projects
│   │   │   └── admin/      # 后台文章、标签、项目、上传、媒体库
│   │   ├── core/           # 配置、安全
│   │   ├── db/             # 引擎、会话、Base
│   │   ├── models/         # SQLAlchemy 模型（post、tag、media、project）
│   │   ├── schemas/        # Pydantic 模型
│   │   ├── scripts/        # create_admin、seed_demo
│   │   ├── services/       # 业务逻辑（含限流）
│   │   └── main.py
│   ├── alembic/            # 数据库迁移（0001_initial、0002_media、0003_projects）
│   ├── tests/              # pytest 测试
│   ├── uploads/            # 上传文件（已 gitignore）
│   ├── alembic.ini
│   ├── pytest.ini
│   ├── requirements.txt
│   ├── .env.example
│   └── .env.test.example
├── frontend/
│   ├── src/
│   │   ├── app/[locale]/   # 首页、文章、项目、后台（admin/）
│   │   ├── components/     # 站点壳、文章组件、项目卡片、后台组件（admin/）
│   │   ├── content/        # 目前只有 site.ts
│   │   ├── i18n/           # next-intl 配置
│   │   ├── lib/            # API 封装（server-only）
│   │   ├── messages/       # zh.json、en.json
│   │   └── proxy.ts
│   ├── e2e/                # Playwright 测试（public、admin、projects）、helpers 与全局初始化
│   ├── next.config.ts
│   ├── playwright.config.ts
│   ├── package.json
│   └── .env.local.example
├── deploy/                 # nginx、systemd、备份脚本与上线指南
├── docs/superpowers/       # 设计文档与实施计划
└── README.md
```

## 前置条件

- Node.js 24（npm 随附）
- Python 3.12
- PostgreSQL 17
- Playwright Chromium：首次运行 E2E 前安装，必须在 `frontend` 下执行 `npm install` 之后安装（见[前端](#前端)）

本文主要针对 Windows 本机开发。除特别标注为 PowerShell 的命令外，代码块以 bash 语法展示，默认在 **Git Bash** 中执行。PowerShell 用户请直接使用 Git Bash；若必须在 PowerShell 中执行，请使用调用运算符，例如：

```powershell
& ".\venv\Scripts\python.exe" -m pytest -v
```

同时 `cp` 需换成 `Copy-Item`。带引号的可执行文件路径（如 `"venv/Scripts/python.exe"`）在 Windows PowerShell 5.1 中会解析失败，因此不要假设所有命令都能在 PowerShell 中直接粘贴。除标注“可在任意目录执行”的命令外，**每个代码块都假定从仓库根目录开始**，执行完一个代码块后请回到仓库根目录（长驻服务命令除外），再执行下一个。

## PostgreSQL

### 检查并启动 Windows 服务

以下命令在 PowerShell 中执行（可在任意目录）：

```powershell
Get-Service postgresql-x64-17
Start-Service postgresql-x64-17
```

若服务已处于 `Running` 状态则无需启动。`Start-Service` 通常需要**以管理员身份运行 PowerShell**；若提示 Access denied，请关闭当前窗口，右键“以管理员身份运行”后重试。

### 创建数据库与扩展

需要开发库 `my_blog` 与测试库 `my_blog_test`，两者都要启用 `pg_trgm` 扩展。以下命令可在任意目录执行，使用 `postgres` 超级用户。这里用 postgres 预创建以兼容不同权限；迁移中也会 `CREATE EXTENSION IF NOT EXISTS pg_trgm`，PostgreSQL 13+ 中库所有者通常也能创建。`psql` 会提示输入 postgres 用户的密码：

```powershell
# 创建应用账号（若已存在可跳过）
psql -U postgres -h 127.0.0.1 -d postgres -c "CREATE ROLE blog_user LOGIN PASSWORD 'your-db-password';"

# 创建开发库与测试库
psql -U postgres -h 127.0.0.1 -d postgres -c "CREATE DATABASE my_blog OWNER blog_user;"
psql -U postgres -h 127.0.0.1 -d postgres -c "CREATE DATABASE my_blog_test OWNER blog_user;"

# 启用 pg_trgm
psql -U postgres -h 127.0.0.1 -d my_blog -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
psql -U postgres -h 127.0.0.1 -d my_blog_test -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
```

如果 `psql` 不在 `PATH` 中，可使用 PostgreSQL 安装目录下的 `bin/psql.exe`。PowerShell 中带空格的路径需要用调用运算符，例如：

```powershell
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -h 127.0.0.1 -d postgres
```

如果本机安装路径不同，请相应调整。

### 故障排查

- 端口占用：`netstat -ano | findstr :8000`、`netstat -ano | findstr :3000` 查看监听进程，再按 PID 排查。
- 数据库服务：`Get-Service postgresql-x64-17` 确认状态为 `Running`。
- 连接认证：`psql -U postgres -h 127.0.0.1 -d postgres` 会提示输入 postgres 用户的密码；若反复失败，检查安装时设置的密码或 `pg_hba.conf` 认证方式。

## 后端

### 虚拟环境

以下命令在仓库根目录执行：

```bash
cd backend
python -m venv venv
"venv/Scripts/python.exe" -m pip install -r requirements.txt
```

`backend/venv` 不会随仓库提交（已被 gitignore）。若本地已有可用的 `backend/venv`，可跳过创建与安装；新环境必须执行上述命令。

### 配置环境变量

以下命令在仓库根目录执行：

```bash
cd backend
cp .env.example .env
cp .env.test.example .env.test
```

编辑 `.env`，至少填写：

- `DATABASE_URL`：把 `.env.example` 里 `DATABASE_URL` 中的 `YOUR_PASSWORD` 替换为 `blog_user` 的密码，不要把整个变量设成密码。形如 `postgresql+asyncpg://blog_user:<密码>@127.0.0.1:5432/my_blog`。
- `JWT_SECRET`：不少于 32 字符的随机字符串。
- `ADMIN_PASSWORD`：不少于 12 字符。
- `IP_HASH_SALT`：随机字符串；必须手动替换，但不会被占位符校验拦截。
- `COOKIE_SECURE`：本机 HTTP 开发保持 `false`；生产环境（HTTPS）设为 `true`。
- `SITE_ORIGIN`：前端来源地址，后台写操作的 Origin 校验会与它比对。

`.env.test` 供 pytest 使用，默认指向 `my_blog_test`，同样需要把其中的 `YOUR_PASSWORD` 替换为实际数据库密码。

### 初始化并启动

以下命令在仓库根目录执行：

```bash
cd backend
venv/Scripts/python.exe -m alembic upgrade head
venv/Scripts/python.exe -m app.scripts.create_admin
venv/Scripts/python.exe -m app.scripts.seed_demo
venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
```

`create_admin` 会创建管理员，若用户已存在则更新其密码；`seed_demo` 会写入演示文章。

`uvicorn ... --reload` 会占用当前终端，不会返回；请保持该终端运行，并在新终端执行后续步骤。

健康检查：<http://127.0.0.1:8000/api/health>，应返回 `{"status":"ok"}`。

## 前端

以下命令在仓库根目录执行：

```bash
cd frontend
cp .env.local.example .env.local
npm install                        # 仅首次
npx playwright install chromium    # 首次运行 E2E 前；必须在 npm install 之后
npm run dev
```

顺序很重要：先 `npm install`（安装 `@playwright/test`），再执行 `npx playwright install chromium` 安装浏览器。

`npm run dev` 同样会占用当前终端，不会返回；请保持该终端运行，并在新终端执行后续步骤。

打开 <http://localhost:3000/zh>。

### `API_BASE_URL` 与请求路径

`frontend/.env.local` 中的 `API_BASE_URL` 有两个读取位置：

- `frontend/next.config.ts` 的 `/api`、`/uploads` rewrites 在 **`next build` 时**读取 `API_BASE_URL` 并固化到构建产物中；生产执行 `npm run build` 前必须先设置正确的后端地址。
- `frontend/src/lib/api.ts` 是 `server-only` 模块，在**服务端运行时**也读取同一个 `API_BASE_URL`。当前页面数据由 Next 服务端直接请求 FastAPI，浏览器不直接依赖 `/api/*` rewrite。

修改 `.env.local` 后需要重启 `next dev`。`NEXT_PUBLIC_SITE_URL` 用于 `frontend/src/app/[locale]/layout.tsx` 的 `metadataBase`。

## 测试与构建

### 后端测试

以下命令在仓库根目录执行：

```bash
cd backend
"venv/Scripts/python.exe" -m pytest -v
```

当前基线：**69 passed**。

注意：pytest 会删除并重建 `my_blog_test` 中的所有表；请确保 `.env.test` 指向测试库，不要把测试指向开发库。测试会话结束时会再次删除表，测试库会保持空结构，下次运行重新迁移。

### 前端 E2E

以下命令在仓库根目录执行：

```bash
cd frontend
npm run test:e2e
```

当前基线：**6 passed**（4 条公开浏览 + 1 条后台文章主流程 + 1 条后台项目主流程）。

E2E 读取 `backend/.env`（开发库 `my_blog`），全局初始化会执行 `alembic upgrade head`、运行 `seed_demo` 写入演示文章，并**重置管理员密码**。Playwright 会自动启动或复用 3000/8000 端口上的服务；`seed_demo` 是 upsert，会覆盖 `first-post` 的演示内容并刷新发布时间。

### 生产构建

以下命令在仓库根目录执行：

```bash
cd frontend
npm run build
```

## 后台开关

在 `backend/.env` 中设置：

```dotenv
ADMIN_ENABLED=true
```

- `true`：`/api/auth/login`、`/api/auth/logout`、`/api/auth/me`、`/api/site/config` 正常。
- `false`：`/api/auth/login`、`/api/auth/logout` 返回 404；`/api/auth/me` 返回 401；`/api/site/config` 仍返回 200，且响应中 `admin_enabled: false`。

修改后需重启 FastAPI。该开关只控制后台是否开放，不能替代权限校验。

## 后台管理

- 启动前后端，并确保 `backend/.env` 中 `ADMIN_ENABLED=true`。
- 打开 <http://localhost:3000/zh/admin>，使用 `backend/.env` 中配置的管理员账号登录。
- 文章支持草稿/发布、Markdown 实时预览、正文图片上传。
- 项目管理：中英文标题与正文、技术栈、封面、Repo/Demo 地址、精选与排序，支持草稿/发布。
- 媒体库支持上传、复制链接、删除。
- 所有 `/api/admin/*` 写操作都会校验 `Origin`；`SITE_ORIGIN` 必须与浏览器地址栏的来源（scheme + host + port）一致，否则请求会被拒绝。

## 环境注意事项

- 只有 `JWT_SECRET` 和 `ADMIN_PASSWORD` 会拒绝以 `replace-with` 开头的占位符（长度下限分别为 32 和 12 字符）。`IP_HASH_SALT` 必须手动替换为随机值，但不会被校验。
- 生产环境设置 `COOKIE_SECURE=true`（需要 HTTPS），并配置真实的 `SITE_ORIGIN`（后台写操作的 Origin 校验依赖它）。
- `frontend/package.json` 中的 `@swc/core` override 针对的是 next-intl 的传递依赖：若在 Windows 上遇到 `ERR_SWC_NATIVE_CACHE`，当前通过 pin 到 1.16.0 规避；升级 next-intl 或修复 ACL 后可移除该 override。这不是所有平台都必须保留的设置。
- `frontend/src/content/site.ts` 中的 email 仍是占位值，上线前请按需替换为真实信息（GitHub 已指向 `kawayi-nei`）。
- 限流为进程内实现。生产环境建议使用单个 uvicorn worker，并由 nginx `limit_req` 兜底。
- 后台已实现登录、受保护布局、文章 CRUD、Markdown 编辑器、图片上传、媒体库与项目管理。E2E 会重置管理员密码并写入开发库 `my_blog`；不要用该库保存重要数据。上传限制为单文件 5 MB，图片单边不超过 12000 像素且总像素不超过 4000 万；`backend/uploads/` 已 gitignore。

## 部署

当前部署目标：Ubuntu 24.04，公网 IP `123.206.100.36`，暂无域名，先用 HTTP 访问。
完整步骤、变量解释、systemd/nginx 配置、备份与回滚见 `deploy/README.md`。

- `deploy/nginx.conf`：nginx 站点配置
- `deploy/myblog-api.service`：FastAPI systemd 单元
- `deploy/myblog-web.service`：Next.js systemd 单元
- `deploy/backup.sh`：数据库与上传文件每日备份

## 相关文档

- 部署指南：`deploy/README.md`
- 设计文档：`docs/superpowers/specs/2026-10-19-personal-blog-design.md`
- 基础阶段实施计划：`docs/superpowers/plans/2026-10-19-personal-blog-foundation.md`
- 作品集设计文档：`docs/superpowers/specs/2026-10-21-projects-design.md`
- 作品集实施计划：`docs/superpowers/plans/2026-10-21-projects.md`
