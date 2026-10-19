'use client';

import {useLocale} from 'next-intl';
import {Link, usePathname} from '@/i18n/navigation';

export default function LocaleSwitcher() {
  const locale = useLocale();
  const pathname = usePathname();
  const nextLocale = locale === 'zh' ? 'en' : 'zh';

  return (
    <Link
      href={pathname}
      locale={nextLocale}
      aria-label={locale === 'zh' ? 'Switch to English' : '切换到中文'}
      className="rounded border border-border px-2 py-1 hover:text-foreground"
    >
      {locale === 'zh' ? 'EN' : '中文'}
    </Link>
  );
}
