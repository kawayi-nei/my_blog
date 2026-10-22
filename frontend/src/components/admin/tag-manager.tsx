'use client';

import {useLocale, useTranslations} from 'next-intl';
import {useRouter} from 'next/navigation';
import {useState} from 'react';
import type {AdminTag} from '@/lib/admin-types';

function sortTags(tags: AdminTag[], locale: string) {
  return [...tags].sort((a, b) =>
    a.name.localeCompare(b.name, locale === 'zh' ? 'zh-CN' : 'en-US')
  );
}

export default function TagManager({tags: initialTags}: {tags: AdminTag[]}) {
  const t = useTranslations('admin.tags');
  const locale = useLocale();
  const router = useRouter();
  const [tags, setTags] = useState(() => sortTags(initialTags, locale));
  const [newName, setNewName] = useState('');
  const [newSlug, setNewSlug] = useState('');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState('');
  const [editSlug, setEditSlug] = useState('');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleFailure(status: number, fallback: string) {
    if (status === 401) {
      router.replace(`/${locale}/admin/login`);
      return;
    }
    if (status === 409) {
      setError(t('conflict'));
      return;
    }
    if (status === 422) {
      setError(t('invalid'));
      return;
    }
    setError(fallback);
  }

  async function create(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = newName.trim();
    const slug = newSlug.trim();
    if (!name || !slug) return;

    setPending(true);
    setError(null);
    try {
      const response = await fetch('/api/admin/tags', {
        method: 'POST',
        headers: {'content-type': 'application/json'},
        body: JSON.stringify({name, slug})
      });
      if (!response.ok) {
        handleFailure(response.status, t('createFailed'));
        return;
      }
      const tag = (await response.json()) as AdminTag;
      setTags((current) => sortTags([...current, tag], locale));
      setNewName('');
      setNewSlug('');
    } catch {
      setError(t('createFailed'));
    } finally {
      setPending(false);
    }
  }

  function startEdit(tag: AdminTag) {
    setEditingId(tag.id);
    setEditName(tag.name);
    setEditSlug(tag.slug);
    setError(null);
  }

  async function save(id: number) {
    const name = editName.trim();
    const slug = editSlug.trim();
    if (!name || !slug) return;

    setPending(true);
    setError(null);
    try {
      const response = await fetch(`/api/admin/tags/${id}`, {
        method: 'PATCH',
        headers: {'content-type': 'application/json'},
        body: JSON.stringify({name, slug})
      });
      if (!response.ok) {
        handleFailure(response.status, t('saveFailed'));
        return;
      }
      const tag = (await response.json()) as AdminTag;
      setTags((current) =>
        sortTags(
          current.map((item) => (item.id === id ? tag : item)),
          locale
        )
      );
      setEditingId((current) => (current === id ? null : current));
    } catch {
      setError(t('saveFailed'));
    } finally {
      setPending(false);
    }
  }

  async function remove(tag: AdminTag) {
    if (
      !window.confirm(
        t('confirmDelete', {name: tag.name, count: tag.post_count})
      )
    ) {
      return;
    }

    setPending(true);
    setError(null);
    try {
      const response = await fetch(`/api/admin/tags/${tag.id}`, {
        method: 'DELETE'
      });
      if (response.status === 401) {
        router.replace(`/${locale}/admin/login`);
        return;
      }
      if (response.ok || response.status === 404) {
        setTags((current) => current.filter((item) => item.id !== tag.id));
        return;
      }
      handleFailure(response.status, t('deleteFailed'));
    } catch {
      setError(t('deleteFailed'));
    } finally {
      setPending(false);
    }
  }

  return (
    <div>
      <form
        onSubmit={create}
        className="mt-6 flex flex-wrap items-end gap-3 font-mono text-xs"
      >
        <label className="grid gap-1">
          <span className="text-muted">{t('name')}</span>
          <input
            value={newName}
            onChange={(event) => setNewName(event.target.value)}
            disabled={pending}
            required
            className="rounded border border-border bg-surface px-2 py-1"
          />
        </label>
        <label className="grid gap-1">
          <span className="text-muted">{t('slug')}</span>
          <input
            value={newSlug}
            onChange={(event) => setNewSlug(event.target.value)}
            disabled={pending}
            required
            className="rounded border border-border bg-surface px-2 py-1"
          />
        </label>
        <button
          type="submit"
          disabled={pending || !newName.trim() || !newSlug.trim()}
          className="rounded bg-accent px-4 py-2 font-mono text-sm font-semibold text-black disabled:opacity-60"
        >
          {t('create')}
        </button>
      </form>

      {error ? (
        <p role="alert" className="mt-4 font-mono text-xs text-red-400">
          {error}
        </p>
      ) : null}

      {tags.length === 0 ? (
        <p className="mt-8 text-muted">{t('empty')}</p>
      ) : (
        <ul className="mt-8 grid gap-3">
          {tags.map((tag) => (
            <li
              key={tag.id}
              data-testid={`admin-tag-${tag.slug}`}
              className="rounded border border-border bg-surface p-4"
            >
              {editingId === tag.id ? (
                <form
                  onSubmit={(event) => {
                    event.preventDefault();
                    void save(tag.id);
                  }}
                  className="flex flex-wrap items-end gap-3 font-mono text-xs"
                >
                  <label className="grid gap-1">
                    <span className="text-muted">{t('name')}</span>
                    <input
                      value={editName}
                      onChange={(event) => setEditName(event.target.value)}
                      required
                      className="rounded border border-border bg-background px-2 py-1"
                    />
                  </label>
                  <label className="grid gap-1">
                    <span className="text-muted">{t('slug')}</span>
                    <input
                      value={editSlug}
                      onChange={(event) => setEditSlug(event.target.value)}
                      required
                      className="rounded border border-border bg-background px-2 py-1"
                    />
                  </label>
                  <button
                    type="submit"
                    disabled={pending || !editName.trim() || !editSlug.trim()}
                    className="rounded bg-accent px-3 py-1 font-semibold text-black disabled:opacity-60"
                  >
                    {pending ? t('saving') : t('save')}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setError(null);
                      setEditingId(null);
                    }}
                    className="rounded border border-border px-3 py-1 hover:border-accent"
                  >
                    {t('cancel')}
                  </button>
                </form>
              ) : (
                <div className="flex flex-wrap items-center justify-between gap-3 font-mono text-sm">
                  <div className="flex flex-wrap items-baseline gap-2">
                    <span className="text-accent">#{tag.name}</span>
                    <span className="text-xs text-muted">/{tag.slug}</span>
                  </div>
                  <span className="text-xs text-muted">
                    {t('postCount', {count: tag.post_count})}
                  </span>
                  <div className="flex gap-3 text-xs">
                    <button
                      type="button"
                      onClick={() => startEdit(tag)}
                      aria-label={`${t('edit')} ${tag.name}`}
                      className="hover:text-accent"
                    >
                      {t('edit')}
                    </button>
                    <button
                      type="button"
                      onClick={() => void remove(tag)}
                      aria-label={`${t('delete')} ${tag.name}`}
                      disabled={pending}
                      className="text-red-400 hover:underline disabled:opacity-60"
                    >
                      {t('delete')}
                    </button>
                  </div>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
