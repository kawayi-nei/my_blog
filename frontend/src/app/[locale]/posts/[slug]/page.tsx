import type {Metadata} from 'next';
import {getTranslations, setRequestLocale} from 'next-intl/server';
import {notFound} from 'next/navigation';
import {Markdown} from '@/components/markdown';
import {Link} from '@/i18n/navigation';
import {getPostOrNull} from '@/lib/api';

export async function generateMetadata({
  params
}: {
  params: Promise<{locale: string; slug: string}>;
}): Promise<Metadata> {
  const {slug} = await params;
  const post = await getPostOrNull(slug);
  if (!post) return {};
  return {title: post.title, description: post.excerpt};
}

export default async function PostDetailPage({
  params
}: {
  params: Promise<{locale: string; slug: string}>;
}) {
  const {locale, slug} = await params;
  setRequestLocale(locale);
  const t = await getTranslations('posts');
  const post = await getPostOrNull(slug);
  if (!post) notFound();

  const date = post.published_at
    ? new Intl.DateTimeFormat(locale === 'zh' ? 'zh-CN' : 'en-US', {
        dateStyle: 'long',
        timeZone: 'Asia/Shanghai'
      }).format(new Date(post.published_at))
    : '';

  return (
    <article
      lang={post.language}
      className="mx-auto max-w-3xl px-4 py-12"
    >
      <Link href="/posts" className="font-mono text-xs text-muted hover:text-accent">
        &lt; {t('back')}
      </Link>

      <header className="mt-6 border-b border-border pb-6">
        <h1 className="text-3xl font-bold sm:text-4xl">{post.title}</h1>
        <div className="mt-3 flex flex-wrap items-center gap-3 font-mono text-xs text-muted">
          {post.published_at ? (
            <time dateTime={post.published_at}>{date}</time>
          ) : null}
          <span>{post.language.toUpperCase()}</span>
          <span>
            {new Intl.NumberFormat(locale === 'zh' ? 'zh-CN' : 'en-US').format(
              post.view_count
            )}{' '}
            {t('views')}
          </span>
        </div>
        <div className="mt-3 flex flex-wrap gap-2 font-mono text-xs text-accent">
          {post.tags.map((tag) => (
            <span key={tag.slug}>#{tag.name}</span>
          ))}
        </div>
      </header>

      <div className="mt-8">
        <Markdown content={post.content_md} />
      </div>
    </article>
  );
}
