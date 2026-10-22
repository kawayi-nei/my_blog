import {useLocale, useTranslations} from 'next-intl';
import {Link} from '@/i18n/navigation';
import LocaleSwitcher from '@/components/locale-switcher';
import {site} from '@/content/site';

export default function SiteHeader({
  adminEnabled = false
}: {
  adminEnabled?: boolean;
}) {
  const t = useTranslations('nav');
  const locale = useLocale();

  return (
    <header className="border-b border-border/80 bg-background/90 backdrop-blur">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4">
        <Link href="/" className="font-mono text-sm font-semibold text-accent">
          ~/{locale === 'zh' ? site.name : site.nameEn}
        </Link>
        <nav className="flex items-center gap-5 font-mono text-xs text-muted">
          <Link href="/projects" className="hover:text-foreground">
            {t('projects')}
          </Link>
          <Link href="/posts" className="hover:text-foreground">
            {t('posts')}
          </Link>
          <Link href="/search" className="hover:text-foreground">
            {t('search')}
          </Link>
          {adminEnabled ? (
            <Link href="/admin/posts" className="hover:text-foreground">
              {t('admin')}
            </Link>
          ) : null}
          <a
            href={site.github}
            target="_blank"
            rel="noreferrer"
            className="hover:text-foreground"
          >
            {t('github')}
          </a>
          <LocaleSwitcher />
        </nav>
      </div>
    </header>
  );
}
