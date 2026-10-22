import {getTranslations} from 'next-intl/server';
import {Link} from '@/i18n/navigation';
import type {ProjectListItem} from '@/lib/api';

function formatMonth(value: string | null, locale: string) {
  if (!value) return '';
  return new Intl.DateTimeFormat(locale === 'zh' ? 'zh-CN' : 'en-US', {
    year: 'numeric',
    month: 'short',
    timeZone: 'UTC'
  }).format(new Date(`${value}T00:00:00Z`));
}

export default async function ProjectCard({
  project,
  locale,
  headingLevel = 2
}: {
  project: ProjectListItem;
  locale: string;
  headingLevel?: 2 | 3;
}) {
  const t = await getTranslations('projects');
  const Heading = headingLevel === 3 ? 'h3' : 'h2';
  const started = formatMonth(project.started_on, locale);
  const ended = project.ended_on
    ? formatMonth(project.ended_on, locale)
    : started
      ? t('present')
      : '';
  const range = [started, ended].filter(Boolean).join(' – ');

  return (
    <article className="overflow-hidden rounded-lg border border-border bg-surface transition hover:border-accent/60">
      {project.cover_url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={project.cover_url}
          alt={project.title}
          loading="lazy"
          className="h-44 w-full object-cover"
        />
      ) : null}
      <div className="p-5">
        <div className="flex items-center justify-between gap-3 font-mono text-xs text-muted">
          <span>{range}</span>
          {project.featured ? (
            <span className="rounded border border-accent/60 px-1.5 py-0.5 text-accent">
              {t('featured')}
            </span>
          ) : null}
        </div>
        <Heading className="mt-3 text-xl font-semibold">
          <Link href={`/projects/${project.slug}`} className="hover:text-accent">
            {project.title}
          </Link>
        </Heading>
        <p className="mt-2 text-sm text-muted">{project.summary}</p>
        <div className="mt-4 flex flex-wrap gap-2 font-mono text-xs text-accent">
          {project.tech_stack.map((tech) => (
            <span key={tech}>#{tech}</span>
          ))}
        </div>
      </div>
    </article>
  );
}
