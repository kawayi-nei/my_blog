import {execFileSync} from 'node:child_process';
import path from 'node:path';

export default function globalSetup() {
  const backendDir = path.resolve(process.cwd(), '../backend');
  const python =
    process.platform === 'win32'
      ? path.join('venv', 'Scripts', 'python.exe')
      : path.join('venv', 'bin', 'python');

  execFileSync(path.join(backendDir, python), ['-m', 'app.scripts.seed_demo'], {
    cwd: backendDir,
    stdio: 'inherit'
  });
}
