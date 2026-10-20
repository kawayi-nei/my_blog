import {useTranslations} from 'next-intl';
import {Link} from '@/i18n/navigation';

export default function NotFound() {
  const t = useTranslations('errors');

  return (
    <section className="mx-auto max-w-3xl px-4 py-24 text-center">
      <p className="font-mono text-sm text-accent">404</p>
      <h1 className="mt-3 font-mono text-2xl text-accent">
        {t('notFoundTitle')}
      </h1>
      <p className="mt-3 text-muted">{t('notFoundDescription')}</p>
      <Link
        href="/"
        className="mt-6 inline-block rounded border border-border px-4 py-2 font-mono text-sm hover:border-accent"
      >
        {t('backHome')}
      </Link>
    </section>
  );
}
