# 计划 3A：作品集设计

- 日期：2026-10-21
- 状态：已确认
- 分支：`feature/projects`
- 上游设计：`docs/superpowers/specs/2026-10-19-personal-blog-design.md`（§6.5、§7.4、§13）

## 1. 目标与范围

在现有文章系统之上增加「作品集」：

- 后台项目管理：双语内容、封面、技术栈、Repo/Demo 链接、起止日期、精选与排序、草稿/发布、删除；
- 公开页面：项目列表、项目详情；
- 首页「精选项目」区块；
- 页头与后台导航新增项目入口。

### 1.1 本次包含

- `projects` 表与迁移；
- 公开项目列表/详情 API；
- 后台项目 CRUD API；
- 后台项目列表、新建/编辑表单、封面选择器；
- 前台项目列表/详情、首页精选；
- 后端 pytest 与 Playwright 覆盖。

### 1.2 本次不包含

- 标签管理页、站内搜索、评论、阅读统计、简历/关于、SEO；
- 项目分页（项目数量少，公开列表不 paginate）；
- 封面裁剪/压缩/对象存储；
- 项目标签。

## 2. 数据模型

新增表 `projects`，迁移 `0003_projects`。

| 字段 | 类型 | 约束 |
|---|---|---|
| id | BIGSERIAL | PK |
| slug | VARCHAR(200) | UNIQUE, NOT NULL，`^[a-z0-9-]+$` |
| title_zh | VARCHAR(200) | NOT NULL |
| title_en | VARCHAR(200) | NOT NULL |
| summary_zh | VARCHAR(500) | NOT NULL，默认空串 |
| summary_en | VARCHAR(500) | NOT NULL，默认空串 |
| content_md_zh | TEXT | NOT NULL，默认空串 |
| content_md_en | TEXT | NOT NULL，默认空串 |
| cover_url | VARCHAR(500) | NULL |
| tech_stack | TEXT[] | NOT NULL，默认空数组 |
| repo_url | VARCHAR(500) | NULL |
| demo_url | VARCHAR(500) | NULL |
| started_on | DATE | NULL |
| ended_on | DATE | NULL |
| featured | BOOLEAN | NOT NULL，默认 false |
| sort_order | INTEGER | NOT NULL，默认 0 |
| status | VARCHAR(10) | NOT NULL，CHECK IN ('draft','published') |
| created_at | TIMESTAMPTZ | NOT NULL，默认 now() |
| updated_at | TIMESTAMPTZ | NOT NULL，默认 now() |

约束与索引：

- `ck_projects_status`：`status IN ('draft','published')`
- `ck_projects_slug_format`：`slug ~ '^[a-z0-9-]+$'`
- `UNIQUE (slug)`
- `ix_projects_public_order`：`(status, featured DESC, sort_order ASC, started_on DESC NULLS LAST)`

业务规则：

- `sort_order` 越小越靠前；
- 删除为硬删除；`cover_url` 指向的媒体文件不自动删除，仍保留在媒体库；
- 发布不额外记录时间，前台只按 `status='published'` 过滤。

## 3. 公开 API

### 3.1 项目列表

`GET /api/projects`

查询参数：

- `featured`：可选布尔值；为 true 时只返回精选项目；
- `locale`：`zh` 或 `en`，默认 `zh`。

行为：

- 仅返回 `status='published'`；
- 排序：`featured DESC, sort_order ASC, started_on DESC NULLS LAST, id DESC`；
- 不分页，返回列表。

响应：

```json
[
  {
    "slug": "remote-sensing-water",
    "title": "遥感水体分割",
    "summary": "用深度学习提取遥感影像中的水体。",
    "cover_url": "/uploads/2026/10/xxxx.png",
    "tech_stack": ["PyTorch", "FastAPI"],
    "featured": true,
    "started_on": "2026-03-01",
    "ended_on": null
  }
]
```

### 3.2 项目详情

`GET /api/projects/{slug}?locale=zh`

