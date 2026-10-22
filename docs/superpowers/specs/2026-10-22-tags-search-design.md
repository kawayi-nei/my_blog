# 标签管理与站内搜索设计

- 日期：2026-10-22
- 状态：已确认
- 项目目录：`Z:\my_blog`
- 关联文档：`docs/superpowers/specs/2026-10-19-personal-blog-design.md`

## 1. 目标与范围

### 1.1 目标

完成总体设计中的计划 3B：

1. 后台标签管理：创建、改名、删除。
2. 公开站点标签入口：独立标签页 `/{locale}/tags/[slug]`，文章列表展示标签筛选。
3. 站内搜索：文章 + 项目，分组展示结果。

### 1.2 成功标准

- 管理员可在后台创建、改名、删除标签；删除标签不删除文章。
- 访客可从文章列表或文章卡片进入标签页，看到该标签下的已发布文章并可分页。
- 访客可搜索文章标题/摘要/正文和项目对应语言字段，草稿不出现。
- 现有公开页、后台、测试基线不回退。

### 1.3 非目标

- 标签合并、标签层级、旧 slug 重定向。
- 搜索分页、结果高亮、自动补全、搜索历史。
- 外部搜索引擎或 PostgreSQL 全文检索扩展。
- 为项目表新增 trigram 索引（数据量小时顺序扫描可接受）。
- 公开页面 SEO 元数据（留给计划 3E）。

## 2. 现状与差距

已有：

- `GET /api/tags` 返回 `{name, slug, post_count}`，`post_count` 只统计已发布文章。
- `GET /api/posts` 已支持 `tag`（slug）和 `language` 查询参数。
- 后台 `GET /api/admin/tags`、`POST /api/admin/tags`；文章表单内可顺手创建标签。
- 文章表已有 `title`、`excerpt`、`content_md` 的 GIN trigram 索引。

缺少：

- 后台标签改名的更新接口、删除接口，以及管理页面。
- 公开标签页与前端标签入口；文章卡片上的标签目前是不可点击文本。
- `/api/search`、搜索页、页头搜索入口。

## 3. 后端设计

### 3.1 后台标签管理

沿用 `app/api/admin/tags.py`、`app/services/admin_tags.py`、`app/schemas/admin_tag.py` 现有分层。

**Schema**

```python
class AdminTagRef(BaseModel):
    id: int
    name: str
    slug: str


class AdminTagOut(AdminTagRef):
    post_count: int


class AdminTagUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    slug: str | None = Field(
        default=None, min_length=1, max_length=50, pattern=r"^[a-z0-9-]+$"
    )

    # name 与 slug 至少提供一个，否则 422
```

`post_count` 统计该标签关联的全部文章（含草稿），用于管理页删除前提示影响面。创建后的响应 `post_count` 为 0。

后台文章接口（`AdminPostListItem.tags`）继续使用轻量 `AdminTagRef`，不复用 `AdminTagOut`，避免文章序列化时强制要求 `post_count`。

**接口**

| 方法 | 路径 | 行为 |
|---|---|---|
| GET | `/api/admin/tags` | 列表，按名称、id 排序，每项含 `post_count` |
| POST | `/api/admin/tags` | 现有行为，响应改为含 `post_count` |
| PATCH | `/api/admin/tags/{tag_id}` | 部分更新 `name`/`slug`；至少一个字段；返回更新后的标签 |
| DELETE | `/api/admin/tags/{tag_id}` | 删除标签，返回 204 |

**规则**

- PATCH 未提供的字段保持不变；显式 `null` 视为未提供。
- 唯一性检查排除自身：`name` 或 `slug` 与其他标签冲突返回 409；并发下捕获 `IntegrityError` 同样返回 409。
- 标签不存在返回 404。
- DELETE 依赖 `post_tags` 外键 `ON DELETE CASCADE` 解除关联，文章保留。
- 所有接口继承 `/api/admin` 现有的管理员登录与同源校验。

**实现要点**

