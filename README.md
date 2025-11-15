# File Server

A minimal, local file server built with Flask that renders a friendly HTML directory listing.

This repository serves files from a configured directory and provides an attractive, client-side searchable
and sortable index using the template at `src/views/files.html`.

**Key features**
- **Simple**: single-file server logic in `src/main.py`.
- **Safe-ish**: prevents path traversal outside the configured base directory.
- **Pretty UI**: `src/views/files.html` provides filtering and column sorting in the browser.
- **Hidden folders**: directories containing a file named `.hide` are excluded from listings.

**Repository layout**
- `src/main.py`: application entrypoint and browsing logic.
- `src/views/files.html`: Jinja2 template used to render directory listings.
- `requirements.txt`: Python dependencies.

## Requirements
- Python 3.8+
- The project dependencies listed in `requirements.txt` (Flask).

## Install
Create and activate a virtual environment, then install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run
You can run the server from the repository root. By default it serves the parent directory of `src/`.

```bash
# serve the default directory
python src/main.py

# serve a specific directory
python src/main.py --dir /path/to/serve --host 0.0.0.0 --port 8000

# or set the environment variable
export FILE_DIR=/path/to/serve
python src/main.py
```

Open your browser at `http://localhost:8000/` (or the host/port you provided).

## Environment & Options
- `--dir, -d`: the directory to serve (overrides `FILE_DIR` environment variable).
- `--host, -H`: host to bind to (default `0.0.0.0`).
- `--port, -p`: port to listen on (default `8000`).
- `FILE_DIR`: environment variable alternative to `--dir`.

## Template
The HTML index is at `src/views/files.html`. It includes client-side JavaScript for:
- filtering by name/type
- sorting columns (name, modified, size, type)

You can customize the template to change styling or add features such as icons, thumbnails, or download controls.

## Security notes
- This server is intended for local or trusted-network use only. Do not expose it publicly without adding
  authentication and additional security controls.
- The server prevents directory traversal by checking that resolved paths start with the configured base directory.

## Contributing
Bug reports and small improvements are welcome. Suggested contributions:
- Improve MIME type handling or previews.
- Add optional authentication or access controls.
- Add unit tests and CI workflows.

## Systemd service
You can create a systemd service unit using the included `create-service.py` utility.

- Dry-run (preview the unit):

```bash
./create-service.py --dir . --user --dry-run
```

- Create a user service, bootstrap a `.venv`, install `requirements.txt`, install and start it:

```bash
./create-service.py --dir . --user --install --bootstrap --force
```

This will create (or reuse) `.venv` in the repo, install dependencies into it, write the unit to
`~/.config/systemd/user/<slug>.service`, reload the user systemd daemon, enable and start the service.

- Create a system-wide service (requires sudo):

```bash
sudo ./create-service.py --dir /srv/files --install --force
```

- View logs for the user service:

```bash
journalctl --user -u file-server.service -f
```

- Stop / disable:

```bash
systemctl --user stop file-server.service
systemctl --user disable file-server.service
```

Notes:
- For user services you may need to enable lingering if you want the service kept running without a user session: `loginctl enable-linger $USER`.
- The `--bootstrap` flag creates `.venv` and installs `requirements.txt`; activation is not required because the script uses the venv's python directly.

## License
This project is available under the MIT License. See the `LICENSE` file for details.
