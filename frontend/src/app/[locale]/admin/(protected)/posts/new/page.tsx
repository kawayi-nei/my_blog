import {setRequestLocale} from 'next-intl/server';
import PostForm from '@/components/admin/post-form';
import {getAdminTags} from '@/lib/admin-api';

export default async function NewPostPage({
  params
}: {
  params: Promise<{locale: string}>;
}) {
  const {locale} = await params;
  setRequestLocale(locale);
  const tags = await getAdminTags();
  return <PostForm tags={tags} />;
}
