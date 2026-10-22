import {expect, test} from '@playwright/test';
import {loginAsAdmin} from './helpers';

test('admin can create, rename and delete a tag', async ({page}) => {
  const stamp = Date.now();
  const name = `E2E 标签 ${stamp}`;
  const slug = `e2e-tag-${stamp}`;
  const renamed = `E2E 改名 ${stamp}`;

  await loginAsAdmin(page);
  await page.getByRole('link', {name: '标签', exact: true}).click();
  await expect(page).toHaveURL(/\/zh\/admin\/tags$/);

  await page.getByLabel('名称').fill(name);
  await page.getByLabel('Slug').fill(slug);
  await page.getByRole('button', {name: '创建'}).click();

  const row = page.getByTestId(`admin-tag-${slug}`);
  await expect(row).toBeVisible();

  await row.getByRole('button', {name: '编辑'}).click();
  await row.getByLabel('名称').fill(renamed);
  await row.getByRole('button', {name: '保存'}).click();
  await expect(row).toContainText(renamed);

  page.once('dialog', async (dialog) => {
    expect(dialog.message()).toContain(renamed);
    await dialog.accept();
  });
  await row.getByRole('button', {name: '删除'}).click();
  await expect(row).toHaveCount(0);
  await page.reload();
  await expect(page.getByTestId(`admin-tag-${slug}`)).toHaveCount(0);
});

test('post tag links open the tag page and unknown tags are 404', async ({
  page
}) => {
  await page.goto('/zh/posts');

  const chips = page.getByRole('navigation', {name: '标签'});
  await expect(chips.getByRole('link', {name: /#后端/})).toBeVisible();

  const card = page.getByRole('article', {name: /第一篇测试文章/});
  await expect(card.getByRole('link', {name: '#后端'})).toBeVisible();

  await chips.getByRole('link', {name: /#后端/}).click();
  await expect(page).toHaveURL(/\/zh\/tags\/backend$/);
  await expect(
    page.locator('main').getByRole('heading', {level: 1})
  ).toContainText('后端');
  await expect(
    page.getByRole('link', {name: '第一篇测试文章'})
  ).toBeVisible();

  const response = await page.goto('/zh/tags/no-such-tag');
  expect(response?.status()).toBe(404);
  await expect(
    page.getByRole('heading', {name: '页面不存在'})
  ).toBeVisible();
});
