'use client';

import {useTranslations} from 'next-intl';
import {useRef, useState} from 'react';
import {Markdown} from '@/components/markdown';

export default function MarkdownEditor({
  value,
  onChange
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  const t = useTranslations('admin.posts.form');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function insert(before: string, after: string, fallback: string) {
    const textarea = textareaRef.current;
    if (!textarea) return;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selected = value.slice(start, end) || fallback;
    const next =
      value.slice(0, start) + before + selected + after + value.slice(end);
    onChange(next);
    requestAnimationFrame(() => {
      textarea.focus();
      textarea.setSelectionRange(
        start + before.length,
        start + before.length + selected.length
      );
    });
  }

  async function onFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;

    setUploading(true);
    setError(null);
    const form = new FormData();
    form.append('file', file);

    const response = await fetch('/api/admin/uploads', {
      method: 'POST',
      body: form
    });
    setUploading(false);

    if (!response.ok) {
      setError(t('uploadFailed'));
      return;
    }
    const data = (await response.json()) as {url: string};
    insert('![', `](${data.url})`, file.name);
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div>
        <div className="mb-2 flex flex-wrap gap-2 font-mono text-xs">
          <button
            type="button"
            onClick={() => insert('**', '**', t('bold'))}
            className="rounded border border-border px-2 py-1 hover:border-accent"
          >
            {t('bold')}
          </button>
          <button
            type="button"
            onClick={() => insert('_', '_', t('italic'))}
            className="rounded border border-border px-2 py-1 hover:border-accent"
          >
            {t('italic')}
          </button>
          <button
            type="button"
            onClick={() => insert('`', '`', t('code'))}
            className="rounded border border-border px-2 py-1 hover:border-accent"
          >
            {t('code')}
          </button>
          <button
            type="button"
            onClick={() => insert('[', '](https://)', t('link'))}
            className="rounded border border-border px-2 py-1 hover:border-accent"
          >
            {t('link')}
          </button>
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
            className="rounded border border-border px-2 py-1 hover:border-accent disabled:opacity-60"
          >
            {uploading ? t('uploading') : t('insertImage')}
          </button>
          <input
            ref={fileRef}
            type="file"
            accept="image/jpeg,image/png,image/webp,image/gif"
            onChange={onFileChange}
            className="hidden"
          />
        </div>

        <textarea
          id="content_md"
          ref={textareaRef}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          rows={20}
          placeholder={t('contentPlaceholder')}
          className="w-full rounded border border-border bg-surface p-3 font-mono text-sm"
        />
        {error ? (
          <p className="mt-2 font-mono text-xs text-red-400">{error}</p>
        ) : null}
      </div>

      <div>
        <div className="mb-2 font-mono text-xs text-muted">{t('preview')}</div>
        <div className="min-h-40 rounded border border-border bg-surface p-3">
          {value ? (
            <Markdown content={value} />
          ) : (
            <p className="text-sm text-muted">{t('previewEmpty')}</p>
          )}
        </div>
      </div>
    </div>
  );
}
