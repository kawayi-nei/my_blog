import {getTranslations, setRequestLocale} from 'next-intl/server';
import {notFound} from 'next/navigation';
import PostCard from '@/components/post-card';
import {Link} from '@/i18n/navigation';
import {getPosts} from '@/lib/api';

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
  const rawPage = Array.isArray(pageParam) ? pageParam[0] : pageParam;
  const parsedPage = Number(rawPage);
  const page =
    Number.isSafeInteger(parsedPage) && parsedPage > 0 ? parsedPage : 1;

  const data = await getPosts({page, pageSize: PAGE_SIZE});
  const lastPage = Math.max(1, Math.ceil(data.total / data.page_size));
  if (page > lastPage) {
    notFound();
  }

  return (
    <section className="mx-auto max-w-5xl px-4 py-12">
      <h1 className="font-mono text-2xl text-accent">&gt; {t('title')}_</h1>

      <div className="mt-8 grid gap-4">
        {data.items.length === 0 ? (
          <p className="text-muted">{t('empty')}</p>
        ) : (
          data.items.map((post) => (
            <PostCard key={post.slug} post={post} locale={locale} />
          ))
        )}
      </div>

      <nav className="mt-8 flex gap-4 font-mono text-sm">
        {page > 1 ? (
          <Link href={`/posts?page=${page - 1}`} className="hover:text-accent">
            ← {t('prev')}
          </Link>
        ) : null}
        {page < lastPage ? (
          <Link href={`/posts?page=${page + 1}`} className="hover:text-accent">
            {t('next')} →
          </Link>
        ) : null}
      </nav>
    </section>
  );
}
