import {getTranslations, setRequestLocale} from 'next-intl/server';
import {notFound} from 'next/navigation';
import PostList from '@/components/post-list';
import {Link} from '@/i18n/navigation';
import {getPosts, getTags} from '@/lib/api';

const PAGE_SIZE = 10;

export default async function PostsPage({
  params,
  searchParams
}: {
  params: Promise<{locale: string}>;
  searchParams: Promise<{page?: string | string[]}>;
}) {
  const {locale} = await params;
  const {page: pageParam} = await searchParams;
  setRequestLocale(locale);
  const t = await getTranslations('posts');
  const tTags = await getTranslations('tags');
  const rawPage = Array.isArray(pageParam) ? pageParam[0] : pageParam;
  const parsedPage = Number(rawPage);
  const page = Math.min(
    Number.isSafeInteger(parsedPage) && parsedPage > 0 ? parsedPage : 1,
    100_000
  );

  const [data, tags] = await Promise.all([
    getPosts({page, pageSize: PAGE_SIZE}),
    getTags()
  ]);
  const lastPage = Math.max(1, Math.ceil(data.total / data.page_size));
  if (page > lastPage) {
    notFound();
  }

  const visibleTags = tags.filter((tag) => tag.post_count > 0);

  return (
    <section className="mx-auto max-w-5xl px-4 py-12">
      <h1 className="font-mono text-2xl text-accent">&gt; {t('title')}_</h1>

      {visibleTags.length > 0 ? (
        <nav
          aria-label={tTags('title')}
          className="mt-6 flex flex-wrap items-center gap-2 font-mono text-xs"
        >
          {visibleTags.map((tag) => (
            <Link
              key={tag.slug}
              href={`/tags/${tag.slug}`}
              className="rounded border border-border px-2 py-1 text-muted hover:border-accent hover:text-accent"
            >
              #{tag.name} <span className="text-accent">{tag.post_count}</span>
            </Link>
          ))}
        </nav>
      ) : null}

      <PostList
        items={data.items}
        page={page}
        lastPage={lastPage}
        emptyText={t('empty')}
        locale={locale}
      />
    </section>
  );
}
