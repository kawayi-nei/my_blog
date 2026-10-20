import {execFileSync} from 'node:child_process';
import {existsSync} from 'node:fs';
import path from 'node:path';

export default function globalSetup() {
  const backendDir = path.resolve(__dirname, '../../backend');

  if (!existsSync(path.join(backendDir, '.env'))) {
    throw new Error('backend/.env is required for E2E (database URL and admin credentials)');
  }

  const python =
    process.platform === 'win32'
      ? path.join(backendDir, 'venv', 'Scripts', 'python.exe')
      : path.join(backendDir, 'venv', 'bin', 'python');

  execFileSync(python, ['-m', 'alembic', 'upgrade', 'head'], {
    cwd: backendDir,
    stdio: 'inherit'
  });
  execFileSync(python, ['-m', 'app.scripts.seed_demo'], {
    cwd: backendDir,
    stdio: 'inherit'
  });
  execFileSync(python, ['-m', 'app.scripts.create_admin'], {
    cwd: backendDir,
    stdio: 'inherit'
  });
}
