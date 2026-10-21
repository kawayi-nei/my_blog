'use client';

import {useLocale, useTranslations} from 'next-intl';
import {useRouter} from 'next/navigation';
import {useState} from 'react';

export default function DeleteProjectButton({
  id,
  title
}: {
  id: number;
  title: string;
}) {
  const t = useTranslations('admin.projects');
  const locale = useLocale();
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onDelete() {
    if (!window.confirm(t('confirmDelete', {title}))) return;
    setPending(true);
    setError(null);
    try {
      const response = await fetch(`/api/admin/projects/${id}`, {
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
      setPending(false);
    }
  }

  return (
    <span className="inline-flex items-center gap-2">
      <button
        type="button"
        onClick={onDelete}
        disabled={pending}
        className="text-red-400 hover:underline disabled:opacity-60"
      >
        {t('delete')}
      </button>
      {error ? (
        <span role="alert" className="text-red-400">
          {error}
        </span>
      ) : null}
    </span>
  );
}
