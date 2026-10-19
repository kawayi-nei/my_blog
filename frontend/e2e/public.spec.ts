import {expect, test} from '@playwright/test';

test('home page loads with hero and navigation', async ({page}) => {
  await page.goto('/zh');
  await expect(page.getByRole('heading', {level: 1})).toContainText('彭科道');
  await expect(
    page.getByRole('link', {name: '文章', exact: true})
  ).toBeVisible();
});

test('posts list and detail render seeded content', async ({page}) => {
  await page.goto('/zh');
  await page.getByRole('link', {name: '文章', exact: true}).click();
  await expect(page).toHaveURL(/\/zh\/posts$/);
  await expect(
    page.getByRole('heading', {name: /文章/})
  ).toBeVisible();

  await page
    .getByRole('link', {name: '第一篇测试文章'})
    .first()
    .click();
  await expect(page.locator('article header h1')).toHaveText(
    '第一篇测试文章'
  );
  await expect(page.locator('pre code')).toContainText('print');
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
});
