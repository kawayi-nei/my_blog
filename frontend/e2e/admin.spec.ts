import {expect, test} from '@playwright/test';

const username = process.env.E2E_ADMIN_USERNAME ?? 'admin';
const password = process.env.E2E_ADMIN_PASSWORD ?? '';

test('admin can log in, create, publish and delete a post', async ({page}) => {
  const stamp = Date.now();
  const title = `E2E 管理员文章 ${stamp}`;
  const slug = `e2e-admin-${stamp}`;

  await page.goto('/zh');
  await expect(page.getByRole('link', {name: '后台'})).toBeVisible();

  await page.goto('/zh/admin/posts');
  await expect(page).toHaveURL(/\/zh\/admin\/login$/);

  await page.getByLabel('用户名').fill(username);
  await page.getByLabel('密码').fill(password);
  await page.getByRole('button', {name: '登录'}).click();
  await expect(page).toHaveURL(/\/zh\/admin\/posts$/);

  await page.getByRole('link', {name: '新建文章'}).click();
  await expect(page).toHaveURL(/\/zh\/admin\/posts\/new$/);

  await page.getByLabel('标题').fill(title);
  await page.locator('#slug').fill(slug);
  await page.getByLabel('正文').fill('# E2E\n\n后台发布测试。');
  await page.getByRole('button', {name: '保存'}).click();

  await expect(page).toHaveURL(/\/zh\/admin\/posts\/\d+\/edit$/);
  const match = page.url().match(/\/admin\/posts\/(\d+)\/edit/);
  expect(match).not.toBeNull();
  const postId = match![1];

  await page.getByLabel('状态').selectOption('published');
  await page.getByRole('button', {name: '保存'}).click();
  await expect(page.getByText('已保存')).toBeVisible();

  await page.goto(`/zh/posts/${slug}`);
  await expect(page.locator('article header h1')).toHaveText(title);

  await page.goto('/zh/admin/posts');
  const row = page.getByTestId(`admin-post-${postId}`);
  await expect(row).toBeVisible();

  page.once('dialog', (dialog) => dialog.accept());
  await row.getByRole('button', {name: '删除'}).click();
  await expect(page.getByTestId(`admin-post-${postId}`)).toHaveCount(0);
});
