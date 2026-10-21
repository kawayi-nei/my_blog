import {getTranslations, setRequestLocale} from 'next-intl/server';
import ProjectCard from '@/components/project-card';
import {getProjects, type ProjectLocale} from '@/lib/api';

export default async function ProjectsPage({
  params
}: {
  params: Promise<{locale: string}>;
}) {
  const {locale} = await params;
  setRequestLocale(locale);
  const t = await getTranslations('projects');
  const projectLocale: ProjectLocale = locale === 'en' ? 'en' : 'zh';

  const projects = await getProjects({locale: projectLocale});

  return (
    <section className="mx-auto max-w-5xl px-4 py-12">
      <h1 className="font-mono text-2xl text-accent">&gt; {t('title')}_</h1>

      {projects.length === 0 ? (
        <p className="mt-8 text-muted">{t('empty')}</p>
      ) : (
        <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <ProjectCard
              key={project.slug}
              project={project}
              locale={locale}
            />
          ))}
        </div>
      )}
    </section>
  );
}