- `AdminTagOut.post_count` 使创建/更新接口也需要计数；新建标签计数为 0，更新后查询一次关联数。
- 列表查询使用 `outerjoin(post_tags)` + `count(Post.id)` + `group_by(Tag.id)`，与公开标签计数写法一致，但不加 `status='published'` 条件。

### 3.2 公开标签读取

不新增公开标签详情接口。标签页通过现有 `GET /api/tags` 查找 slug：

- 找到：使用其 `name` 与 `post_count` 渲染标题。
- 找不到：页面返回 404。

标签页文章列表调用现有 `GET /api/posts?tag=<slug>&page=N`，无需后端改动。

### 3.3 站内搜索

**模块**

- `backend/app/schemas/search.py`：`SearchResponse`
- `backend/app/services/search.py`：查询与排序
- `backend/app/api/public/search.py`：路由
- `backend/app/main.py`：注册 `/api/search`

**请求**

```
GET /api/search?q=<关键词>&locale=zh
```

- `q` 必填，最大 100 字符；去除首尾空白后为空时返回空结果（200），不报错。
- 缺失 `q` 或超过 100 字符返回 422。
- `locale` 只允许 `zh`/`en`，默认 `zh`，只影响项目搜索字段与项目结果本地化。

**响应**

```json
{
  "posts": [
    {
      "slug": "first-post",
      "title": "第一篇测试文章",
      "excerpt": "用于本地开发验证的文章。",
      "cover_url": null,
      "language": "zh",
      "published_at": "2026-10-22T02:00:00Z",
      "view_count": 0,
      "tags": [{"name": "后端", "slug": "backend"}]
    }
  ],
  "projects": [
    {
      "slug": "demo-project",
      "title": "示例项目",
      "summary": "项目摘要",
      "cover_url": null,
      "tech_stack": ["FastAPI"],
      "featured": true,
      "started_on": "2026-01-01",
      "ended_on": null
    }
  ],
  "total": 2
}
```

- `posts` 复用 `PostListItem`；`projects` 复用本地化后的 `ProjectListItem`。
- 每组最多 10 条，`total` 为两组长度之和（最大 20）。

**匹配**

- 文章：`status='published'`，匹配 `title`、`excerpt`、`content_md`。
- 项目：`status='published'`，按 `locale` 匹配 `title_{locale}`、`summary_{locale}`、`content_md_{locale}`。
- 项目结果的标题必须双语非空，因此本地化标题直接取对应语言；摘要按现有 `localize_project` 回退规则。

**排序**

- 两组都先按 `greatest(similarity(<字段1>, q), similarity(<字段2>, q), ...)` 降序。
- 文章次序：发布时间降序、id 降序。
- 项目次序：`featured` 降序、`sort_order` 升序、id 降序。

**LIKE 转义**

- `ILIKE` 使用 SQLAlchemy 参数绑定。
- 用户输入中的 `\`、`%`、`_` 在构造模式串前转义，并使用 `escape="\\"`，避免 `%`/`_` 变成通配符。
- `similarity()` 使用原始 `q`，不使用转义后的模式串。

**查询实现**

- 使用 `select(Post).where(...)` 与 `select(Project).where(...)` 分别查询，各 `limit(10)`。
- 文章查询保留 `selectin` 标签加载；不返回正文。
- 项目通过 `localize_project(project, locale)` 转换为响应模型。

## 4. 前端设计

### 4.1 共用文章列表

从 `frontend/src/app/[locale]/(site)/posts/page.tsx` 抽出 `frontend/src/components/post-list.tsx`（服务端组件）：

```ts
type PostListProps = {
  items: PostListItem[];
  total: number;
  page: number;
  pageSize: number;
  basePath?: string;   // 默认 "/posts"
  emptyText: string;
};
```

- 负责空状态、文章卡片列表、上一页/下一页。
- 分页链接为 `${basePath}?page=N`。
- `/posts` 与标签页共用；抽出的同时保持现有视觉与行为不变。

### 4.2 标签入口与标签页

`/posts`：

- 并行请求文章列表与 `GET /api/tags`。
- 标题下渲染标签 chips：只显示 `post_count > 0` 的标签，文案 `#名称 N`，链接到 `/{locale}/tags/{slug}`。
- 无标签时不渲染 chips。

