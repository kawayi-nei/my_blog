# My Blog 上线指南

- 服务器：`123.206.100.36`（Ubuntu 24.04，有 sudo 权限）
- 代码仓库：<https://github.com/kawayi-nei/my_blog>（Public）
- 当前阶段：**没有域名，先用 `http://123.206.100.36` 直接访问**
- 应用目录：`/srv/my_blog`
- 运行用户：`myblog`
- 进程：`myblog-api.service`（FastAPI）、`myblog-web.service`（Next.js）
- 反向代理：nginx

> **先读这一段：HTTP 临时方案的限制**
>
> 没有域名就无法正常申请 Let's Encrypt 证书，所以本指南当前用 HTTP。
> 这意味着管理员登录的用户名和密码会以明文经过网络。个人博客的公开浏览问题不大，
> 但**后台登录不要在公共 Wi-Fi 等不可信网络进行**。
>
> 拿到域名后，请按本文最后的「切换到 HTTPS」章节升级。届时需要修改
> `COOKIE_SECURE=true`、`SITE_ORIGIN`、`NEXT_PUBLIC_SITE_URL` 并重新构建前端。
>
> 不推荐用自签名证书：浏览器会报警告，且不能解决“用户如何确认站点身份”的问题。
> 也不建议依赖 IP 证书：申请和续期都更麻烦，不适合首次上线。

---

## 0. 整体结构

```text
浏览器
  │
  └── nginx :80
        ├── /api/*     → 127.0.0.1:8000  uvicorn（FastAPI）
        ├── /uploads/* → /srv/my_blog/backend/uploads/
        └── /*         → 127.0.0.1:3000  next start（Next.js）
                            │
                            └── PostgreSQL 127.0.0.1:5432
```

为什么要这样拆：

- **只有 nginx 监听公网端口**。FastAPI 和 Next 都绑定 `127.0.0.1`，外部无法绕过 nginx 直接访问，减少了暴露面。
- **`/api` 和 `/uploads` 不经过 Next**。FastAPI 是唯一业务 API；图片由 nginx 直接读磁盘，比让 Python 或 Node 转发更省资源。
- **PostgreSQL 只监听本机**。数据库不暴露公网，降低被扫描和暴力破解的风险。
- **systemd 负责进程守护**。服务崩溃自动重启、开机自启、日志统一进 journald，不需要手工开终端挂进程。

---

## 1. 服务器环境准备

### 1.1 登录服务器

```bash
ssh <你的用户名>@123.206.100.36
```

后面所有命令默认在这台服务器上执行；需要 sudo 的命令已经写明。

### 1.2 安装系统包

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y \
  git curl build-essential \
  nginx ufw \
  python3.12 python3.12-venv python3.12-dev libpq-dev \
  postgresql-common
