'use client';

import {useLocale, useTranslations} from 'next-intl';
import {useRouter} from 'next/navigation';
import {useState} from 'react';

export default function LogoutButton() {
  const t = useTranslations('admin.nav');
  const locale = useLocale();
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function logout() {
    setPending(true);
    setError(null);
    try {
      const response = await fetch('/api/auth/logout', {method: 'POST'});
      if (!response.ok) {
        setError(t('logoutFailed'));
        return;
      }
      router.replace(`/${locale}/admin/login`);
      router.refresh();
    } catch {
      setError(t('logoutFailed'));
    } finally {
      setPending(false);
    }
  }

  return (
    <span>
      <button
        type="button"
        onClick={logout}
        disabled={pending}
        className="hover:text-accent disabled:opacity-60"
      >
        {t('logout')}
      </button>
      {error ? (
        <span role="alert" className="ml-2 font-mono text-xs text-red-400">
          {error}
        </span>
      ) : null}
    </span>
  );
}
