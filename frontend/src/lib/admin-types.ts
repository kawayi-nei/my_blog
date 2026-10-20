export type AdminTag = {
  id: number;
  name: string;
  slug: string;
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
  tags: AdminTag[];
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
