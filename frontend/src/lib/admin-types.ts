export type AdminTagRef = {
  id: number;
  name: string;
  slug: string;
};

export type AdminTag = AdminTagRef & {
  post_count: number;
};

export type AdminPostListItem = {
  id: number;
  slug: string;
  title: string;
  excerpt: string;
  language: 'zh' | 'en';
  status: 'draft' | 'published';
  published_at: string | null;
  updated_at: string;
  tags: AdminTagRef[];
};

export type AdminPostDetail = AdminPostListItem & {
  content_md: string;
  created_at: string;
};

export type AdminPostListResponse = {
  items: AdminPostListItem[];
  total: number;
  page: number;
  page_size: number;
};

export type MediaItem = {
  id: number;
  url: string;
  filename: string;
  original_name: string;
  mime: string;
  size_bytes: number;
  created_at: string;
};

export type MediaListResponse = {
  items: MediaItem[];
  total: number;
  page: number;
  page_size: number;
};

export type AdminProjectListItem = {
  id: number;
  slug: string;
  title_zh: string;
  title_en: string;
  status: 'draft' | 'published';
  featured: boolean;
  sort_order: number;
  started_on: string | null;
  ended_on: string | null;
  cover_url: string | null;
  updated_at: string;
};

export type AdminProjectDetail = AdminProjectListItem & {
  summary_zh: string;
  summary_en: string;
  content_md_zh: string;
  content_md_en: string;
  tech_stack: string[];
  repo_url: string | null;
  demo_url: string | null;
  created_at: string;
};

export type AdminProjectListResponse = {
  items: AdminProjectListItem[];
  total: number;
  page: number;
  page_size: number;
};
