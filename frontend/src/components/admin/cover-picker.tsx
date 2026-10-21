'use client';

import {useLocale, useTranslations} from 'next-intl';
import {useRef, useState} from 'react';
import type {MediaItem} from '@/lib/admin-types';

export default function CoverPicker({
  value,
  onChange
}: {
  value: string | null;
  onChange: (value: string | null) => void;
}) {
  const t = useTranslations('admin.projects.form.cover');
  const locale = useLocale();
  const fileRef = useRef<HTMLInputElement>(null);
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<MediaItem[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function upload(event: React.ChangeEvent<HTMLInputElement>) {
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
      const data = (await response.json()) as {url: string};
      onChange(data.url);
    } catch {
      setError(t('uploadFailed'));
    } finally {
      setUploading(false);
    }
  }

  async function toggleLibrary() {
    if (open) {
      setOpen(false);
      return;
    }

    setOpen(true);
    setError(null);
    if (items !== null) return;

    setLoading(true);
    try {
      const response = await fetch('/api/admin/media?page_size=100');
      if (response.status === 401) {
        window.location.assign(`/${locale}/admin/login`);
        return;
      }
      if (!response.ok) {
        setError(t('loadFailed'));
        return;
      }
      const data = (await response.json()) as {items: MediaItem[]};
      setItems(data.items);
    } catch {
      setError(t('loadFailed'));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid gap-3">
      <span className="font-mono text-sm">{t('label')}</span>

      {value ? (
        <img
          src={value}
          alt={t('preview')}
          className="h-36 w-full max-w-xs rounded border border-border object-cover"
        />
      ) : (
        <p className="text-xs text-muted">{t('noCover')}</p>
      )}

      <div className="flex flex-wrap gap-2 font-mono text-xs">
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          disabled={uploading}
          className="rounded border border-border px-3 py-1 hover:border-accent disabled:opacity-60"
        >
          {uploading ? t('uploading') : t('upload')}
        </button>
        <button
          type="button"
          onClick={toggleLibrary}
          aria-expanded={open}
          className="rounded border border-border px-3 py-1 hover:border-accent"
        >
          {open ? t('close') : t('choose')}
        </button>
        {value ? (
          <button
            type="button"
            onClick={() => onChange(null)}
            className="rounded border border-border px-3 py-1 text-red-400 hover:border-red-400"
          >
            {t('clear')}
          </button>
        ) : null}
        <input
          ref={fileRef}
          type="file"
          accept="image/jpeg,image/png,image/webp,image/gif"
          onChange={upload}
          className="hidden"
        />
      </div>

      {error ? (
        <span role="alert" className="font-mono text-xs text-red-400">
          {error}
        </span>
      ) : null}

      {open ? (
        loading ? (
          <p className="text-xs text-muted">{t('loading')}</p>
        ) : items && items.length > 0 ? (
          <div className="grid max-h-72 grid-cols-2 gap-2 overflow-y-auto sm:grid-cols-3">
            {items.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => {
                  onChange(item.url);
                  setOpen(false);
                }}
                className="overflow-hidden rounded border border-border hover:border-accent"
              >
                <img
                  src={item.url}
                  alt={item.original_name}
                  loading="lazy"
                  className="h-24 w-full object-cover"
                />
              </button>
            ))}
          </div>
        ) : (
          <p className="text-xs text-muted">{t('libraryEmpty')}</p>
        )
      ) : null}
    </div>
  );
}
