import {Link} from '@/i18n/navigation';
import type {PostListItem} from '@/lib/api';

export default function PostCard({
  post,
  locale,
  headingLevel = 2
}: {
  post: PostListItem;
  locale: string;
  headingLevel?: 2 | 3;
}) {
  const date = post.published_at
    ? new Intl.DateTimeFormat(locale === 'zh' ? 'zh-CN' : 'en-US', {
        dateStyle: 'medium',
        timeZone: 'Asia/Shanghai'
      }).format(new Date(post.published_at))
    : '';
  const headingId = `post-${post.slug}`;
  const Heading = headingLevel === 3 ? 'h3' : 'h2';

  return (
    <article
      aria-labelledby={headingId}
      lang={post.language}
      className="rounded-lg border border-border bg-surface p-5 transition hover:border-accent/60"
    >
      <div className="flex items-center justify-between gap-4 font-mono text-xs text-muted">
        {post.published_at ? (
          <time dateTime={post.published_at}>{date}</time>
        ) : null}
        <span className="rounded border border-border px-1.5 py-0.5">
          {post.language.toUpperCase()}
        </span>
      </div>
      <Heading id={headingId} className="mt-3 text-xl font-semibold">
        <Link
          href={`/posts/${post.slug}`}
          className="hover:text-accent"
        >
          {post.title}
        </Link>
      </Heading>
      <p className="mt-2 text-sm text-muted">{post.excerpt}</p>
      <div className="mt-4 flex flex-wrap gap-2 font-mono text-xs text-accent">
        {post.tags.map((tag) => (
          <Link
            key={tag.slug}
            href={`/tags/${tag.slug}`}
            className="hover:underline"
          >
            #{tag.name}
          </Link>
        ))}
      </div>
    </article>
  );
}