`PostCard`：

- `#标签` 从 `<span>` 改为指向标签页的 `Link`。
- 仍位于文章卡片内部，但独立于标题链接，不嵌套 `<a>`。

新增 `frontend/src/app/[locale]/(site)/tags/[slug]/page.tsx`：

- 读取 `params.slug` 与 `searchParams.page`。
- 从 `getTags()` 找到标签；找不到 `notFound()`。
- 请求 `getPosts({tag: slug, page})`；标题显示 `> #标签名_` 与文章数。
- 使用 `PostList`，`basePath="/tags/{slug}"`。
- 页码超过最后一页时返回 404，行为与 `/posts` 一致。

### 4.3 搜索页

新增 `frontend/src/app/[locale]/(site)/search/page.tsx`（服务端渲染）：

- 读取 `searchParams.q`；数组取第一个。
- 顶部为 GET 表单，`action` 为 `/{locale}/search`，输入框 `name="q"`、`maxLength={100}`，有可见 label 与占位文案。
- `q` 为空：显示「输入关键词开始搜索」，不请求 API。
- 有 `q`：调用 `search({q, locale})`，显示结果总数。
- 结果分「文章」「项目」两组：
  - 文章复用 `PostCard`。
  - 项目复用 `ProjectCard`。
  - 某组为空时不渲染该组标题。
- 无任何结果时显示空状态。不做分页。

页头 `SiteHeader` 导航新增「搜索」链接到 `/search`，位置在「文章」之后。

### 4.4 后台标签管理页

新增 `frontend/src/app/[locale]/admin/(protected)/tags/page.tsx`：

- 服务端调用 `getAdminTags()`，渲染客户端 `TagManager`。
- 后台导航新增「标签」。

新增 `frontend/src/components/admin/tag-manager.tsx`（客户端）：

- 顶部创建表单：名称 + slug，提交 `POST /api/admin/tags`。
- 列表每行显示名称、slug、`post_count`，操作为「编辑」「删除」。
- 编辑：行内切换为两个输入框，保存发 `PATCH /api/admin/tags/{id}`，取消恢复原值。
- 删除：`confirm` 提示「确定删除标签《名称》？将影响 N 篇文章，文章不会被删除。」成功发 `DELETE`，返回 204 后从列表移除。
- 错误处理：
  - 401 跳转登录页。
  - 409 显示「名称或 slug 已存在」。
  - 422 显示「输入不合法」。
  - 其他失败显示通用错误。
- 创建与编辑成功后同步本地状态，不整页刷新。

### 4.5 API 客户端与类型

`frontend/src/lib/api.ts` 新增：

```ts
export type TagWithCount = Tag & {post_count: number};
export function getTags(): Promise<TagWithCount[]>;

export type SearchResponse = {
  posts: PostListItem[];
  projects: ProjectListItem[];
  total: number;
};
export function search(params: {
  q: string;
  locale: ProjectLocale;
}): Promise<SearchResponse>;
```

`frontend/src/lib/admin-types.ts`：

```ts
export type AdminTag = {id: number; name: string; slug: string; post_count: number};
```

`frontend/src/lib/admin-api.ts` 保持不变，`getAdminTags()` 自然返回新字段。

### 4.6 文案

`frontend/src/messages/zh.json` 与 `en.json` 新增：

- `nav.search`
- `tags.title`、`tags.count`、`tags.empty`、`tags.back`
- `search.title`、`search.placeholder`、`search.submit`、`search.prompt`、`search.empty`、`search.resultCount`、`search.posts`、`search.projects`
- `admin.nav.tags`
- `admin.tags.title`、`admin.tags.create`、`admin.tags.name`、`admin.tags.slug`、`admin.tags.postCount`、`admin.tags.edit`、`admin.tags.save`、`admin.tags.cancel`、`admin.tags.delete`、`admin.tags.confirmDelete`、`admin.tags.empty`、`admin.tags.conflict`、`admin.tags.invalid`、`admin.tags.createFailed`、`admin.tags.saveFailed`、`admin.tags.deleteFailed`