```

每个包的作用：

- `git`：从 GitHub 拉代码。
- `curl`：安装 Node、调试 HTTP。
- `build-essential`、`python3.12-dev`、`libpq-dev`：编译/安装 Python 依赖时需要（asyncpg、argon2 等）。
- `nginx`：反向代理与静态文件服务。
- `ufw`：防火墙。
- `python3.12-venv`：创建隔离的 Python 环境，避免污染系统 Python。
- `postgresql-common`：添加 PostgreSQL 官方源的工具。

### 1.3 安装 Node.js 22 LTS

Ubuntu 自带的 Node 版本可能偏旧。Next.js 16 要求 Node 20.9+，用 22 LTS 更稳：

```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs
node -v    # 应为 v22.x
npm -v
```

为什么不用系统自带 Node：版本不可控，且不同 Ubuntu 镜像差异大。NodeSource 提供统一的 LTS 版本。

### 1.4 安装 PostgreSQL 17

Ubuntu 24.04 默认源是 PostgreSQL 16；项目使用 17，需要 PGDG 官方源：

```bash
sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh
sudo apt install -y postgresql-17 postgresql-contrib-17
sudo systemctl enable --now postgresql
```

创建数据库用户、数据库和 `pg_trgm` 扩展：

```bash
sudo -u postgres psql <<'SQL'
CREATE ROLE blog_user LOGIN PASSWORD '替换成强密码';
CREATE DATABASE my_blog OWNER blog_user;
\c my_blog
CREATE EXTENSION IF NOT EXISTS pg_trgm;
SQL
```

说明：

- `blog_user` 是应用专用账号，不要用 `postgres` 超级用户跑应用。
- `pg_trgm` 是三元组索引扩展，文章搜索/模糊查询会用到；迁移里也会尝试创建，但由 `postgres` 预先创建更稳妥。
- PostgreSQL 默认只监听 `localhost`，不要改 `listen_addresses` 为 `*`。

### 1.5 创建应用用户与目录

```bash
sudo adduser --system --group --home /home/myblog --shell /bin/bash myblog
sudo mkdir -p /srv/my_blog
sudo chown myblog:myblog /srv/my_blog
```

为什么单独建用户：

- 应用不以 root 运行。即使 FastAPI/Next 被攻破，攻击者也只有 `myblog` 的权限。
- `/srv/my_blog` 归 `myblog` 所有，代码、venv、上传文件权限一致，避免 `Permission denied`。
- `--shell /bin/bash` 是为了方便 `sudo -u myblog` 执行 git/npm/pip；该用户不设密码，不能直接 SSH 登录。

### 1.6 防火墙

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
sudo ufw status
```

只放行 SSH 和 HTTP/HTTPS。不要放行 3000、8000、5432；这些服务都只监听 `127.0.0.1`。

---

## 2. 通过 GitHub 传代码

### 2.1 为什么服务器可以直接 clone

仓库是 Public，服务器只需要读权限，因此用 HTTPS clone 即可，**不需要配置 deploy key**。
以后要更新时直接 `git pull`，也不会要求密码。

```bash
sudo -u myblog git clone https://github.com/kawayi-nei/my_blog.git /srv/my_blog
```

检查：

```bash
sudo -u myblog git -C /srv/my_blog log -1 --oneline
```

### 2.2 本地还没有推送过？

如果本地仓库还没有 remote：

```bash
cd Z:/my_blog
git remote add origin git@github.com:kawayi-nei/my_blog.git
git push -u origin master
```

- `-u` 把本地 `master` 与 `origin/master` 关联，以后直接 `git push`。
- 如果 SSH key 没配好，可以把 remote 改成 HTTPS：
  `git remote set-url origin https://github.com/kawayi-nei/my_blog.git`
- **不要把 `.env`、`.env.local`、`venv/`、`node_modules/`、`.next/`、`backend/uploads/` 推到 GitHub。**

### 2.3 以后的更新方式

服务器上：

```bash
sudo -u myblog git -C /srv/my_blog pull --ff-only
```

`--ff-only` 表示只接受快进合并，避免服务器上产生意外的 merge commit。发布流程见第 8 节。

---

## 3. 后端：Python 环境、配置与迁移

### 3.1 创建虚拟环境

```bash
cd /srv/my_blog/backend
sudo -u myblog python3.12 -m venv venv
sudo -u myblog venv/bin/pip install --upgrade pip
sudo -u myblog venv/bin/pip install -r requirements.txt
```

为什么用 `venv`：

- 项目依赖（FastAPI、SQLAlchemy、asyncpg、Pillow 等）与系统 Python 隔离。
- 升级服务器系统包时不会破坏应用依赖。
- `requirements.txt` 锁定了版本，保证本地和服务器行为一致。

### 3.2 创建后端 `.env`

```bash
sudo -u myblog nano /srv/my_blog/backend/.env
```

内容：

