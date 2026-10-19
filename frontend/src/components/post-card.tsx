import {Link} from '@/i18n/navigation';
import type {PostListItem} from '@/lib/api';

export default function PostCard({
  post,
  locale
}: {
  post: PostListItem;
  locale: string;
}) {
  const date = post.published_at
    ? new Intl.DateTimeFormat(locale === 'zh' ? 'zh-CN' : 'en-US', {
        dateStyle: 'medium',
        timeZone: 'Asia/Shanghai'
      }).format(new Date(post.published_at))
    : '';

  return (
    <article className="rounded-lg border border-border bg-surface p-5 transition hover:border-accent/60">
      <div className="flex items-center justify-between gap-4 font-mono text-xs text-muted">
        <time>{date}</time>
        <span className="rounded border border-border px-1.5 py-0.5">
          {post.language.toUpperCase()}
        </span>
      </div>
      <Link
        href={`/posts/${post.slug}`}
        className="mt-3 block text-xl font-semibold hover:text-accent"
      >
        {post.title}
      </Link>
      <p className="mt-2 text-sm text-muted">{post.excerpt}</p>
      <div className="mt-4 flex flex-wrap gap-2 font-mono text-xs text-accent">
        {post.tags.map((tag) => (
          <span key={tag.slug}>#{tag.name}</span>
        ))}
      </div>
    </article>
  );
}
