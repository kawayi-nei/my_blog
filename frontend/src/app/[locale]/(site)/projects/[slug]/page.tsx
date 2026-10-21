import type {Metadata} from 'next';
import {getTranslations, setRequestLocale} from 'next-intl/server';
import {notFound} from 'next/navigation';
import {Markdown} from '@/components/markdown';
import {Link} from '@/i18n/navigation';
import {getProjectOrNull, type ProjectLocale} from '@/lib/api';

function formatDate(value: string | null, locale: string) {
  if (!value) return '';
  return new Intl.DateTimeFormat(locale === 'zh' ? 'zh-CN' : 'en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    timeZone: 'UTC'
  }).format(new Date(`${value}T00:00:00Z`));
}

export async function generateMetadata({
  params
}: {
  params: Promise<{locale: string; slug: string}>;
}): Promise<Metadata> {
  const {locale, slug} = await params;
  const projectLocale: ProjectLocale = locale === 'en' ? 'en' : 'zh';
  const project = await getProjectOrNull(slug, projectLocale);
  if (!project) return {};
  return {title: project.title, description: project.summary};
}

export default async function ProjectDetailPage({
  params
}: {
  params: Promise<{locale: string; slug: string}>;
}) {
  const {locale, slug} = await params;
  setRequestLocale(locale);
  const t = await getTranslations('projects');
  const projectLocale: ProjectLocale = locale === 'en' ? 'en' : 'zh';
  const project = await getProjectOrNull(slug, projectLocale);
  if (!project) notFound();

  const started = formatDate(project.started_on, locale);
  const ended = project.ended_on
    ? formatDate(project.ended_on, locale)
    : started
      ? t('present')
      : '';
  const dateRange = [started, ended].filter(Boolean).join(' – ');

  return (
    <article className="mx-auto max-w-3xl px-4 py-12">
      <Link
        href="/projects"
        className="font-mono text-xs text-muted hover:text-accent"
      >
        &lt; {t('back')}
      </Link>

      {project.cover_url ? (
        <div className="mt-6 overflow-hidden rounded-lg border border-border">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={project.cover_url}
            alt={project.title}
            className="h-64 w-full object-cover"
            loading="lazy"
          />
        </div>
      ) : null}

      <header className="mt-6 border-b border-border pb-6">
        <h1 className="text-3xl font-bold sm:text-4xl">{project.title}</h1>
        <p className="mt-3 text-muted">{project.summary}</p>
        <div className="mt-4 flex flex-wrap items-center gap-3 font-mono text-xs text-muted">
          {dateRange ? <span>{dateRange}</span> : null}
          {project.repo_url ? (
            <a
              href={project.repo_url}
              target="_blank"
              rel="noreferrer"
              className="hover:text-accent"
            >
              {t('repo')} ↗
            </a>
          ) : null}
          {project.demo_url ? (
            <a
              href={project.demo_url}
              target="_blank"
              rel="noreferrer"
              className="hover:text-accent"
            >
              {t('demo')} ↗
            </a>
          ) : null}
        </div>
        <div className="mt-4 flex flex-wrap gap-2 font-mono text-xs text-accent">
          {project.tech_stack.map((tech) => (
            <span key={tech}>#{tech}</span>
          ))}
        </div>
      </header>

      <div className="mt-8">
        <Markdown content={project.content_md} />
      </div>
    </article>
  );
}
