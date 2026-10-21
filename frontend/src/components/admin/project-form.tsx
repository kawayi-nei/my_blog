'use client';

import {zodResolver} from '@hookform/resolvers/zod';
import {useLocale, useTranslations} from 'next-intl';
import {useRouter} from 'next/navigation';
import {useEffect, useState} from 'react';
import {Controller, useForm} from 'react-hook-form';
import {z} from 'zod';
import CoverPicker from '@/components/admin/cover-picker';
import MarkdownEditor from '@/components/admin/markdown-editor';
import {Link} from '@/i18n/navigation';
import type {AdminProjectDetail} from '@/lib/admin-types';

const projectSchema = z.object({
  slug: z.string().regex(/^[a-z0-9-]+$/).max(200),
  title_zh: z.string().trim().min(1).max(200),
  title_en: z.string().trim().min(1).max(200),
  summary_zh: z.string().max(500),
  summary_en: z.string().max(500),
  content_md_zh: z.string(),
  content_md_en: z.string(),
  cover_url: z.string().nullable(),
  tech_stack: z.string(),
  repo_url: z.string().max(500),
  demo_url: z.string().max(500),
  started_on: z.string(),
  ended_on: z.string(),
  featured: z.boolean(),
  sort_order: z.number().int(),
  status: z.enum(['draft', 'published'])
});

type FormValues = z.infer<typeof projectSchema>;

function slugify(value: string) {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 200);
}

