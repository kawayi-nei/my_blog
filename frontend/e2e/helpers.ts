import {expect, type Page} from '@playwright/test';

export async function loginAsAdmin(page: Page) {
  const username = process.env.E2E_ADMIN_USERNAME ?? 'admin';
  const password = process.env.E2E_ADMIN_PASSWORD ?? '';

  await page.goto('/zh/admin/posts');
  await expect(page).toHaveURL(/\/zh\/admin\/login$/);
  await page.getByLabel('用户名').fill(username);
  await page.getByLabel('密码').fill(password);
  await page.getByRole('button', {name: '登录'}).click();
  await expect(page).toHaveURL(/\/zh\/admin\/posts$/);
}
