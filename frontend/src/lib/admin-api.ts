import 'server-only';
import {cookies} from 'next/headers';
import {ApiError} from '@/lib/api';
import type {
  AdminPostDetail,
  AdminPostListResponse,
  AdminProjectDetail,
  AdminProjectListResponse,
  AdminTag,
  MediaListResponse
} from '@/lib/admin-types';

const API_BASE_URL = (
  process.env.API_BASE_URL ?? 'http://127.0.0.1:8000'
).replace(/\/+$/, '');

async function adminFetch<T>(path: string): Promise<T> {
  const cookieStore = await cookies();
  const cookie = cookieStore.toString();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    cache: 'no-store',
    headers: cookie ? {cookie} : undefined
  });

  if (!response.ok) {
    let detail: string | undefined;
    try {
      const body = (await response.json()) as {detail?: unknown};
      if (typeof body.detail === 'string') detail = body.detail;
    } catch {
      // 非 JSON 错误体
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

export async function getMe(): Promise<{username: string} | null> {
  try {
    return await adminFetch<{username: string}>('/api/auth/me');
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return null;
    throw error;
  }
}

export async function getAdminPosts(params?: {
  page?: number;
  pageSize?: number;
  status?: string;
  q?: string;
}): Promise<AdminPostListResponse> {
  const search = new URLSearchParams();
  if (params?.page !== undefined) search.set('page', String(params.page));
  if (params?.pageSize !== undefined)
    search.set('page_size', String(params.pageSize));
  if (params?.status) search.set('status', params.status);
  if (params?.q) search.set('q', params.q);
  const query = search.toString();
  return adminFetch<AdminPostListResponse>(
    `/api/admin/posts${query ? `?${query}` : ''}`
  );
}

export async function getAdminPost(id: number): Promise<AdminPostDetail> {
  return adminFetch<AdminPostDetail>(`/api/admin/posts/${id}`);
}

export async function getAdminPostOrNull(
  id: number
): Promise<AdminPostDetail | null> {
  try {
    return await getAdminPost(id);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

export async function getAdminTags(): Promise<AdminTag[]> {
  return adminFetch<AdminTag[]>('/api/admin/tags');
}

export async function getMediaList(params?: {
  page?: number;
  pageSize?: number;
}): Promise<MediaListResponse> {
  const search = new URLSearchParams();
  if (params?.page !== undefined) search.set('page', String(params.page));
  if (params?.pageSize !== undefined)
    search.set('page_size', String(params.pageSize));
  const query = search.toString();
  return adminFetch<MediaListResponse>(
    `/api/admin/media${query ? `?${query}` : ''}`
  );
}

export async function getAdminProjects(params?: {
  page?: number;
  pageSize?: number;
  status?: string;
  q?: string;
}): Promise<AdminProjectListResponse> {
  const search = new URLSearchParams();
  if (params?.page !== undefined) search.set('page', String(params.page));
  if (params?.pageSize !== undefined)
    search.set('page_size', String(params.pageSize));
  if (params?.status) search.set('status', params.status);
  if (params?.q) search.set('q', params.q);
  const query = search.toString();
  return adminFetch<AdminProjectListResponse>(
    `/api/admin/projects${query ? `?${query}` : ''}`
  );
}

export async function getAdminProject(
  id: number
): Promise<AdminProjectDetail> {
  return adminFetch<AdminProjectDetail>(`/api/admin/projects/${id}`);
}

export async function getAdminProjectOrNull(
  id: number
): Promise<AdminProjectDetail | null> {
  try {
    return await getAdminProject(id);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}
