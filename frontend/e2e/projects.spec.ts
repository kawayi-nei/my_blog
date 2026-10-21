import {expect, test} from '@playwright/test';
import {loginAsAdmin} from './helpers';

test('admin can create, publish and delete a project', async ({page}) => {
  const stamp = Date.now();
  const titleZh = `E2E 项目 ${stamp}`;
  const titleEn = `E2E project ${stamp}`;
  const slug = `e2e-project-${stamp}`;

  await loginAsAdmin(page);

  await page.goto('/zh/admin/projects');
  await page.getByRole('link', {name: '新建项目'}).click();
  await expect(page).toHaveURL(/\/zh\/admin\/projects\/new$/);

  await page.getByLabel('中文标题').fill(titleZh);
  await page.getByLabel('英文标题').fill(titleEn);
  await page.locator('#slug').fill(slug);
  await page.getByLabel('中文正文').fill('# 项目简介\n\n这是 E2E 项目。');
  await page.getByLabel('英文正文').fill('# Project\n\nE2E project.');
  await page.getByLabel('技术栈').fill('PyTorch, FastAPI');
  await page.getByLabel('状态').selectOption('published');
  await page.getByRole('button', {name: '保存'}).click();

  await expect(page).toHaveURL(/\/zh\/admin\/projects\/\d+\/edit$/);
  const match = page.url().match(/\/admin\/projects\/(\d+)\/edit/);
  expect(match).not.toBeNull();
  const projectId = match![1];

  await page.goto('/zh/projects');
  await expect(page.getByRole('link', {name: titleZh})).toBeVisible();

  await page.getByRole('link', {name: titleZh}).click();
  await expect(page.locator('article header h1')).toHaveText(titleZh);
  await expect(page.locator('article')).toContainText('PyTorch');

  await page.goto('/zh/admin/projects');
  const row = page.getByTestId(`admin-project-${projectId}`);
  await expect(row).toBeVisible();

  page.once('dialog', (dialog) => dialog.accept());
  await row.getByRole('button', {name: '删除'}).click();
  await expect(page.getByTestId(`admin-project-${projectId}`)).toHaveCount(0);
});