export default function ProjectForm({
  project
}: {
  project?: AdminProjectDetail;
}) {
  const locale = useLocale();
  const router = useRouter();
  const t = useTranslations('admin.projects.form');
  const [slugTouched, setSlugTouched] = useState(Boolean(project));
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const {
    register,
    control,
    handleSubmit,
    watch,
    setValue,
    formState: {errors, isSubmitting}
  } = useForm<FormValues>({
    resolver: zodResolver(projectSchema),
    defaultValues: project
      ? {
          slug: project.slug,
          title_zh: project.title_zh,
          title_en: project.title_en,
          summary_zh: project.summary_zh,
          summary_en: project.summary_en,
          content_md_zh: project.content_md_zh,
          content_md_en: project.content_md_en,
          cover_url: project.cover_url,
          tech_stack: project.tech_stack.join(', '),
          repo_url: project.repo_url ?? '',
          demo_url: project.demo_url ?? '',
          started_on: project.started_on ?? '',
          ended_on: project.ended_on ?? '',
          featured: project.featured,
          sort_order: project.sort_order,
          status: project.status
        }
      : {
          slug: '',
          title_zh: '',
          title_en: '',
          summary_zh: '',
          summary_en: '',
          content_md_zh: '',
          content_md_en: '',
          cover_url: null,
          tech_stack: '',
          repo_url: '',
          demo_url: '',
          started_on: '',
          ended_on: '',
          featured: false,
          sort_order: 0,
          status: 'draft'
        }
  });

  const titleEn = watch('title_en');
  useEffect(() => {
    if (!slugTouched) {
      setValue('slug', slugify(titleEn || ''));
    }
  }, [titleEn, slugTouched, setValue]);

  async function onSubmit(values: FormValues) {
    setSubmitError(null);
    setSaved(false);

    if (
      values.started_on &&
      values.ended_on &&
      values.ended_on < values.started_on
    ) {
      setSubmitError(t('dateOrder'));
      return;
    }

    const payload = {
      slug: values.slug,
      title_zh: values.title_zh.trim(),
      title_en: values.title_en.trim(),
      summary_zh: values.summary_zh,
      summary_en: values.summary_en,
      content_md_zh: values.content_md_zh,
      content_md_en: values.content_md_en,
      cover_url: values.cover_url,
      tech_stack: values.tech_stack
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean),
      repo_url: values.repo_url.trim() || null,
      demo_url: values.demo_url.trim() || null,
      started_on: values.started_on || null,
      ended_on: values.ended_on || null,
      featured: values.featured,
      sort_order: values.sort_order,
      status: values.status
    };

    const isEdit = Boolean(project);
    try {
      const response = await fetch(
        isEdit
          ? `/api/admin/projects/${project!.id}`
          : '/api/admin/projects',
        {
          method: isEdit ? 'PATCH' : 'POST',
          headers: {'content-type': 'application/json'},
          body: JSON.stringify(payload)
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

      const data = (await response.json()) as AdminProjectDetail;
      if (!isEdit) {
        router.replace(`/${locale}/admin/projects/${data.id}/edit`);
        router.refresh();
        return;
      }
      setSaved(true);
      router.refresh();
    } catch {
      setSubmitError(t('saveFailed'));
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="grid gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="font-mono text-2xl text-accent">
          &gt; {project ? t('editTitle') : t('createTitle')}_
        </h1>
        <Link
          href="/admin/projects"
          className="font-mono text-xs text-muted hover:text-accent"
        >
          &lt; {t('back')}
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="grid gap-1">
          <span className="font-mono text-sm">{t('titleZh')}</span>
          <input
            id="title_zh"
            {...register('title_zh')}
            className="rounded border border-border bg-surface px-3 py-2"
          />
          {errors.title_zh ? (
            <span className="text-xs text-red-400">{t('titleRequired')}</span>
          ) : null}
        </label>

        <label className="grid gap-1">
          <span className="font-mono text-sm">{t('titleEn')}</span>
          <input
            id="title_en"
            {...register('title_en')}
            className="rounded border border-border bg-surface px-3 py-2"
          />
          {errors.title_en ? (
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

        <label className="flex items-center gap-2 font-mono text-sm">
          <input type="checkbox" {...register('featured')} />
          <span>{t('featured')}</span>
        </label>

        <label className="grid gap-1">
          <span className="font-mono text-sm">{t('sortOrder')}</span>
          <input
            id="sort_order"
            type="number"
            {...register('sort_order', {valueAsNumber: true})}
            className="rounded border border-border bg-surface px-3 py-2"
          />
        </label>

        <label className="grid gap-1">
          <span className="font-mono text-sm">{t('startedOn')}</span>
          <input
            id="started_on"
            type="date"
            {...register('started_on')}
            className="rounded border border-border bg-surface px-3 py-2"
          />
        </label>

        <label className="grid gap-1">
          <span className="font-mono text-sm">{t('endedOn')}</span>
          <input
            id="ended_on"
            type="date"
            {...register('ended_on')}
            className="rounded border border-border bg-surface px-3 py-2"
          />
        </label>
      </div>

      <label className="grid gap-1">
        <span className="font-mono text-sm">{t('techStack')}</span>
        <input
          id="tech_stack"
          {...register('tech_stack')}
          className="rounded border border-border bg-surface px-3 py-2"
        />
        <span className="text-xs text-muted">{t('techStackHint')}</span>
      </label>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="grid gap-1">
          <span className="font-mono text-sm">{t('repoUrl')}</span>
          <input
            id="repo_url"
            {...register('repo_url')}
            className="rounded border border-border bg-surface px-3 py-2"
          />
        </label>
        <label className="grid gap-1">
          <span className="font-mono text-sm">{t('demoUrl')}</span>
          <input
            id="demo_url"
            {...register('demo_url')}
            className="rounded border border-border bg-surface px-3 py-2"
          />
        </label>
      </div>

      <Controller
        control={control}
        name="cover_url"
        render={({field}) => (
          <CoverPicker value={field.value} onChange={field.onChange} />
        )}
      />

      <fieldset className="grid gap-4">
        <legend className="font-mono text-sm text-accent">中文</legend>

        <label className="grid gap-1">
          <span className="font-mono text-sm">{t('summaryZh')}</span>
          <textarea
            id="summary_zh"
            rows={3}
            {...register('summary_zh')}
            className="rounded border border-border bg-surface px-3 py-2"
          />
        </label>

        <label htmlFor="content_md_zh" className="font-mono text-sm">
          {t('contentZh')}
        </label>
        <Controller
          control={control}
          name="content_md_zh"
          render={({field}) => (
            <MarkdownEditor
              id="content_md_zh"
              value={field.value}
              onChange={field.onChange}
            />
          )}
        />
      </fieldset>

      <fieldset className="grid gap-4">
        <legend className="font-mono text-sm text-accent">English</legend>

        <label className="grid gap-1">
          <span className="font-mono text-sm">{t('summaryEn')}</span>
          <textarea
            id="summary_en"
            rows={3}
            {...register('summary_en')}
            className="rounded border border-border bg-surface px-3 py-2"
          />
        </label>

        <label htmlFor="content_md_en" className="font-mono text-sm">
          {t('contentEn')}
        </label>
        <Controller
          control={control}
          name="content_md_en"
          render={({field}) => (
            <MarkdownEditor
              id="content_md_en"
              value={field.value}
              onChange={field.onChange}
            />
          )}
        />
      </fieldset>

      {submitError ? (
        <p role="alert" className="font-mono text-xs text-red-400">
          {submitError}
        </p>
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
          href="/admin/projects"
          className="rounded border border-border px-4 py-2 font-mono text-sm hover:border-accent"
        >
          {t('cancel')}
        </Link>
      </div>
    </form>
  );
}
