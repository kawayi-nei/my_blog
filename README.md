# My Blog

个人站点：作品集 + 技术写作。前端使用 Next.js，后端使用 FastAPI，数据存储使用 PostgreSQL。

当前阶段已完成基础闭环：健康检查、管理员认证、公开文章 API、数据库迁移、深色双语站点壳、首页/文章列表/文章详情，以及 Playwright 公共浏览测试。后台 CRUD、项目、评论、统计与图片上传尚未实现（见文末文档）。

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
│   │   ├── api/            # 公开接口（auth、site、posts、tags）
│   │   ├── core/           # 配置、安全
│   │   ├── db/             # 引擎、会话、Base
│   │   ├── models/         # SQLAlchemy 模型
│   │   ├── schemas/        # Pydantic 模型
│   │   ├── scripts/        # create_admin、seed_demo
│   │   ├── services/       # 业务逻辑（含限流）
│   │   └── main.py
│   ├── alembic/            # 数据库迁移
│   ├── tests/              # pytest 测试
│   ├── uploads/            # 上传文件（运行时生成，不入库）
│   ├── alembic.ini
│   ├── pytest.ini
│   ├── requirements.txt
│   ├── .env.example
│   └── .env.test.example
├── frontend/
│   ├── src/
│   │   ├── app/[locale]/   # 首页、文章列表、文章详情
│   │   ├── components/     # 站点壳、文章卡片、Markdown 渲染
│   │   ├── content/        # site.ts、简历/关于内容
│   │   ├── i18n/           # next-intl 配置
│   │   ├── lib/            # API 封装
│   │   └── messages/       # zh.json、en.json
│   ├── e2e/                # Playwright 测试与全局初始化
│   ├── next.config.ts
│   ├── playwright.config.ts
│   ├── package.json
│   └── .env.local.example
├── deploy/                 # nginx/systemd 部署配置（后续阶段）
├── docs/superpowers/       # 设计文档与实施计划
└── README.md
```

## 前置条件

- Node.js 24（npm 随附）
- Python 3.12
- PostgreSQL 17
- Playwright Chromium（首次运行 E2E 前安装）：

```bash
cd frontend
npx playwright install chromium
```

## PostgreSQL

### 检查并启动 Windows 服务

本机服务名为 `postgresql-x64-17`。在 PowerShell 中执行：

```powershell
Get-Service postgresql-x64-17
Start-Service postgresql-x64-17
```

若服务已处于 `Running` 状态则无需启动。

### 创建数据库与扩展

需要开发库 `my_blog` 与测试库 `my_blog_test`，两者都要启用 `pg_trgm` 扩展。以下命令使用 `postgres` 超级用户执行（创建扩展需要超级用户权限）：

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

如果 `psql` 不在 `PATH` 中，可使用 PostgreSQL 安装目录下的 `bin/psql.exe`。

## 后端

```bash
cd backend
```

首次使用需准备虚拟环境（仓库中已有 `backend/venv` 时可跳过）：

```bash
python -m venv venv
venv/Scripts/python.exe -m pip install -r requirements.txt
```

### 配置环境变量

```bash
cp .env.example .env
cp .env.test.example .env.test
```

编辑 `.env`，至少填写：

- `DATABASE_URL`：数据库密码（与上面 `blog_user` 的密码一致）
- `JWT_SECRET`：不少于 32 字符的随机字符串
- `ADMIN_PASSWORD`：不少于 12 字符
- `IP_HASH_SALT`：随机字符串

`.env.test` 供 pytest 使用，默认指向 `my_blog_test`，按需修改数据库密码。

### 初始化并启动

```bash
venv/Scripts/python.exe -m alembic upgrade head
venv/Scripts/python.exe -m app.scripts.create_admin
venv/Scripts/python.exe -m app.scripts.seed_demo
venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
```

健康检查：<http://127.0.0.1:8000/api/health>，应返回 `{"status":"ok"}`。

## 前端

```bash
cd frontend
cp .env.local.example .env.local
npm install        # 仅首次
npm run dev
```

打开 <http://localhost:3000/zh>。`next.config.ts` 会把 `/api/*` 与 `/uploads/*` 反向代理到 FastAPI，因此浏览器侧始终同源。

## 测试与构建

后端测试（使用 `.env.test` 与测试库）：

```bash
cd backend
"venv/Scripts/python.exe" -m pytest -v
```

前端 E2E（会自动执行 `alembic upgrade head` 和 seed，并启动前后端开发服务器）：

```bash
cd frontend
npm run test:e2e
```

生产构建：

```bash
cd frontend
npm run build
```

## 后台开关

在 `backend/.env` 中设置：

```dotenv
ADMIN_ENABLED=true
```

- `true`：登录接口与后台接口可用。
- `false`：`/api/auth/login`、`/api/auth/logout` 及 `/api/admin/*` 返回 404，后台入口隐藏；公开页面与公开 API 不受影响。

修改后需重启 FastAPI。该开关只控制后台是否开放，不能替代权限校验。

## 环境注意事项

- `JWT_SECRET` 至少 32 字符，`ADMIN_PASSWORD` 至少 12 字符；配置会拒绝以 `replace-with` 开头的占位符。
- `API_BASE_URL` 由 `frontend/next.config.ts` 的 rewrites 在**构建时**读取。生产执行 `npm run build` 前必须先设置正确的后端地址。
- `frontend/package.json` 中的 `@swc/core` override 是本机 Windows ACL 导致 `ERR_SWC_NATIVE_CACHE` 的 workaround；升级 next-intl 或修复 ACL 后可移除。
- `frontend/src/content/site.ts` 中的 GitHub 与 email 仍是占位值，上线前请替换为真实信息。
- 限流为进程内实现。生产环境建议使用单个 uvicorn worker，并由 nginx `limit_req` 兜底。
- 本阶段未实现后台 CRUD、项目、评论、统计、图片上传等能力；范围与后续计划见下方文档。

## 相关文档

- 设计文档：`docs/superpowers/specs/2026-10-19-personal-blog-design.md`
- 基础阶段实施计划：`docs/superpowers/plans/2026-10-19-personal-blog-foundation.md`
