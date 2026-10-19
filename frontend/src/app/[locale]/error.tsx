'use client';

import {useTranslations} from 'next-intl';

export default function LocaleError({reset}: {reset: () => void}) {
  const t = useTranslations('errors');

  return (
    <section className="mx-auto max-w-3xl px-4 py-24 text-center">
      <h1 className="font-mono text-2xl text-accent">{t('title')}</h1>
      <p className="mt-3 text-muted">{t('description')}</p>
      <button
        onClick={reset}
        className="mt-6 rounded border border-border px-4 py-2 font-mono text-sm hover:border-accent"
      >
        {t('retry')}
      </button>
    </section>
  );
}
