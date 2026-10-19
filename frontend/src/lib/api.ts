const API_BASE_URL = process.env.API_BASE_URL ?? 'http://127.0.0.1:8000';

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

async function fetchApi<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {cache: 'no-store'});
  if (!response.ok) {
    throw new Error(`API ${response.status}: ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export async function getPosts(params?: {
  page?: number;
  pageSize?: number;
  tag?: string;
  language?: string;
}): Promise<PostListResponse> {
  const search = new URLSearchParams();
  if (params?.page) search.set('page', String(params.page));
  if (params?.pageSize) search.set('page_size', String(params.pageSize));
  if (params?.tag) search.set('tag', params.tag);
  if (params?.language) search.set('language', params.language);
  const query = search.toString();
  return fetchApi<PostListResponse>(`/api/posts${query ? `?${query}` : ''}`);
}

export async function getPost(slug: string): Promise<PostDetail> {
  return fetchApi<PostDetail>(`/api/posts/${encodeURIComponent(slug)}`);
}

export async function getSiteConfig(): Promise<{admin_enabled: boolean}> {
  return fetchApi<{admin_enabled: boolean}>('/api/site/config');
}
