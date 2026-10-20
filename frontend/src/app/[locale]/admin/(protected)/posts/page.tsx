import {getTranslations, setRequestLocale} from 'next-intl/server';
import DeletePostButton from '@/components/admin/delete-post-button';
import {Link} from '@/i18n/navigation';
import {getAdminPosts} from '@/lib/admin-api';

const PAGE_SIZE = 10;

function formatDate(value: string, locale: string) {
  return new Intl.DateTimeFormat(locale === 'zh' ? 'zh-CN' : 'en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Asia/Shanghai'
  }).format(new Date(value));
}

export default async function AdminPostsPage({
  params,
  searchParams
}: {
  params: Promise<{locale: string}>;
  searchParams: Promise<{
    page?: string | string[];
    status?: string | string[];
    q?: string | string[];
  }>;
}) {
  const {locale} = await params;
  setRequestLocale(locale);
  const t = await getTranslations('admin.posts');
  const sp = await searchParams;

  const rawPage = Array.isArray(sp.page) ? sp.page[0] : sp.page;
  const parsedPage = Number(rawPage);
  const page = Math.min(
    Number.isSafeInteger(parsedPage) && parsedPage > 0 ? parsedPage : 1,
    100_000
  );

  const rawStatus = Array.isArray(sp.status) ? sp.status[0] : sp.status;
  const status =
    rawStatus === 'draft' || rawStatus === 'published' ? rawStatus : undefined;

  const rawQ = Array.isArray(sp.q) ? sp.q[0] : sp.q;
  const q = rawQ?.trim() || undefined;

  const data = await getAdminPosts({page, pageSize: PAGE_SIZE, status, q});
  const lastPage = Math.max(1, Math.ceil(data.total / data.page_size));

  function pageHref(target: number) {
    const search = new URLSearchParams();
    if (status) search.set('status', status);
    if (q) search.set('q', q);
    search.set('page', String(target));
    return `/admin/posts?${search.toString()}`;
  }

  return (
    <section>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="font-mono text-2xl text-accent">&gt; {t('title')}_</h1>
        <Link
          href="/admin/posts/new"
          className="rounded bg-accent px-4 py-2 font-mono text-sm font-semibold text-black hover:opacity-90"
        >
          {t('new')}
        </Link>
      </div>

      <form className="mt-6 flex flex-wrap items-end gap-3 font-mono text-xs">
        <label className="grid gap-1">
          <span className="text-muted">{t('status')}</span>
          <select
            name="status"
            defaultValue={status ?? ''}
            className="rounded border border-border bg-surface px-3 py-2"
          >
            <option value="">{t('all')}</option>
            <option value="draft">{t('draft')}</option>
            <option value="published">{t('published')}</option>
          </select>
        </label>
        <label className="grid gap-1">
          <span className="text-muted">{t('search')}</span>
          <input
            name="q"
            defaultValue={q ?? ''}
            maxLength={100}
            placeholder={t('searchPlaceholder')}
            className="rounded border border-border bg-surface px-3 py-2"
          />
        </label>
        <button
          type="submit"
          className="rounded border border-border px-4 py-2 hover:border-accent"
        >
          {t('filter')}
        </button>
      </form>

      <div className="mt-6 grid gap-3">
        {data.items.length === 0 ? (
          <p className="text-muted">{t('empty')}</p>
        ) : (
          data.items.map((post) => (
            <article
              key={post.id}
              data-testid={`admin-post-${post.id}`}
              className="rounded border border-border bg-surface p-4"
            >
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <h2 className="font-semibold">
                    <Link
                      href={`/admin/posts/${post.id}/edit`}
                      className="hover:text-accent"
                    >
                      {post.title}
                    </Link>
                  </h2>
                  <p className="mt-1 font-mono text-xs text-muted">
                    {post.slug} · {post.language.toUpperCase()} ·{' '}
                    {t('updated')} {formatDate(post.updated_at, locale)}
                  </p>
                </div>
                <div className="flex items-center gap-3 font-mono text-xs">
                  <span
                    className={
                      post.status === 'published'
                        ? 'rounded border border-accent/60 px-1.5 py-0.5 text-accent'
                        : 'rounded border border-border px-1.5 py-0.5 text-muted'
                    }
                  >
                    {t(post.status)}
                  </span>
                  <Link
                    href={`/admin/posts/${post.id}/edit`}
                    className="hover:text-accent"
                  >
                    {t('edit')}
                  </Link>
                  <DeletePostButton id={post.id} title={post.title} />
                </div>
              </div>
            </article>
          ))
        )}
      </div>

      <nav className="mt-8 flex gap-4 font-mono text-sm">
        {page > 1 ? (
          <Link href={pageHref(page - 1)} className="hover:text-accent">
            ← {t('prev')}
          </Link>
        ) : null}
        {page < lastPage ? (
          <Link href={pageHref(page + 1)} className="hover:text-accent">
            {t('next')} →
          </Link>
        ) : null}
      </nav>
    </section>
  );
}
