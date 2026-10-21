import {setRequestLocale} from 'next-intl/server';
import {notFound} from 'next/navigation';
import ProjectForm from '@/components/admin/project-form';
import {getAdminProjectOrNull} from '@/lib/admin-api';

export default async function EditProjectPage({
  params
}: {
  params: Promise<{locale: string; id: string}>;
}) {
  const {locale, id} = await params;
  setRequestLocale(locale);

  const projectId = Number(id);
  if (!Number.isSafeInteger(projectId) || projectId <= 0) notFound();

  const project = await getAdminProjectOrNull(projectId);
  if (!project) notFound();

  return <ProjectForm project={project} />;
}
