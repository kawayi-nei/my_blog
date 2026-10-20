import {getTranslations, setRequestLocale} from 'next-intl/server';
import {notFound, redirect} from 'next/navigation';
import LogoutButton from '@/components/admin/logout-button';
import {Link} from '@/i18n/navigation';
import {getMe} from '@/lib/admin-api';
import {getSiteConfig} from '@/lib/api';

export default async function AdminProtectedLayout({
  children,
  params
}: {
  children: React.ReactNode;
  params: Promise<{locale: string}>;
}) {
  const {locale} = await params;
  setRequestLocale(locale);

  const config = await getSiteConfig();
  if (!config.admin_enabled) notFound();

  const me = await getMe();
  if (!me) redirect(`/${locale}/admin/login`);

  const t = await getTranslations('admin.nav');

  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-border bg-surface">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-4 px-4 py-4">
          <nav className="flex flex-wrap items-center gap-5 font-mono text-xs">
            <span className="text-accent">~/admin</span>
            <Link href="/admin/posts" className="hover:text-accent">
              {t('posts')}
            </Link>
            <Link href="/admin/media" className="hover:text-accent">
              {t('media')}
            </Link>
            <Link href="/" className="hover:text-accent">
              {t('backToSite')}
            </Link>
          </nav>
          <div className="flex items-center gap-4 font-mono text-xs text-muted">
            <span>{me.username}</span>
            <LogoutButton />
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">
        {children}
      </main>
    </div>
  );
}