```dotenv
DATABASE_URL=postgresql+asyncpg://blog_user:数据库密码@127.0.0.1:5432/my_blog
JWT_SECRET=用 openssl rand -hex 32 生成
JWT_EXPIRE_DAYS=7
ADMIN_USERNAME=admin
ADMIN_PASSWORD=替换成至少 12 位强密码
ADMIN_ENABLED=true
UPLOAD_DIR=/srv/my_blog/backend/uploads
IP_HASH_SALT=用 openssl rand -hex 32 生成
COOKIE_SECURE=false
SITE_ORIGIN=http://123.206.100.36
```

生成随机值：

```bash
openssl rand -hex 32
```

逐项解释：

| 变量 | 作用 | 注意 |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy 连接串 | 密码含 `@ : / %` 等字符时要 URL 编码，或者直接用字母数字强密码 |
| `JWT_SECRET` | 签发/校验登录 JWT | 至少 32 字符；泄露等于别人可以伪造登录态 |
| `JWT_EXPIRE_DAYS` | 登录 Cookie 有效期 | 默认 7 天 |
| `ADMIN_USERNAME` | 管理员用户名 | 可改 |
| `ADMIN_PASSWORD` | 管理员密码 | 至少 12 字符；`create_admin` 会用它写入数据库 |
| `ADMIN_ENABLED` | 后台总开关 | `false` 时后台接口全部 404 |
| `UPLOAD_DIR` | 图片保存目录 | 必须是 `myblog` 可写、nginx 可读 |
| `IP_HASH_SALT` | 评论/阅读统计的 IP 哈希盐 | 随机值，不要外泄 |
| `COOKIE_SECURE` | Cookie 是否只走 HTTPS | **当前 HTTP 临时方案必须为 false**；上 HTTPS 后改 true |
| `SITE_ORIGIN` | 后台写操作 Origin 校验 | 必须与浏览器地址栏完全一致；当前是 `http://123.206.100.36` |

权限：

```bash
sudo chown myblog:myblog /srv/my_blog/backend/.env
sudo chmod 600 /srv/my_blog/backend/.env
```

为什么是 600：只有 `myblog` 能读，其他系统用户看不到 JWT 密钥和数据库密码。

### 3.3 建上传目录

```bash
sudo -u myblog mkdir -p /srv/my_blog/backend/uploads
sudo chown -R myblog:myblog /srv/my_blog/backend/uploads
```

FastAPI 启动时也会自动创建该目录，但提前建好并设权限更直观。

### 3.4 执行数据库迁移

```bash
cd /srv/my_blog/backend
sudo -u myblog venv/bin/alembic upgrade head
```

为什么需要迁移：建表、约束、索引、`media` 表都定义在 Alembic 迁移里；只拉代码不执行迁移，应用会报表不存在。

验证：

```bash
sudo -u myblog venv/bin/alembic current
# 应显示 0002_media (head)
```

### 3.5 创建管理员

```bash
sudo -u myblog venv/bin/python -m app.scripts.create_admin
```

- 从 `.env` 读取 `ADMIN_USERNAME` / `ADMIN_PASSWORD`。
- 用户不存在则创建；已存在则更新密码。
- **不要在生产运行 `seed_demo`**：它会写入/覆盖演示文章。
- **不要在生产运行 pytest / Playwright**：测试会清空测试库或操作开发库，绝不能指向生产库。

---

## 4. 前端：依赖、环境变量与构建

### 4.1 安装依赖

```bash
cd /srv/my_blog/frontend
sudo -u myblog npm ci
```

为什么用 `npm ci` 而不是 `npm install`：

- `npm ci` 严格按 `package-lock.json` 安装，版本可复现。
- 不会修改锁文件，适合服务器/CI。

### 4.2 创建前端 `.env.local`

```bash
sudo -u myblog nano /srv/my_blog/frontend/.env.local
```

内容：

```dotenv
API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_SITE_URL=http://123.206.100.36
```

权限：

```bash
sudo chown myblog:myblog /srv/my_blog/frontend/.env.local
sudo chmod 600 /srv/my_blog/frontend/.env.local
```

