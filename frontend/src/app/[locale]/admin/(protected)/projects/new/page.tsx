import {setRequestLocale} from 'next-intl/server';
import ProjectForm from '@/components/admin/project-form';

export default async function NewProjectPage({
  params
}: {
  params: Promise<{locale: string}>;
}) {
  const {locale} = await params;
  setRequestLocale(locale);
  return <ProjectForm />;
}
