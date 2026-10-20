import {setRequestLocale} from 'next-intl/server';
import {notFound} from 'next/navigation';
import PostForm from '@/components/admin/post-form';
import {getAdminPostOrNull, getAdminTags} from '@/lib/admin-api';

export default async function EditPostPage({
  params
}: {
  params: Promise<{locale: string; id: string}>;
}) {
  const {locale, id} = await params;
  setRequestLocale(locale);

  const postId = Number(id);
  if (!Number.isSafeInteger(postId) || postId <= 0) notFound();

  const [post, tags] = await Promise.all([
    getAdminPostOrNull(postId),
    getAdminTags()
  ]);
  if (!post) notFound();

  return <PostForm post={post} tags={tags} />;
}