两个变量的区别：

- `API_BASE_URL`：Next 服务端组件请求 FastAPI 用；同时 `next.config.ts` 的 rewrites 在 **build 时**读取它并固化。改它必须重新 build。
- `NEXT_PUBLIC_SITE_URL`：用于页面 metadata / canonical 等，`NEXT_PUBLIC_` 前缀的变量会在 **build 时内联进前端产物**。改域名必须重新 build。

### 4.3 构建

```bash
cd /srv/my_blog/frontend
sudo -u myblog npm run build
```

为什么在服务器 build：

- `.next/` 构建产物通常在 `.gitignore` 里，不会从 GitHub 传过去。
- 构建依赖服务器上的 Node 和 `.env.local`，在目标环境构建最稳妥。
- 生产用 `next start` 跑构建产物，**不要用 `next dev`**。

字体说明：项目已改用 `geist` 包在本地自托管 Geist / Geist Mono 字体，
`next build` 不再请求 `fonts.googleapis.com`。这对国内服务器很重要——否则
构建会因为访问不了 Google Fonts 而直接失败。以后不要把字体改回
`next/font/google`，除非确认服务器能稳定访问 Google。

构建输出中应看到：

```text
ƒ /[locale]
ƒ /[locale]/admin
ƒ /[locale]/admin/login
ƒ /[locale]/admin/media
ƒ /[locale]/admin/posts
ƒ /[locale]/admin/posts/[id]/edit
ƒ /[locale]/admin/posts/new
ƒ /[locale]/posts
ƒ /[locale]/posts/[slug]
```

---

## 5. 用 systemd 接管 FastAPI

### 5.1 安装 service 文件

仓库里已经准备好：

- `deploy/myblog-api.service`
- `deploy/myblog-web.service`

复制到 systemd：

```bash
sudo cp /srv/my_blog/deploy/myblog-api.service /etc/systemd/system/
sudo cp /srv/my_blog/deploy/myblog-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now myblog-api myblog-web
```

检查：

```bash
sudo systemctl status myblog-api
sudo systemctl status myblog-web
```

### 5.2 为什么要这样配

- **`User=myblog`**：不以 root 运行。
- **`WorkingDirectory`**：uvicorn 需要能找到 `app.main:app`；Next 需要找到 `.next` 和 `package.json`。
- **`--host 127.0.0.1`**：只允许 nginx 访问，公网打不到 8000/3000。
- **`--workers 1`**：当前登录限流是进程内计数。多开 worker 会变成“每个 worker 各限 5 次”，实际额度翻倍。
- **`--proxy-headers --forwarded-allow-ips=127.0.0.1`**：让 FastAPI 信任 nginx 传来的 `X-Forwarded-For`，拿到真实客户端 IP。否则所有请求都被当成 127.0.0.1，登录限流和阅读统计都会失真。
- **`Restart=always`**：进程异常退出后自动拉起。
- **`ProtectSystem=full` / `PrivateTmp` / `NoNewPrivileges`**：基础加固，减少进程被利用后的影响面。
- **`ProtectHome=read-only` 而不是 `true`**：asyncpg 建立连接时会探测 `~/.postgresql/postgresql.key` 这个默认客户端证书路径。如果把 `/home` 完全隐藏，这个探测会变成 `Permission denied`，即使你根本没有使用客户端证书。设为只读即可。

后端自己读取 `backend/.env`，所以 service 文件里不需要再写数据库密码。这样密钥只存在一个地方。

### 5.3 查看日志

```bash
sudo journalctl -u myblog-api -f
sudo journalctl -u myblog-web -f
```

`journalctl` 是 systemd 的日志入口，不需要额外配置日志文件；`-f` 表示持续跟随。

---

## 6. nginx 反向代理

### 6.1 安装配置

