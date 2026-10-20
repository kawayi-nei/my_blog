import {expect, test} from '@playwright/test';

test('home page loads with hero and navigation', async ({page}) => {
  await page.goto('/zh');
  await expect(page.getByRole('heading', {level: 1})).toContainText('彭科道');
  await expect(page.getByText('记录遥感、水利与代码。')).toBeVisible();
  await expect(
    page.getByRole('link', {name: '文章', exact: true})
  ).toBeVisible();
});

test('posts list and detail render seeded content', async ({page}) => {
  await page.goto('/zh');
  await page.getByRole('link', {name: '文章', exact: true}).click();
  await expect(page).toHaveURL(/\/zh\/posts$/, {timeout: 15_000});
  await expect(
    page.locator('main').getByRole('heading', {level: 1, name: /文章/})
  ).toBeVisible();

  await page
    .getByRole('link', {name: '第一篇测试文章', exact: true})
    .first()
    .click();
  await expect(page.locator('article header h1')).toHaveText(
    '第一篇测试文章'
  );
  await expect(page.locator('pre code').first()).toContainText(
    "print('hello')"
  );
});

test('unknown post renders localized 404 inside the site shell', async ({
  page
}) => {
  const response = await page.goto('/zh/posts/no-such-post');
  expect(response?.status()).toBe(404);
  await expect(
    page.getByRole('heading', {name: '页面不存在'})
  ).toBeVisible();
  await expect(
    page.getByRole('link', {name: '返回首页'})
  ).toBeVisible();
  await expect(page.getByRole('banner')).toBeVisible();
});

test('language switch changes UI copy', async ({page}) => {
  await page.goto('/zh');
  await page
    .getByRole('link', {name: 'Switch to English', exact: true})
    .click();
  await expect(page).toHaveURL(/\/en$/);
  await expect(
    page.getByRole('link', {name: 'Posts', exact: true})
  ).toBeVisible();
  await expect(page.getByRole('heading', {level: 1})).toContainText(
    'Peng Kedao'
  );
});
