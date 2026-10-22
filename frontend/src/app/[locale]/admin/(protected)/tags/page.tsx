import {getTranslations, setRequestLocale} from 'next-intl/server';
import TagManager from '@/components/admin/tag-manager';
import {getAdminTags} from '@/lib/admin-api';

export default async function AdminTagsPage({
  params
}: {
  params: Promise<{locale: string}>;
}) {
  const {locale} = await params;
  setRequestLocale(locale);
  const t = await getTranslations('admin.tags');
  const tags = await getAdminTags();

  return (
    <section>
      <h1 className="font-mono text-2xl text-accent">&gt; {t('title')}_</h1>
      <TagManager tags={tags} />
    </section>
  );
}
