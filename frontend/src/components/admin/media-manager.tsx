'use client';

import Image from 'next/image';
import {useLocale, useTranslations} from 'next-intl';
import {useRouter} from 'next/navigation';
import {useRef, useState} from 'react';
import type {MediaItem} from '@/lib/admin-types';

export default function MediaManager({items}: {items: MediaItem[]}) {
  const t = useTranslations('admin.media');
  const locale = useLocale();
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [pendingId, setPendingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<number | null>(null);

  async function onFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;

    setUploading(true);
    setError(null);
    try {
      const form = new FormData();
      form.append('file', file);
      const response = await fetch('/api/admin/uploads', {
        method: 'POST',
        body: form
      });
      if (response.status === 401) {
        window.location.assign(`/${locale}/admin/login`);
        return;
      }
      if (!response.ok) {
        setError(t('uploadFailed'));
        return;
      }
      router.refresh();
    } catch {
      setError(t('uploadFailed'));
    } finally {
      setUploading(false);
    }
  }

  async function remove(id: number) {
    if (!window.confirm(t('confirmDelete'))) return;
    setPendingId(id);
    setError(null);
    try {
      const response = await fetch(`/api/admin/media/${id}`, {
        method: 'DELETE'
      });
      if (response.status === 401) {
        window.location.assign(`/${locale}/admin/login`);
        return;
      }
      if (response.ok || response.status === 404) {
        router.refresh();
        return;
      }
      setError(t('deleteFailed'));
    } catch {
      setError(t('deleteFailed'));
    } finally {
      setPendingId(null);
    }
  }

  async function copy(item: MediaItem) {
    try {
      await navigator.clipboard.writeText(
        `${window.location.origin}${item.url}`
      );
      setCopiedId(item.id);
      window.setTimeout(() => setCopiedId(null), 1500);
    } catch {
      setError(t('copyFailed'));
    }
  }

  return (
    <div>
      <div className="mt-6 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          disabled={uploading}
          className="rounded bg-accent px-4 py-2 font-mono text-sm font-semibold text-black disabled:opacity-60"
        >
          {uploading ? t('uploading') : t('upload')}
        </button>
        <input
          ref={fileRef}
          type="file"
          accept="image/jpeg,image/png,image/webp,image/gif"
          onChange={onFileChange}
          className="hidden"
        />
        {error ? (
          <span role="alert" className="font-mono text-xs text-red-400">
            {error}
          </span>
        ) : null}
      </div>

      {items.length === 0 ? (
        <p className="mt-8 text-muted">{t('empty')}</p>
      ) : (
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((item) => (
            <article
              key={item.id}
              className="overflow-hidden rounded border border-border bg-surface"
            >
              <Image
                src={item.url}
                alt={item.original_name}
                width={320}
                height={200}
                unoptimized
                className="h-40 w-full object-cover"
              />
              <div className="grid gap-2 p-3 font-mono text-xs">
                <p className="truncate text-muted" title={item.original_name}>
                  {item.original_name}
                </p>
                <div className="flex items-center justify-between gap-2">
                  <button
                    type="button"
                    onClick={() => copy(item)}
                    className="hover:text-accent"
                  >
                    {copiedId === item.id ? t('copied') : t('copy')}
                  </button>
                  <button
                    type="button"
                    onClick={() => remove(item.id)}
                    disabled={pendingId === item.id}
                    className="text-red-400 hover:underline disabled:opacity-60"
                  >
                    {t('delete')}
                  </button>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
