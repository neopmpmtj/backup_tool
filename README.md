# Google Drive snapshot backup (systemd)

This project creates a timestamped snapshot of the **current working directory** (PWD),
excluding blacklisted folders (e.g. `.venv`, `.git`, `node_modules`), and uploads it to Google Drive.

## Configuration (two places)

| Location | Purpose |
|----------|---------|
| [`src/backup_tool/backup_config.json`](src/backup_tool/backup_config.json) | **`blacklist` only** — path names to skip as whole directories |
| [`.env`](.env.example) at repository root | **Secrets and options** — OAuth client ID/secret, Drive folder name, token filename, retention, hostname subfolder (copy from [`.env.example`](.env.example)) |

OAuth tokens are stored in the package directory (default `src/backup_tool/gdrive_token.json`; name overridable via `TOKEN_FILE` in `.env`).

Runtime logs go to **stdout** and to **`src/backup_tool/backup.log`** (append).

Dependencies include **`python-dotenv`** (see [`requirements.txt`](requirements.txt)).

## Running tests

```bash
source .venv/bin/activate
pip install -r requirements.txt pytest
PYTHONPATH=src pytest
```

## What it guarantees

As long as the timer runs successfully:

- Every run produces a full snapshot of the directory state.
- Blacklisted folders are **skipped as whole directories** (fast, no log spam).
- No reliance on git for file discovery.

## Files you must create

From the repository root (the directory containing `src/` and `pyproject.toml`):

```bash
cd /home/pmpmt/tools_custom/backup_tool

cp src/backup_tool/backup_config.json.example.json src/backup_tool/backup_config.json
cp .env.example .env
```

Edit **`.env`**: set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and any optional variables (see comments in `.env.example`). Edit **`src/backup_tool/backup_config.json`** only to adjust `blacklist`.

Install dependencies (from repo root):

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## First-time authorization

Run once manually so the browser OAuth flow can create the token file. `cd` to the folder you want backed up (e.g. Documents), then run with `PYTHONPATH` pointing at your backup_tool `src`:

```bash
cd /home/pmpmt/Documents
PYTHONPATH=/home/pmpmt/tools_custom/backup_tool/src \
  BACKUP_INTERACTIVE=1 /home/pmpmt/tools_custom/backup_tool/.venv/bin/python -m backup_tool.main
```

After this, the systemd timer can run non-interactively.

## Run manually (non-interactive)

```bash
cd /home/pmpmt/Documents
PYTHONPATH=/home/pmpmt/tools_custom/backup_tool/src \
  /home/pmpmt/tools_custom/backup_tool/.venv/bin/python -m backup_tool.main
```

## Where local temp archives go

Archives are created in **`.backup_cache/`** under the working directory. They are uploaded to Drive; you can optionally clean old local archives yourself.

## Logs

- **Journald:** `journalctl -u mybackup.service -n 200 --no-pager`
- **Timer:** `journalctl -u mybackup.timer -n 50 --no-pager`
- **File:** `src/backup_tool/backup.log` (same messages as stdout, when the app logger is used)

## Troubleshooting

- **`ProtectHome=true` in systemd** must allow read/write to the tree that contains `.env` (repo root), `src/backup_tool/backup_config.json`, the token file, and `src/backup_tool/backup.log`. The sample unit below uses `ReadWritePaths` for both the backup_tool repo and the snapshotted directory.
- If OAuth was revoked, run the **First-time authorization** step again with `BACKUP_INTERACTIVE=1`.

---

## Example systemd unit (hardened)

Focused on correct **working directory**, **venv Python**, and **non-interactive** runs.

### `/etc/systemd/system/mybackup.service`

```ini
[Unit]
Description=Google Drive snapshot backup (project directory)
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot

User=pmpmt
Group=pmpmt

WorkingDirectory=/home/pmpmt/Documents

Environment=BACKUP_INTERACTIVE=0
Environment=PYTHONPATH=/home/pmpmt/tools_custom/backup_tool/src

ExecStart=/home/pmpmt/tools_custom/backup_tool/.venv/bin/python -m backup_tool.main

NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
ReadWritePaths=/home/pmpmt/Documents /home/pmpmt/tools_custom

TimeoutStartSec=20min

[Install]
WantedBy=multi-user.target
```

**Why these matter**

- `WorkingDirectory=` is the tree that gets snapshotted (here, your Documents folder).
- `Environment=BACKUP_INTERACTIVE=0` avoids hanging on a timer waiting for a browser.
- `PYTHONPATH` must include `.../backup_tool/src` so Python finds the package.
- `ReadWritePaths=` needs both the snapshotted dir (for `.backup_cache`) and the backup_tool repo (for config, token, log).

### `/etc/systemd/system/mybackup.timer`

```ini
[Unit]
Description=Run Google Drive snapshot backup hourly

[Timer]
OnBootSec=5min
OnUnitActiveSec=1h
Persistent=true
AccuracySec=1min
Unit=mybackup.service

[Install]
WantedBy=timers.target
```

### Install the units

Copy the service and timer from the repo, then reload and enable:

```bash
sudo cp /home/pmpmt/tools_custom/backup_tool/mybackup.service /home/pmpmt/tools_custom/backup_tool/mybackup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mybackup.timer
```

Manual one-shot:

```bash
sudo systemctl start mybackup.service
```

### Check status

```bash
systemctl status mybackup.service
systemctl status mybackup.timer
```

Full step-by-step notes for Ubuntu: [`ubuntu_systemd_python_backup_setup.md`](ubuntu_systemd_python_backup_setup.md).
