'use client';

import {zodResolver} from '@hookform/resolvers/zod';
import {useLocale, useTranslations} from 'next-intl';
import {useRouter} from 'next/navigation';
import {useState} from 'react';
import {useForm} from 'react-hook-form';
import {z} from 'zod';

const loginSchema = z.object({
  username: z.string().min(1),
  password: z.string().min(1)
});

type LoginValues = z.infer<typeof loginSchema>;

export default function LoginForm() {
  const t = useTranslations('admin.login');
  const locale = useLocale();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: {errors, isSubmitting}
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {username: '', password: ''}
  });

  async function onSubmit(values: LoginValues) {
    setError(null);
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: {'content-type': 'application/json'},
      body: JSON.stringify(values)
    });

    if (response.ok) {
      router.replace(`/${locale}/admin/posts`);
      router.refresh();
      return;
    }
    if (response.status === 401) {
      setError(t('invalid'));
    } else if (response.status === 429) {
      setError(t('rateLimited'));
    } else {
      setError(t('failed'));
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="mt-6 grid gap-4">
      <label className="grid gap-1 font-mono text-sm">
        <span>{t('username')}</span>
        <input
          id="username"
          autoComplete="username"
          {...register('username')}
          className="rounded border border-border bg-surface px-3 py-2"
        />
        {errors.username ? (
          <span className="text-xs text-red-400">{t('required')}</span>
        ) : null}
      </label>

      <label className="grid gap-1 font-mono text-sm">
        <span>{t('password')}</span>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          {...register('password')}
          className="rounded border border-border bg-surface px-3 py-2"
        />
        {errors.password ? (
          <span className="text-xs text-red-400">{t('required')}</span>
        ) : null}
      </label>

      {error ? <p className="font-mono text-xs text-red-400">{error}</p> : null}

      <button
        type="submit"
        disabled={isSubmitting}
        className="rounded bg-accent px-4 py-2 font-mono text-sm font-semibold text-black disabled:opacity-60"
      >
        {isSubmitting ? t('submitting') : t('submit')}
      </button>
    </form>
  );
}
