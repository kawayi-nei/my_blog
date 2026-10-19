import {getTranslations, setRequestLocale} from 'next-intl/server';
import PostCard from '@/components/post-card';
import {site} from '@/content/site';
import {Link} from '@/i18n/navigation';
import {getPosts} from '@/lib/api';

export default async function HomePage({
  params
}: {
  params: Promise<{locale: string}>;
}) {
  const {locale} = await params;
  setRequestLocale(locale);
  const t = await getTranslations('home');

  const data = await getPosts({pageSize: 5});

  return (
    <section className="mx-auto max-w-5xl px-4 py-16">
      <p className="font-mono text-sm text-accent">$ whoami</p>
      <h1 className="mt-4 text-4xl font-bold tracking-tight sm:text-5xl">
        {t('greeting')}
        {locale === 'zh' ? '' : ' '}
        <span className="text-accent">
          {locale === 'zh' ? site.name : site.nameEn}
        </span>
      </h1>
      <p className="mt-4 max-w-xl text-muted">{t('tagline')}</p>

      <div className="mt-8 flex flex-wrap gap-3">
        <Link
          href="/posts"
          className="rounded bg-accent px-4 py-2 font-mono text-sm font-semibold text-black hover:opacity-90"
        >
          {t('latestPosts')}
        </Link>
        <a
          href={site.github}
          target="_blank"
          rel="noreferrer"
          className="rounded border border-border px-4 py-2 font-mono text-sm hover:border-accent"
        >
          GitHub
        </a>
      </div>

      <section className="mt-16">
        <h2 className="font-mono text-sm text-muted">
          &gt; {t('latestPosts')}_
        </h2>
        <div className="mt-6 grid gap-4">
          {data.items.length === 0 ? (
            <p className="text-muted">{t('empty')}</p>
          ) : (
            data.items.map((post) => (
              <PostCard
                key={post.slug}
                post={post}
                locale={locale}
                headingLevel={3}
              />
            ))
          )}
        </div>
      </section>
    </section>
  );
}