- 仅 `status='published'`；草稿或不存在返回 404；
- 返回本地化后的标题/摘要/正文，以及封面、技术栈、Repo/Demo、日期、featured。

响应在列表字段基础上增加：

```json
{
  "content_md": "# 项目背景\n...",
  "repo_url": "https://github.com/...",
  "demo_url": null
}
```

### 3.3 本地化规则

- 请求语言为 `zh` 时使用 `*_zh`，为 `en` 时使用 `*_en`；
- `title`：必须双语，直接使用请求语言，不回退；
- `summary`：请求语言为空时使用另一语言；两者都空则为 `""`；
- `content_md`：同 summary；
- 不返回另一语言的原始字段，前端只消费本地化结果。

## 4. 后台 API

所有接口在 `/api/admin/projects` 下，自动继承现有 `require_admin` 与 `require_same_origin`。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/admin/projects` | `status`、`q`、`page`、`page_size` |
| POST | `/api/admin/projects` | 创建，201 |
| GET | `/api/admin/projects/{id}` | 详情，404 |
| PATCH | `/api/admin/projects/{id}` | 部分更新 |
| DELETE | `/api/admin/projects/{id}` | 硬删除，204 |

列表：

- `q` 对 `slug`、`title_zh`、`title_en` 做 ILIKE；
- 排序 `updated_at DESC, id DESC`；
- 返回 `{items, total, page, page_size}`；
- 列表项包含 `id, slug, title_zh, title_en, status, featured, sort_order, started_on, ended_on, updated_at, cover_url`。

写入字段与校验：

- `slug`：1–200，`^[a-z0-9-]+$`，唯一；冲突 409；
- `title_zh`、`title_en`：1–200 字符，必填；
- `summary_zh`、`summary_en`：≤500，默认空串；
- `content_md_zh`、`content_md_en`：字符串，默认空串；
- `cover_url`：≤500，可空；
- `tech_stack`：字符串数组，默认空；每项 trim 后去掉空串、按原顺序去重，每项 ≤50，最多 20 项；
- `repo_url`、`demo_url`：≤500，可空；
- `started_on`、`ended_on`：日期，可空；两者都有且 `ended_on < started_on` 时 422；
- `featured`：布尔，默认 false；
- `sort_order`：整数，默认 0；
- `status`：`draft` / `published`，默认 draft。

更新为部分更新；显式传 `null` 对可空字段生效（如清空日期/链接），对非空字段忽略。

## 5. 前端公开页

### 5.1 导航与首页

- `SiteHeader` 新增「作品集 / Projects」入口，指向 `/projects`；
- 首页在 Hero 与「最新文章」之间增加「精选项目 / Featured projects」：
  - 调用 `GET /api/projects?featured=true&locale={locale}`；
  - 最多展示 3 个；
  - 没有精选项目时整块隐藏。

### 5.2 项目列表 `/projects`

- 卡片显示：封面（有则显示）、标题、摘要、技术栈 chips、起止时间、featured 标记；
- 空状态文案；
- 卡片链接到 `/projects/{slug}`。

### 5.3 项目详情 `/projects/{slug}`

- 封面、标题、摘要、技术栈、Repo/Demo 链接、起止时间；
- Markdown 正文，复用现有 `Markdown` 组件（不渲染原始 HTML）；
- `generateMetadata` 使用本地化 title/summary；
- 草稿/不存在 404。

### 5.4 数据访问

在 `frontend/src/lib/api.ts` 增加：

- `getProjects({featured?, locale})`
- `getProject(slug, locale)`
- `getProjectOrNull(slug, locale)`（仅 404 返回 null）

## 6. 后台项目管理

### 6.1 页面

- 后台导航新增「项目」；
- `/admin/projects`：列表、状态筛选、搜索、分页、编辑、删除；
- `/admin/projects/new`、`/admin/projects/[id]/edit`。

### 6.2 表单

共享字段：

- slug（新建时按 `title_en` 建议，可手改）；
- 状态、featured、sort_order；
- started_on、ended_on（`<input type="date">`）；
- tech_stack（逗号分隔输入，提交时转数组）；
- repo_url、demo_url；
- 封面：预览、上传、从媒体库选择、清除。

双语区域：

- 中文：title_zh、summary_zh、content_md_zh；
- 英文：title_en、summary_en、content_md_en；
- 两个 Markdown 编辑器复用 `MarkdownEditor`。

保存：

- 新建 POST，编辑 PATCH；
- 401 跳登录，409 slug 冲突，422 表单不合法，其他显示保存失败；
- 新建成功跳编辑页；编辑成功显示「已保存」；
- 删除需确认。

### 6.3 封面选择器

新增 `CoverPicker` 客户端组件：

- 显示当前封面预览与「清除」；
- 「上传图片」：`POST /api/admin/uploads`，成功后写入返回的 `url`；
- 「从媒体库选择」：展开内联网格，客户端请求 `GET /api/admin/media?page_size=100`，点选图片写入 `cover_url`；
- 401 跳登录；上传/加载失败显示错误；
- 没有媒体时提示先上传。

### 6.4 后台数据访问

`frontend/src/lib/admin-api.ts` 增加：

- `getAdminProjects(params)`
- `getAdminProject(id)`
- `getAdminProjectOrNull(id)`

`frontend/src/lib/admin-types.ts` 增加项目类型。

## 7. 国际化

新增中英文文案：

- `nav.projects`
- `admin.nav.projects`
- `public projects`：列表标题、空状态、精选、Repo/Demo、起止时间
- `admin.projects`：列表、表单、封面选择器、错误提示

所有界面文案走 `messages/{zh,en}.json`，组件中不写死中文。

## 8. 测试策略

### 8.1 后端

新增测试覆盖：

- 创建草稿/已发布；
- 公开列表只返回已发布；
- `featured=true` 过滤；
- 公开列表排序；
- 草稿详情 404；
- 本地化：summary/content 回退；title 不回退（必须双语）；
- 后台列表 status/q/分页；
- 更新部分字段、slug 冲突 409、非法 slug 422；
- `tech_stack` 去空/去重、超过 20 项 422；
- `ended_on < started_on` 422；
- 删除 204 与 404。

更新 `conftest.py`：

- 迁移冒烟测试 DROP 语句与表断言加入 `projects`。

### 8.2 Playwright

新增 1 条主流程：

- 登录后台 → 新建项目（填写中英文标题/摘要/正文、技术栈）→ 发布；
- 前台 `/zh/projects` 可见；
- 详情页标题与正文可见；
- 删除后前台消失。

总用例数：6。

### 8.3 验证命令

```bash
cd Z:/my_blog/backend
"venv/Scripts/python.exe" -m pytest -q

cd Z:/my_blog/frontend
npm run build
npm run test:e2e
```

## 9. 风险与注意事项

- **封面 URL 来源**：后台选择器只写入本地上传的 `/uploads/...`；API 仍接受任意字符串，外部 URL 可能影响图片优化，前端展示使用 `unoptimized`。
- **双语内容容易只填一半**：标题必填双语；摘要/正文允许回退，但后台表单会明确分中英文两块。
- **公开列表不分页**：项目数量预计很小；若未来超过 100 个再增加分页。
- **删除项目不删封面文件**：封面可能被多篇文章/项目复用；需要时在媒体库手动删除。
- **日期时区**：项目日期是纯日期，不含时区；前端按原值展示，不做时区转换。
- **迁移顺序**：0003 依赖 0002；生产发布前先备份数据库。

## 10. 验收标准

- 后台可以创建、编辑、发布、撤回、删除项目；
- 双语内容与回退规则正确；
- 首页只展示精选项目，最多 3 个；
- 项目列表/详情只展示已发布项目；
- 封面可上传、从媒体库选择、清除并在前台展示；
- 后端 pytest 全部通过；
- Playwright 6 条全部通过；
- `npm run build` 成功。
