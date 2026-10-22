import {expect, test} from '@playwright/test';

test('search page finds seeded posts and shows empty states', async ({
  page
}) => {
  await page.goto('/zh');
  await expect(
    page.getByRole('link', {name: '搜索', exact: true})
  ).toBeVisible();

  await page.goto('/zh/search');
  await expect(page.getByText('输入关键词开始搜索。')).toBeVisible();
  await expect(
    page.locator('main').getByRole('heading', {level: 2})
  ).toHaveCount(0);

  await page.getByLabel('搜索关键词').fill('第一篇');
  await page.getByRole('button', {name: '搜索'}).click();
  await expect(page).toHaveURL(/\/zh\/search\?q=/);
  await expect(
    page.getByRole('link', {name: '第一篇测试文章'})
  ).toBeVisible();

  await page.goto('/zh/search?q=zzzz-not-found');
  await expect(page.getByText('没有找到匹配的内容。')).toBeVisible();
});
