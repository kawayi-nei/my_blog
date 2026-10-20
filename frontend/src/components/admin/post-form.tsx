'use client';

import {zodResolver} from '@hookform/resolvers/zod';
import {useLocale, useTranslations} from 'next-intl';
import {useRouter} from 'next/navigation';
import {useEffect, useState} from 'react';
import {Controller, useForm} from 'react-hook-form';
import {z} from 'zod';
import MarkdownEditor from '@/components/admin/markdown-editor';
import {Link} from '@/i18n/navigation';
import type {AdminPostDetail, AdminTag} from '@/lib/admin-types';

const postSchema = z.object({
  title: z.string().trim().min(1).max(200),
  slug: z.string().regex(/^[a-z0-9-]+$/).max(200),
  language: z.enum(['zh', 'en']),
  status: z.enum(['draft', 'published']),
  excerpt: z.string().max(500),
  content_md: z.string(),
  tag_ids: z.array(z.number())
});

type FormValues = z.infer<typeof postSchema>;

function slugify(value: string) {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 200);
}

export default function PostForm({
  post,
  tags: initialTags
}: {
  post?: AdminPostDetail;
  tags: AdminTag[];
}) {
  const locale = useLocale();
  const router = useRouter();
  const t = useTranslations('admin.posts.form');
  const [tags, setTags] = useState(initialTags);
  const [slugTouched, setSlugTouched] = useState(Boolean(post));
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [newTagName, setNewTagName] = useState('');
  const [newTagSlug, setNewTagSlug] = useState('');
  const [tagError, setTagError] = useState<string | null>(null);

  const {
    register,
    control,
    handleSubmit,
    watch,
    setValue,
    getValues,
    formState: {errors, isSubmitting}
  } = useForm<FormValues>({
    resolver: zodResolver(postSchema),
    defaultValues: post
      ? {
          title: post.title,
          slug: post.slug,
          language: post.language,
          status: post.status,
          excerpt: post.excerpt,
          content_md: post.content_md,
          tag_ids: post.tags.map((tag) => tag.id)
        }
      : {
          title: '',
          slug: '',
          language: 'zh',
          status: 'draft',
          excerpt: '',
          content_md: '',
          tag_ids: []
        }
  });

  const title = watch('title');
  useEffect(() => {
    if (!slugTouched) {
      setValue('slug', slugify(title || ''));
    }
  }, [title, slugTouched, setValue]);

  async function onSubmit(values: FormValues) {
    setSubmitError(null);
    setSaved(false);
    const isEdit = Boolean(post);
    const response = await fetch(
      isEdit ? `/api/admin/posts/${post!.id}` : '/api/admin/posts',
      {
        method: isEdit ? 'PATCH' : 'POST',
        headers: {'content-type': 'application/json'},
        body: JSON.stringify(values)
      }
    );

    if (response.status === 401) {
      router.replace(`/${locale}/admin/login`);
      return;
    }
    if (response.status === 409) {
      setSubmitError(t('slugConflict'));
      return;
    }
    if (response.status === 422) {
      setSubmitError(t('invalid'));
      return;
    }
    if (!response.ok) {
      setSubmitError(t('saveFailed'));
      return;
    }

    const data = (await response.json()) as AdminPostDetail;
    if (!isEdit) {
      router.replace(`/${locale}/admin/posts/${data.id}/edit`);
      router.refresh();
      return;
    }
    setSaved(true);
    router.refresh();
  }

  async function createTag() {
    setTagError(null);
    const response = await fetch('/api/admin/tags', {
      method: 'POST',
      headers: {'content-type': 'application/json'},
      body: JSON.stringify({name: newTagName, slug: newTagSlug})
    });

    if (!response.ok) {
      setTagError(
        response.status === 409 ? t('tagConflict') : t('tagCreateFailed')
      );
      return;
    }

    const tag = (await response.json()) as AdminTag;
    setTags((current) => [...current, tag]);
    setValue('tag_ids', [...getValues('tag_ids'), tag.id]);
    setNewTagName('');
    setNewTagSlug('');
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="grid gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="font-mono text-2xl text-accent">
          &gt; {post ? t('editTitle') : t('createTitle')}_
        </h1>
        <Link href="/admin/posts" className="font-mono text-xs text-muted hover:text-accent">
          &lt; {t('back')}
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="grid gap-1">
          <span className="font-mono text-sm">{t('title')}</span>
          <input
            id="title"
            {...register('title')}
            className="rounded border border-border bg-surface px-3 py-2"
          />
          {errors.title ? (
            <span className="text-xs text-red-400">{t('titleRequired')}</span>
          ) : null}
        </label>

        <label className="grid gap-1">
          <span className="font-mono text-sm">{t('slug')}</span>
          <input
            id="slug"
            {...register('slug', {onChange: () => setSlugTouched(true)})}
            className="rounded border border-border bg-surface px-3 py-2 font-mono"
          />
          <span className="text-xs text-muted">{t('slugHint')}</span>
          {errors.slug ? (
            <span className="text-xs text-red-400">{t('slugRequired')}</span>
          ) : null}
        </label>

        <label className="grid gap-1">
          <span className="font-mono text-sm">{t('language')}</span>
          <select
            id="language"
            {...register('language')}
            className="rounded border border-border bg-surface px-3 py-2"
          >
            <option value="zh">中文</option>
            <option value="en">English</option>
          </select>
        </label>

        <label className="grid gap-1">
          <span className="font-mono text-sm">{t('status')}</span>
          <select
            id="status"
            {...register('status')}
            className="rounded border border-border bg-surface px-3 py-2"
          >
            <option value="draft">{t('statusDraft')}</option>
            <option value="published">{t('statusPublished')}</option>
          </select>
        </label>
      </div>

      <label className="grid gap-1">
        <span className="font-mono text-sm">{t('excerpt')}</span>
        <textarea
          id="excerpt"
          rows={3}
          {...register('excerpt')}
          className="rounded border border-border bg-surface px-3 py-2"
        />
        {errors.excerpt ? (
          <span className="text-xs text-red-400">{t('tooLong')}</span>
        ) : null}
      </label>

      <fieldset className="grid gap-3">
        <legend className="font-mono text-sm">{t('tags')}</legend>
        <Controller
          control={control}
          name="tag_ids"
          render={({field}) => (
            <div className="flex flex-wrap gap-3 font-mono text-xs">
              {tags.map((tag) => {
                const checked = field.value.includes(tag.id);
                return (
                  <label key={tag.id} className="flex items-center gap-1">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={(event) =>
                        field.onChange(
                          event.target.checked
                            ? [...field.value, tag.id]
                            : field.value.filter((id) => id !== tag.id)
                        )
                      }
                    />
                    #{tag.name}
                  </label>
                );
              })}
            </div>
          )}
        />

        <div className="flex flex-wrap items-end gap-2 font-mono text-xs">
          <label className="grid gap-1">
            <span className="text-muted">{t('tagName')}</span>
            <input
              value={newTagName}
              onChange={(event) => setNewTagName(event.target.value)}
              className="rounded border border-border bg-surface px-2 py-1"
            />
          </label>
          <label className="grid gap-1">
            <span className="text-muted">{t('tagSlug')}</span>
            <input
              value={newTagSlug}
              onChange={(event) => setNewTagSlug(event.target.value)}
              className="rounded border border-border bg-surface px-2 py-1"
            />
          </label>
          <button
            type="button"
            onClick={createTag}
            disabled={!newTagName || !newTagSlug}
            className="rounded border border-border px-3 py-1 hover:border-accent disabled:opacity-60"
          >
            {t('createTag')}
          </button>
          {tagError ? (
            <span className="text-red-400">{tagError}</span>
          ) : null}
        </div>
      </fieldset>

      <div className="grid gap-2">
        <label htmlFor="content_md" className="font-mono text-sm">
          {t('content')}
        </label>
        <Controller
          control={control}
          name="content_md"
          render={({field}) => (
            <MarkdownEditor value={field.value} onChange={field.onChange} />
          )}
        />
      </div>

      {submitError ? (
        <p className="font-mono text-xs text-red-400">{submitError}</p>
      ) : null}
      {saved ? (
        <p className="font-mono text-xs text-accent">{t('saved')}</p>
      ) : null}

      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded bg-accent px-4 py-2 font-mono text-sm font-semibold text-black disabled:opacity-60"
        >
          {isSubmitting ? t('saving') : t('save')}
        </button>
        <Link
          href="/admin/posts"
          className="rounded border border-border px-4 py-2 font-mono text-sm hover:border-accent"
        >
          {t('cancel')}
        </Link>
      </div>
    </form>
  );
}
