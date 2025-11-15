#!/usr/bin/env python3
"""create-service.py

Create and optionally install a systemd service unit for this file server.

Usage examples:
  # show unit file
  python create-service.py --name "File Server" --dir /srv/files --dry-run

  # write and enable the unit (requires password or root)
  python create-service.py --name "File Server" --dir /srv/files --install --enable --start

The script will try to locate a suitable Python executable (prefer `python3`).
"""

from pathlib import Path
import argparse
import shutil
import os
import sys
import re
import subprocess
import textwrap


def ask(prompt, default=None):
  if default:
    prompt = f"{prompt} [{default}]"
  try:
    while True:
      val = input(f"{prompt}: ").strip()
      if not val and default is not None:
        return default
      if val:
        return val
  except KeyboardInterrupt:
    print()
    sys.exit(1)


def find_python(prefer=('python3', 'python')):
  """Return the path to a python executable or None."""
  for name in prefer:
    path = shutil.which(name)
    if path:
      return path
  return None


def slugify(name: str) -> str:
  s = name.lower()
  s = re.sub(r'[^a-z0-9]+', '-', s)
  s = re.sub(r'-{2,}', '-', s)
  return s.strip('-') or 'file-server'


def build_unit(name: str, directory: str, port: int, host: str, python_executable: str, script_path: str) -> str:
  slug = slugify(name)
  wd = Path(script_path).parent.resolve()
  directory = str(Path(directory).resolve())
  unit = textwrap.dedent(f"""
  [Unit]
  Description={name} File Server Service
  After=network.target

  [Service]
  Type=simple
  WorkingDirectory={wd}
  ExecStart={python_executable} {script_path} --dir "{directory}" --host {host} --port {port}
  Restart=on-failure
  RestartSec=5
  StandardOutput=journal
  StandardError=journal

  [Install]
  WantedBy=multi-user.target
  """)
  return slug, unit


def write_unit(dest: str, content: str, force: bool = False, user: bool = False) -> None:
  dest_path = Path(dest)
  if dest_path.exists() and not force:
    raise FileExistsError(f"{dest} exists; use --force to overwrite")
  if user:
    dest_path.write_text(content)
    return
  if os.geteuid() == 0:
    dest_path.write_text(content)
    return
  p = subprocess.run(['sudo', 'tee', dest], input=content.encode(), check=False)
  if p.returncode != 0:
    raise RuntimeError("failed to write unit via sudo")


def systemctl(cmd: str, unit: str = None, use_sudo=True, user_mode=False):
  args = []
  if use_sudo and os.geteuid() != 0 and not user_mode:
    args.append('sudo')
  args.append('systemctl')
  if user_mode:
    args.append('--user')
  args.extend(cmd.split())
  if unit:
    args.append(unit)
  return subprocess.run(args, check=False)


def main():
  p = argparse.ArgumentParser(description='Create a systemd service for the file server')
  p.add_argument('--name', '-n', default='File Server', help='Service display name')
  p.add_argument('--dir', '-d', required=True, help='Directory to serve')
  p.add_argument('--port', '-p', type=int, default=8000, help='Port to serve on')
  p.add_argument('--host', '-H', default='0.0.0.0', help='Host to bind')
  p.add_argument('--python', help='Python executable to use (absolute path)')
  p.add_argument('--bootstrap', action='store_true', help='Create/use .venv in repo, install requirements.txt into it')
  p.add_argument('--install', action='store_true', help='Install unit into /etc/systemd/system')
  p.add_argument('--user', action='store_true', help='Create a user service (~/.config/systemd/user) and use systemctl --user')
  p.add_argument('--enable', action='store_true', help='Enable the service after installing')
  p.add_argument('--start', action='store_true', help='Start the service after enabling')
  p.add_argument('--dry-run', action='store_true', help='Print the unit file and exit')
  p.add_argument('--force', action='store_true', help='Overwrite existing unit if present')
  args = p.parse_args()

  script_path = str(Path(__file__).parent.resolve() / 'src' / 'main.py')
  if not Path(script_path).exists():
    print(f"Error: expected script at {script_path} not found", file=sys.stderr)
    sys.exit(2)

  python_exe = args.python or find_python()
  if not python_exe:
    print('Could not locate a python executable. Specify with --python', file=sys.stderr)
    sys.exit(2)

  if not Path(args.dir).exists():
    print(f"Error: directory {args.dir} does not exist", file=sys.stderr)
    resp = ask('Create it now?', 'y')
    if resp.lower().startswith('y'):
      Path(args.dir).mkdir(parents=True, exist_ok=True)
    else:
      sys.exit(2)

  # Optionally bootstrap or use a project .venv. If --bootstrap is set, create it.
  venv_dir = Path.cwd() / '.venv'
  try:
    if args.bootstrap or venv_dir.exists():
      if not venv_dir.exists():
        print('Creating virtual environment at .venv...')
        subprocess.run([python_exe, '-m', 'venv', str(venv_dir)], check=True)

      venv_python = str(venv_dir / 'bin' / 'python')
      if not Path(venv_python).exists():
        raise RuntimeError(f"venv python not found at {venv_python}")

      req_file = Path.cwd() / 'requirements.txt'
      if req_file.exists():
        print('Installing requirements into .venv...')
        subprocess.run([venv_python, '-m', 'pip', 'install', '-r', str(req_file)], check=True)

      # prefer venv python unless user explicitly passed --python
      if not args.python:
        python_exe = venv_python
        print(f'Using virtualenv python: {python_exe}')
  except subprocess.CalledProcessError as e:
    print('Failed to create venv or install requirements:', e, file=sys.stderr)
    sys.exit(1)
  except Exception as e:
    print('Error preparing virtualenv:', e, file=sys.stderr)
    sys.exit(1)

  slug, unit = build_unit(args.name, args.dir, args.port, args.host, python_exe, script_path)
  if args.user:
    user_dir = Path(os.path.expanduser('~')) / '.config' / 'systemd' / 'user'
    user_dir.mkdir(parents=True, exist_ok=True)
    dest = str(user_dir / f'{slug}.service')
  else:
    dest = f"/etc/systemd/system/{slug}.service"

  if args.dry_run:
    print('# Unit file would be written to:', dest)
    print(unit)
    return

  if not args.install:
    print('# Unit file preview: (use --install to write)')
    print(unit)
    return

  try:
    write_unit(dest, unit, force=args.force, user=args.user)
  except FileExistsError as e:
    print(e, file=sys.stderr)
    sys.exit(1)
  except Exception as e:
    print('Failed to write unit:', e, file=sys.stderr)
    sys.exit(1)

  print(f'Wrote unit to {dest}')

  # reload systemd manager configuration, then enable and start the service
  print('Reloading systemd daemon...')
  r = systemctl('daemon-reload', user_mode=args.user)
  if r.returncode != 0:
    print('Warning: `systemctl daemon-reload` returned non-zero', file=sys.stderr)

  print('Enabling service...')
  r = systemctl('enable', unit=f'{slug}.service', user_mode=args.user)
  if r.returncode != 0:
    print('Warning: failed to enable service', file=sys.stderr)
  else:
    print('Service enabled')

  print('Starting service...')
  r = systemctl('start', unit=f'{slug}.service', user_mode=args.user)
  if r.returncode != 0:
    print('Warning: failed to start service', file=sys.stderr)
  else:
    print('Service started')


if __name__ == '__main__':
  main()

