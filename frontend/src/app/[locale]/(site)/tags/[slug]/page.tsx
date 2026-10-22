import {getTranslations, setRequestLocale} from 'next-intl/server';
import {notFound} from 'next/navigation';
import PostList from '@/components/post-list';
import {getPosts, getTags} from '@/lib/api';

const PAGE_SIZE = 10;

export default async function TagPage({
  params,
  searchParams
}: {
  params: Promise<{locale: string; slug: string}>;
  searchParams: Promise<{page?: string | string[]}>;
}) {
  const {locale, slug} = await params;
  const {page: pageParam} = await searchParams;
  setRequestLocale(locale);
  const t = await getTranslations('tags');
  const rawPage = Array.isArray(pageParam) ? pageParam[0] : pageParam;
  const parsedPage = Number(rawPage);
  const page =
    Number.isSafeInteger(parsedPage) && parsedPage > 0 ? parsedPage : 1;

  const tags = await getTags();
  const tag = tags.find((item) => item.slug === slug);
  if (!tag) {
    notFound();
  }

  const data = await getPosts({page, pageSize: PAGE_SIZE, tag: slug});
  const lastPage = Math.max(1, Math.ceil(data.total / data.page_size));
  if (page > lastPage) {
    notFound();
  }

  return (
    <section className="mx-auto max-w-5xl px-4 py-12">
      <h1 className="font-mono text-2xl text-accent">
        &gt; #{tag.name}_
      </h1>
      <p className="mt-2 font-mono text-xs text-muted">
        {t('count', {count: tag.post_count})}
      </p>

      <PostList
        items={data.items}
        total={data.total}
        page={page}
        pageSize={PAGE_SIZE}
        basePath={`/tags/${slug}`}
        emptyText={t('empty')}
        locale={locale}
      />
    </section>
  );
}