```bash
sudo cp /srv/my_blog/deploy/nginx.conf /etc/nginx/sites-available/myblog
sudo ln -sf /etc/nginx/sites-available/myblog /etc/nginx/sites-enabled/myblog
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

- `sites-available/` 放配置，`sites-enabled/` 放软链接；这是 Ubuntu nginx 的惯例，方便启停。
- 删除 `default` 是为了避免默认站点抢占 `default_server`。
- **`nginx -t` 必须通过再 reload**；配置写错时 reload 会失败，但旧配置仍在运行，不会立刻断站。

### 6.2 配置里每一段在做什么

- `limit_req_zone ... zone=auth ... rate=10r/m`：在 nginx 层给登录接口限流。应用层还有 5 次/15 分钟的限制，两层是互补的。
- `client_max_body_size 6m`：允许上传 5 MB 图片（multipart 有额外开销，留 1 MB 余量）。没有它，nginx 默认 1 MB 会直接返回 413。
- `location /api/`：把业务请求转给 FastAPI。
- `location = /api/auth/login`：精确匹配登录接口，额外套 `limit_req`。
- `location /uploads/`：用 `alias` 直接读磁盘，不经过 FastAPI。`alias` 和目标目录末尾的 `/` 都要保留。
- `location /`：其余请求交给 Next.js。`Upgrade`/`Connection` 头是给 WebSocket/HMR 预留的，生产环境不使用也不影响。
- `X-Content-Type-Options`、`X-Frame-Options`、`Referrer-Policy`：基础安全头。
- **没有 HSTS**：当前是 HTTP，加 HSTS 没有意义；上 HTTPS 并验证稳定后再加。

### 6.3 自检

```bash
curl -s http://123.206.100.36/api/health
# {"status":"ok"}

