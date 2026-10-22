import {getTranslations} from 'next-intl/server';
import PostCard from '@/components/post-card';
import {Link} from '@/i18n/navigation';
import type {PostListItem} from '@/lib/api';

export default async function PostList({
  items,
  total,
  page,
  pageSize,
  locale,
  basePath = '/posts',
  emptyText
}: {
  items: PostListItem[];
  total: number;
  page: number;
  pageSize: number;
  locale: string;
  basePath?: string;
  emptyText: string;
}) {
  const t = await getTranslations('posts');
  const lastPage = Math.max(1, Math.ceil(total / pageSize));

  return (
    <>
      <div className="mt-8 grid gap-4">
        {items.length === 0 ? (
          <p className="text-muted">{emptyText}</p>
        ) : (
          items.map((post) => (
            <PostCard key={post.slug} post={post} locale={locale} />
          ))
        )}
      </div>

      <nav className="mt-8 flex gap-4 font-mono text-sm">
        {page > 1 ? (
          <Link
            href={`${basePath}?page=${page - 1}`}
            className="hover:text-accent"
          >
            ← {t('prev')}
          </Link>
        ) : null}
        {page < lastPage ? (
          <Link
            href={`${basePath}?page=${page + 1}`}
            className="hover:text-accent"
          >
            {t('next')} →
          </Link>
        ) : null}
      </nav>
    </>
  );
}
