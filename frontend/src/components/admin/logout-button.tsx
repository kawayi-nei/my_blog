'use client';

import {useLocale, useTranslations} from 'next-intl';
import {useRouter} from 'next/navigation';

export default function LogoutButton() {
  const t = useTranslations('admin.nav');
  const locale = useLocale();
  const router = useRouter();

  async function logout() {
    await fetch('/api/auth/logout', {method: 'POST'});
    router.replace(`/${locale}/admin/login`);
    router.refresh();
  }

  return (
    <button type="button" onClick={logout} className="hover:text-accent">
      {t('logout')}
    </button>
  );
}