curl -I http://123.206.100.36/zh
# HTTP/1.1 200 OK
```

---

## 7. 首次上线验收

按顺序检查：

```bash
sudo systemctl status postgresql myblog-api myblog-web nginx
sudo journalctl -u myblog-api -n 50 --no-pager
sudo journalctl -u myblog-web -n 50 --no-pager
curl -s http://123.206.100.36/api/health
```

浏览器：

1. <http://123.206.100.36/zh> 首页正常；
2. 文章列表、文章详情正常；
3. 访问 <http://123.206.100.36/zh/admin> 会跳到登录页；
4. 用 `.env` 中的管理员账号登录；
5. 新建文章 → 保存草稿 → 发布；
6. 在正文上传一张图片，确认文章和媒体库都能显示；
7. 前台文章列表能看到刚发布的文章；
8. 退出登录。

后台关闭开关的验收（可选）：

```bash
sudo -u myblog nano /srv/my_blog/backend/.env
# ADMIN_ENABLED=false
sudo systemctl restart myblog-api
```

确认后台入口消失、`/api/admin/*` 返回 404，然后改回 `true` 并重启。

---

## 8. 以后的发布流程

每次更新代码：

```bash
# 1. 先备份
pg_dump -h 127.0.0.1 -U blog_user my_blog | gzip > /srv/backups/my_blog_$(date +%F_%H%M).sql.gz

# 2. 拉代码
sudo -u myblog git -C /srv/my_blog pull --ff-only

# 3. 后端依赖/迁移
cd /srv/my_blog/backend
sudo -u myblog venv/bin/pip install -r requirements.txt
sudo -u myblog venv/bin/alembic upgrade head

# 4. 前端构建
cd /srv/my_blog/frontend
sudo -u myblog npm ci
sudo -u myblog npm run build

# 5. 重启
sudo systemctl restart myblog-api myblog-web

# 6. 验证
curl -s http://123.206.100.36/api/health
sudo journalctl -u myblog-api -n 20 --no-pager
sudo journalctl -u myblog-web -n 20 --no-pager
```

为什么顺序是“先备份、再迁移、后 build、最后 restart”：

- 备份放在最前面，迁移失败时可以恢复。
- 迁移成功后再构建前端，避免前端已更新但数据库还是旧结构。
- `restart` 放在最后，只有新代码、新依赖、新构建都就绪才切换。

---

## 9. 备份

### 9.1 配置数据库免交互密码

```bash
sudo -u myblog nano /home/myblog/.pgpass
```

内容（一行）：

```text
127.0.0.1:5432:my_blog:blog_user:数据库密码
```

```bash
sudo chown myblog:myblog /home/myblog/.pgpass
sudo chmod 600 /home/myblog/.pgpass
```

`.pgpass` 是 PostgreSQL 官方支持的免交互密码文件。比把密码写进脚本/crontab 安全。

### 9.2 备份脚本

仓库里的 `deploy/backup.sh` 会：

1. `pg_dump` 导出数据库并 gzip；
2. 打包 `backend/uploads/`；
3. 删除 7 天前的备份。

安装：

```bash
sudo chmod 755 /srv/my_blog/deploy/backup.sh
sudo -u myblog mkdir -p /srv/backups
sudo -u myblog /srv/my_blog/deploy/backup.sh
```

加到 `myblog` 的 crontab：

```bash
sudo -u myblog crontab -e
```

加入：

```cron
0 3 * * * /srv/my_blog/deploy/backup.sh >> /srv/backups/backup.log 2>&1
```

### 9.3 恢复

```bash
# 数据库
gunzip -c /srv/backups/my_blog_2026-10-21.sql.gz | sudo -u postgres psql my_blog

# 上传文件
sudo tar -xzf /srv/backups/uploads_2026-10-21.tar.gz -C /srv/my_blog/backend
sudo chown -R myblog:myblog /srv/my_blog/backend/uploads
```

恢复前先停服务，恢复后再启动，避免写入冲突。

---

## 10. 回滚

### 10.1 代码回滚

```bash
cd /srv/my_blog
sudo -u myblog git log --oneline -5
sudo -u myblog git checkout <上一个稳定提交>
cd frontend
sudo -u myblog npm ci
sudo -u myblog npm run build
sudo systemctl restart myblog-api myblog-web
```

### 10.2 数据库回滚

```bash
cd /srv/my_blog/backend
sudo -u myblog venv/bin/alembic downgrade -1
```

**先备份再 downgrade。** 迁移降级可能丢数据，尤其是删除列/表的迁移。

### 10.3 nginx 回滚

```bash
sudo cp /etc/nginx/sites-available/myblog /srv/backups/nginx-myblog.bak
# 修改/恢复后
sudo nginx -t && sudo systemctl reload nginx
```

---

## 11. 切换到 HTTPS（拿到域名后）

### 11.1 准备域名

1. 买一个域名，或先用免费二级域名做测试。
2. DNS 添加 A 记录指向 `123.206.100.36`。
3. 等待解析生效：`dig +short your-domain.com`。

### 11.2 申请证书

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

certbot 会自动：

- 验证域名归属；
- 修改 nginx 配置，增加 443 和证书路径；
- 可选地把 HTTP 301 到 HTTPS。

证书自动续期由 systemd timer 负责，可用：

```bash
sudo systemctl list-timers | grep certbot
```

### 11.3 修改应用配置

后端 `/srv/my_blog/backend/.env`：

```dotenv
COOKIE_SECURE=true
SITE_ORIGIN=https://your-domain.com
```

前端 `/srv/my_blog/frontend/.env.local`：

```dotenv
NEXT_PUBLIC_SITE_URL=https://your-domain.com
```

重新构建并重启：

```bash
cd /srv/my_blog/frontend
sudo -u myblog npm run build
sudo systemctl restart myblog-api myblog-web
sudo systemctl reload nginx
```

为什么必须改这三处：

- `COOKIE_SECURE=true`：HTTPS 下才发送登录 Cookie。
- `SITE_ORIGIN`：后台写操作校验 Origin，必须与实际访问的 scheme + host 完全一致。
- `NEXT_PUBLIC_SITE_URL`：canonical/OG 元数据和构建产物里的站点地址，必须重新 build。

验证 HTTPS 后再考虑给 nginx 加 HSTS：

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

### 11.4 如果只保留一个域名

在 nginx 里把另一个 301 到主域名，并让 `SITE_ORIGIN` 与主域名一致。
例如主域名是 `example.com`：

```nginx
server {
    listen 80;
    server_name www.example.com;
    return 301 https://example.com$request_uri;
}
```

---

## 12. 故障排查

| 现象 | 可能原因 | 排查 |
|---|---|---|
| 502 Bad Gateway | FastAPI/Next 没启动或端口不对 | `systemctl status myblog-api myblog-web`、`journalctl -u ...`、`ss -ltnp` |
| 504 Gateway Timeout | Next 构建/SSR 太慢或挂起 | 看 `journalctl -u myblog-web`，确认 `npm run build` 成功 |
| 413 Request Entity Too Large | nginx 限制太小 | 确认 `client_max_body_size 6m` 已 reload |
| 后台写操作 403 | `SITE_ORIGIN` 与实际地址不一致 | 必须精确到 scheme + host + 端口；HTTP 是 `http://IP`，HTTPS 是 `https://域名` |
| 登录后立刻又跳登录页 | `COOKIE_SECURE=true` 但当前是 HTTP | 临时改 false 并重启 API；上 HTTPS 后改回 true |
| 500 数据库连接失败 | `.env` 连接串错误、PostgreSQL 未启动 | `systemctl status postgresql`、`sudo -u postgres psql`、检查密码/端口 |
| 上传失败/权限错误 | `uploads` 归错用户 | `chown -R myblog:myblog /srv/my_blog/backend/uploads` |
| `next: not found` | systemd 找不到 npm | 确认 `ExecStart=/usr/bin/npm ...`，`which npm` |
| `ModuleNotFoundError` | 没用 venv 的 python | 所有后端命令都用 `venv/bin/python` / `venv/bin/uvicorn` |
| 页面样式/静态资源 404 | build 产物缺失或 nginx 配置错误 | 重新 `npm run build`，检查 `/` 代理到 3000 |
| 上传的图片 404 | nginx alias 路径不对 | 确认 `/uploads/` 与 `/srv/my_blog/backend/uploads/` 末尾都有 `/` |

---

## 13. 安全检查清单

- [ ] `.env` 权限 600，属主 `myblog`。
- [ ] `.env`、`.env.local` 没有提交到 GitHub。
- [ ] PostgreSQL 只监听 127.0.0.1。
- [ ] FastAPI/Next 只监听 127.0.0.1。
- [ ] ufw 只放行 SSH / HTTP(S)。
- [ ] 管理员密码 ≥12 位且不是默认值。
- [ ] `JWT_SECRET`、`IP_HASH_SALT` 是随机值。
- [ ] 生产库没有运行 `seed_demo` / pytest / Playwright。
- [ ] 每天有数据库和 uploads 备份。
- [ ] 拿到域名后尽快切 HTTPS，并把 `COOKIE_SECURE` 改回 true。

---

## 14. 常用命令速查

```bash
# 服务
sudo systemctl status myblog-api myblog-web nginx postgresql
sudo systemctl restart myblog-api myblog-web
sudo systemctl reload nginx

# 日志
sudo journalctl -u myblog-api -f
sudo journalctl -u myblog-web -f
sudo journalctl -u myblog-api --since "10 minutes ago"

# 配置检查
sudo nginx -t
sudo -u myblog venv/bin/alembic current

# 健康检查
curl -s http://123.206.100.36/api/health
curl -I http://123.206.100.36/zh

# 代码
sudo -u myblog git -C /srv/my_blog status
sudo -u myblog git -C /srv/my_blog pull --ff-only
```
