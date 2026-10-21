import 'server-only';

const API_BASE_URL = (
  process.env.API_BASE_URL ?? 'http://127.0.0.1:8000'
).replace(/\/+$/, '');

export type Tag = {
  name: string;
  slug: string;
};

export type PostListItem = {
  slug: string;
  title: string;
  excerpt: string;
  cover_url: string | null;
  language: 'zh' | 'en';
  published_at: string | null;
  view_count: number;
  tags: Tag[];
};

export type PostListResponse = {
  items: PostListItem[];
  total: number;
  page: number;
  page_size: number;
};

export type PostDetail = PostListItem & {
  content_md: string;
  updated_at: string;
};

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly path: string,
    readonly detail?: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function fetchApi<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {cache: 'no-store'});
  if (!response.ok) {
    let detail: string | undefined;
    try {
      const body = (await response.json()) as {detail?: unknown};
      if (typeof body.detail === 'string') {
        detail = body.detail;
      }
    } catch {
      // 非 JSON 错误体，忽略解析失败
    }
    throw new ApiError(
      `API ${response.status}: ${response.statusText}`,
      response.status,
      path,
      detail
    );
  }
  return response.json() as Promise<T>;
}

export async function getPosts(params?: {
  page?: number;
  pageSize?: number;
  tag?: string;
  language?: PostListItem['language'];
}): Promise<PostListResponse> {
  const search = new URLSearchParams();
  if (params?.page !== undefined) search.set('page', String(params.page));
  if (params?.pageSize !== undefined)
    search.set('page_size', String(params.pageSize));
  if (params?.tag) search.set('tag', params.tag);
  if (params?.language) search.set('language', params.language);
  const query = search.toString();
  return fetchApi<PostListResponse>(`/api/posts${query ? `?${query}` : ''}`);
}

export async function getPost(slug: string): Promise<PostDetail> {
  return fetchApi<PostDetail>(`/api/posts/${encodeURIComponent(slug)}`);
}

export async function getPostOrNull(
  slug: string
): Promise<PostDetail | null> {
  try {
    return await getPost(slug);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

export type ProjectListItem = {
  slug: string;
  title: string;
  summary: string;
  cover_url: string | null;
  tech_stack: string[];
  featured: boolean;
  started_on: string | null;
  ended_on: string | null;
};

export type ProjectDetail = ProjectListItem & {
  content_md: string;
  repo_url: string | null;
  demo_url: string | null;
};

export type ProjectLocale = 'zh' | 'en';

export async function getProjects(params: {
  locale: ProjectLocale;
  featured?: boolean;
}): Promise<ProjectListItem[]> {
  const search = new URLSearchParams();
  search.set('locale', params.locale);
  if (params.featured) search.set('featured', 'true');
  return fetchApi<ProjectListItem[]>(`/api/projects?${search.toString()}`);
}

export async function getProject(
  slug: string,
  locale: ProjectLocale
): Promise<ProjectDetail> {
  const search = new URLSearchParams();
  search.set('locale', locale);
  return fetchApi<ProjectDetail>(
    `/api/projects/${encodeURIComponent(slug)}?${search.toString()}`
  );
}

export async function getProjectOrNull(
  slug: string,
  locale: ProjectLocale
): Promise<ProjectDetail | null> {
  try {
    return await getProject(slug, locale);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

export type SiteConfigResponse = {
  admin_enabled: boolean;
};

export async function getSiteConfig(): Promise<SiteConfigResponse> {
  return fetchApi<SiteConfigResponse>('/api/site/config');
}
