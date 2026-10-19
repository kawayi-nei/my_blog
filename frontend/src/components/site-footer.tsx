import {useLocale, useTranslations} from 'next-intl';
import {site} from '@/content/site';

export default function SiteFooter() {
  const t = useTranslations('footer');
  const locale = useLocale();
  const name = locale === 'zh' ? site.name : site.nameEn;

  return (
    <footer className="border-t border-border/80 py-8">
      <div className="mx-auto max-w-5xl px-4 font-mono text-xs text-muted">
        <p>{t('copyright', {name})}</p>
      </div>
    </footer>
  );
}
