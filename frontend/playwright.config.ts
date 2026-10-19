import {defineConfig, devices} from '@playwright/test';
import path from 'node:path';

const backendDir = path.resolve(__dirname, '../backend');
const python =
  process.platform === 'win32'
    ? path.join(backendDir, 'venv', 'Scripts', 'python.exe')
    : path.join(backendDir, 'venv', 'bin', 'python');

export default defineConfig({
  testDir: './e2e',
  globalSetup: './e2e/global-setup.ts',
  fullyParallel: true,
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
      command: `"${python}" -m uvicorn app.main:app --host 127.0.0.1 --port 8000`,
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
