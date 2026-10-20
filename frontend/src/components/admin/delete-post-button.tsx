'use client';

import {useTranslations} from 'next-intl';
import {useRouter} from 'next/navigation';

export default function DeletePostButton({
  id,
  title
}: {
  id: number;
  title: string;
}) {
  const t = useTranslations('admin.posts');
  const router = useRouter();

  async function onDelete() {
    if (!window.confirm(t('confirmDelete', {title}))) return;
    const response = await fetch(`/api/admin/posts/${id}`, {
      method: 'DELETE'
    });
    if (response.ok || response.status === 404) {
      router.refresh();
      return;
    }
    window.alert(t('deleteFailed'));
  }

  return (
    <button
      type="button"
      onClick={onDelete}
      className="text-red-400 hover:underline"
    >
      {t('delete')}
    </button>
  );
}
