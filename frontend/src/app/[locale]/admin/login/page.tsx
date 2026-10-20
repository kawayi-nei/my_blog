import {getTranslations, setRequestLocale} from 'next-intl/server';
import {notFound, redirect} from 'next/navigation';
import LoginForm from '@/components/admin/login-form';
import {getMe} from '@/lib/admin-api';
import {getSiteConfig} from '@/lib/api';

export default async function AdminLoginPage({
  params
}: {
  params: Promise<{locale: string}>;
}) {
  const {locale} = await params;
  setRequestLocale(locale);

  const config = await getSiteConfig();
  if (!config.admin_enabled) notFound();

  const me = await getMe();
  if (me) redirect(`/${locale}/admin/posts`);

  const t = await getTranslations('admin.login');

  return (
    <div className="mx-auto flex min-h-screen max-w-sm flex-col justify-center px-4">
      <h1 className="font-mono text-2xl text-accent">&gt; {t('title')}_</h1>
      <LoginForm />
    </div>
  );
}
