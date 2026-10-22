import {getTranslations, setRequestLocale} from 'next-intl/server';
import PostCard from '@/components/post-card';
import ProjectCard from '@/components/project-card';
import {search as searchApi} from '@/lib/api';

export default async function SearchPage({
  params,
  searchParams
}: {
  params: Promise<{locale: string}>;
  searchParams: Promise<{q?: string | string[]}>;
}) {
  const {locale} = await params;
  const {q: qParam} = await searchParams;
  setRequestLocale(locale);
  const t = await getTranslations('search');
  const rawQ = Array.isArray(qParam) ? qParam[0] : qParam;
  const q = (rawQ ?? '').trim().slice(0, 100);
  const projectLocale = locale === 'en' ? 'en' : 'zh';

  const data = q ? await searchApi({q, locale: projectLocale}) : null;

  return (
    <section className="mx-auto max-w-5xl px-4 py-12">
      <h1 className="font-mono text-2xl text-accent">&gt; {t('title')}_</h1>

      <form
        action={`/${locale}/search`}
        method="get"
        className="mt-6 flex flex-wrap gap-3"
      >
        <label htmlFor="q" className="sr-only">
          {t('label')}
        </label>
        <input
          id="q"
          name="q"
          defaultValue={q}
          maxLength={100}
          placeholder={t('placeholder')}
          className="w-full max-w-md rounded border border-border bg-surface px-3 py-2 font-mono text-sm sm:w-auto"
        />
        <button
          type="submit"
          className="rounded bg-accent px-4 py-2 font-mono text-sm font-semibold text-black"
        >
          {t('submit')}
        </button>
      </form>

      {!data ? (
        <p className="mt-8 text-muted">{t('prompt')}</p>
      ) : data.total === 0 ? (
        <p className="mt-8 text-muted">{t('empty')}</p>
      ) : (
        <div className="mt-8 grid gap-10">
          <p className="font-mono text-xs text-muted">
            {t('resultCount', {count: data.total})}
          </p>

          {data.posts.length > 0 ? (
            <section>
              <h2 className="font-mono text-lg text-accent">
                &gt; {t('posts')}
              </h2>
              <div className="mt-4 grid gap-4">
                {data.posts.map((post) => (
                  <PostCard
                    key={post.slug}
                    post={post}
                    locale={locale}
                    headingLevel={3}
                  />
                ))}
              </div>
            </section>
          ) : null}

          {data.projects.length > 0 ? (
            <section>
              <h2 className="font-mono text-lg text-accent">
                &gt; {t('projects')}
              </h2>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                {data.projects.map((project) => (
                  <ProjectCard
                    key={project.slug}
                    project={project}
                    locale={locale}
                  />
                ))}
              </div>
            </section>
          ) : null}
        </div>
      )}
    </section>
  );
}
