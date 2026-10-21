import {defineConfig, devices} from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

function loadAdminCredentials() {
  const envPath = path.resolve(__dirname, '../backend/.env');
  const values: Record<string, string> = {};
  if (!fs.existsSync(envPath)) {
    console.warn('backend/.env not found; admin e2e will be skipped');
    return values;
  }
  const lines = fs.readFileSync(envPath, 'utf8').split(/\r?\n/);
  for (const line of lines) {
    const match = /^([A-Z0-9_]+)=(.*)$/.exec(line.trim());
    if (!match) continue;
    let value = match[2];
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    values[match[1]] = value;
  }
  return values;
}

const adminEnv = loadAdminCredentials();
process.env.E2E_ADMIN_USERNAME = adminEnv.ADMIN_USERNAME ?? 'admin';
process.env.E2E_ADMIN_PASSWORD = adminEnv.ADMIN_PASSWORD ?? '';

const backendDir = path.resolve(__dirname, '../backend');
const python =
  process.platform === 'win32'
    ? path.join(backendDir, 'venv', 'Scripts', 'python.exe')
    : path.join(backendDir, 'venv', 'bin', 'python');

export default defineConfig({
  testDir: './e2e',
  globalSetup: './e2e/global-setup.ts',
  fullyParallel: true,
  workers: 1,
  timeout: 120_000,
  expect: {timeout: 20_000},
  retries: process.env.CI ? 2 : 0,
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'retain-on-failure'
  },
  projects: [
    {
      name: 'chromium',
      use: {...devices['Desktop Chrome']}
    }
  ],
  webServer: [
    {
      command: `"${python}" -m alembic upgrade head && "${python}" -m app.scripts.seed_demo && "${python}" -m app.scripts.create_admin && "${python}" -m uvicorn app.main:app --host 127.0.0.1 --port 8000`,
      cwd: backendDir,
      url: 'http://127.0.0.1:8000/api/health',
      reuseExistingServer: !process.env.CI,
      timeout: 60_000
    },
    {
      command: 'npm run dev',
      url: 'http://localhost:3000/zh',
      reuseExistingServer: !process.env.CI,
      timeout: 120_000
    }
  ]
});
