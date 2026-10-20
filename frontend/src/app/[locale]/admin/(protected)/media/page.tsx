import {getTranslations, setRequestLocale} from 'next-intl/server';
import MediaManager from '@/components/admin/media-manager';
import {Link} from '@/i18n/navigation';
import {getMediaList} from '@/lib/admin-api';

const PAGE_SIZE = 24;

export default async function AdminMediaPage({
  params,
  searchParams
}: {
  params: Promise<{locale: string}>;
  searchParams: Promise<{page?: string | string[]}>;
}) {
  const {locale} = await params;
  setRequestLocale(locale);
  const t = await getTranslations('admin.media');
  const sp = await searchParams;

  const rawPage = Array.isArray(sp.page) ? sp.page[0] : sp.page;
  const parsedPage = Number(rawPage);
  const page = Math.min(
    Number.isSafeInteger(parsedPage) && parsedPage > 0 ? parsedPage : 1,
    100_000
  );

  const data = await getMediaList({page, pageSize: PAGE_SIZE});
  const lastPage = Math.max(1, Math.ceil(data.total / data.page_size));

  return (
    <section>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="font-mono text-2xl text-accent">&gt; {t('title')}_</h1>
        <Link
          href="/admin/posts"
          className="font-mono text-xs text-muted hover:text-accent"
        >
          &lt; {t('backToPosts')}
        </Link>
      </div>

      <MediaManager items={data.items} />

      <nav aria-label={t('title')} className="mt-8 flex gap-4 font-mono text-sm">
        {page > 1 ? (
          <Link
            href={`/admin/media?page=${page - 1}`}
            className="hover:text-accent"
          >
            ← {t('prev')}
          </Link>
        ) : null}
        {page < lastPage ? (
          <Link
            href={`/admin/media?page=${page + 1}`}
            className="hover:text-accent"
          >
            {t('next')} →
          </Link>
        ) : null}
      </nav>
    </section>
  );
}