## 5. 错误处理与安全

- 搜索与标签页均为公开只读接口，无需鉴权。
- 搜索参数全部参数化；LIKE 特殊字符转义。
- 后台写操作继续经过 `require_admin` 与 `require_same_origin`。
- 标签页未知 slug 返回 404；搜索空白词返回空结果而非报错。
- 前端不渲染原始 HTML，不引入新依赖。
- 只读页面服务端请求失败沿用现有 locale 级错误页，不新增 error boundary。

## 6. 测试策略

### 6.1 后端 pytest

`backend/tests/test_admin_tags.py` 扩展：

- 列表与创建响应包含 `post_count`。
- `post_count` 统计已发布与草稿文章。
- PATCH 改名、改 slug、同时修改。
- PATCH 只提交与自身相同的 name/slug 不冲突。
- PATCH 与其他标签重名/重 slug 返回 409。
- PATCH 不存在的标签返回 404。
- PATCH 空 payload 返回 422。
- DELETE 后标签消失、文章仍存在、`post_tags` 关联消失。
- DELETE 不存在的标签返回 404。

新增 `backend/tests/test_search.py`：

- 按标题、摘要、正文命中已发布文章。
- 草稿不出现在文章结果中。
- 按 `locale` 命中项目对应语言字段；另一语言字段不命中。
- 草稿项目不出现。
- 空白 `q` 返回空结果；缺少 `q`、超长 `q` 返回 422。
- 每组最多 10 条。
- `%`、`_` 按字面量匹配，不作为通配符。
- 标题命中排在仅正文命中之前。
- 项目结果按 `featured`、`sort_order` 排序。

### 6.2 前端 Playwright

新增 `frontend/e2e/tags.spec.ts`：

- 后台：登录 → 创建唯一标签 → 行内改名 → 删除 → 列表消失。
- 公开：文章列表点击标签 chip → `/zh/tags/backend` 显示演示文章；访问未知标签得到 404 页面。

新增 `frontend/e2e/search.spec.ts`：

- `/zh/search?q=第一篇` 显示演示文章结果。
- 无 `q` 时显示提示且无结果列表。
- 项目搜索由后端测试覆盖，避免 E2E 依赖其他用例留下的项目数据。

### 6.3 回归

- 后端基线：69 passed 基础上新增用例全部通过。
- 前端基线：6 passed 基础上新增用例全部通过。
- `npm run build` 成功。

## 7. 验收清单

- [ ] 后台可创建、改名、删除标签；删除后文章保留、关联解除。
- [ ] 后台标签列表显示每项关联文章数。
- [ ] 文章列表显示标签 chips，点击进入对应标签页。
- [ ] 文章卡片上的标签可点击。
- [ ] 标签页只显示该标签的已发布文章，支持分页；未知标签 404。
- [ ] 搜索页可按关键词返回文章与项目两组结果，草稿不出现。
- [ ] 搜索空查询显示提示，无结果有空状态。
- [ ] 页头有搜索入口。
- [ ] 后端 pytest、Playwright、`npm run build` 全部通过。

## 8. 部署影响

- 无数据库迁移、无新依赖。
- 服务器更新：bundle → `git pull --ff-only` → `npm run build` → 重启 `myblog-api`、`myblog-web`；不需要 `npm ci` 或 `alembic upgrade`。
- 新功能上线后验证 `/api/search?q=...`、`/zh/tags/backend`、`/zh/search?q=...`。

## 9. 风险与权衡

| 风险 | 权衡 |
|---|---|
| 中文 `similarity()` 相关性有限 | 与总体设计一致；数据量增大后再评估 Meilisearch |
| 项目搜索无 trigram 索引 | 项目数量少，顺序扫描成本可忽略；后续可加迁移 |
| 改 slug 后旧链接失效 | 个人站规模小，已确认不做重定向 |
| 搜索无分页 | 每组封顶 10 条，个人站结果量小；后续需要再加 |
| `AdminTagOut` 增加字段影响旧调用 | 仅前端消费，字段为新增；现有测试按包含关系可继续通过 |
