# Ubuntu systemd timer for Python backup (venv)

How to run the backup on Ubuntu with a **systemd service + timer** and a virtual environment.

- **What gets backed up:** whatever directory you set as `WorkingDirectory` (below: `/home/pmpmt` — VPS with tools_custom).
- **Entry point:** `python -m backup_tool.main` (package in `src/backup_tool/`).
- **Virtualenv:** often `backup_tool/.venv` at the repo root (adjust if elsewhere).
- **Schedule:** every **1 hour** (change in the timer unit).

**Config files** (loaded from package directory and repo root):

- **`.env`** at repository root — OAuth client ID/secret and Drive-related options (copy from `.env.example`).
- **`src/backup_tool/backup_config.json`** — **`blacklist` only** (copy from `src/backup_tool/backup_config.json.example.json`).

**Logs:** script output appears in **journald**; the app also appends to **`src/backup_tool/backup.log`**.

Assume the project already runs manually before you automate it.

---

## 1. Verify that the script runs manually

```bash
cd /home/pmpmt

# PYTHONPATH must include backup_tool/src
PYTHONPATH=/home/pmpmt/tools_custom/backup_tool/src \
  /home/pmpmt/tools_custom/backup_tool/.venv/bin/python -m backup_tool.main
```

Fix dependencies, `.env`, `backup_config.json`, and OAuth token paths before continuing.

---

## 2. Create the systemd service unit

```bash
sudo nano /etc/systemd/system/mybackup.service
```

Example:

```ini
[Unit]
Description=Backup script to Google Drive (uses venv)
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
User=pmpmt
Group=pmpmt

# Directory that is snapshotted (PWD for the backup) — VPS: /home/pmpmt + tools_custom
WorkingDirectory=/home/pmpmt

# Timer/cron runs must not wait for a browser
Environment=BACKUP_INTERACTIVE=0
Environment=PYTHONPATH=/home/pmpmt/tools_custom/backup_tool/src

# Credentials live in .env at repo root (loaded by python-dotenv); no need for
# Environment=GOOGLE_* in the unit unless you prefer systemd to inject them.

ExecStart=/home/pmpmt/tools_custom/backup_tool/.venv/bin/python -m backup_tool.main

NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
ReadWritePaths=/home/pmpmt

TimeoutStartSec=20min

[Install]
WantedBy=multi-user.target
```

Notes:

- `User=` / `Group=` — run as your normal user.
- `WorkingDirectory=` — controls **what folder** is backed up; keep it consistent with manual tests.
- `PYTHONPATH` — must include `.../backup_tool/src` so Python finds the package. `ExecStart=` uses the venv `python` and `-m backup_tool.main`.
- `ReadWritePaths=/home/pmpmt` covers tools_custom/backup_tool (config, token, log) and `.backup_cache/` under `WorkingDirectory`.

Save and exit (`Ctrl+O`, `Enter`, `Ctrl+X`).

---

## 3. Create the systemd timer unit (every 1 hour)

```bash
sudo nano /etc/systemd/system/mybackup.timer
```

```ini
[Unit]
Description=Run mybackup.service every 1 hour

[Timer]
OnBootSec=5min
OnUnitActiveSec=1h
Persistent=true
AccuracySec=1min
Unit=mybackup.service

[Install]
WantedBy=timers.target
```

- `OnBootSec=5min` — first run a few minutes after boot.
- `OnUnitActiveSec=1h` — later runs one hour after the previous run **completed**.
- `Persistent=true` — catch-up after downtime.

---

## 4. Reload systemd and enable the timer

```bash
sudo systemctl daemon-reload
sudo systemctl enable mybackup.timer
sudo systemctl start mybackup.timer
```

---

## 5. Check status and logs

### 5.1 Timer

```bash
systemctl status mybackup.timer
```

Expect `Active: active (waiting)` and a `Next elapse` time.

### 5.2 Service (after a run)

```bash
systemctl status mybackup.service
```

### 5.3 Journal (stdout/stderr from Python)

```bash
journalctl -u mybackup.service -n 50
journalctl -u mybackup.service -f
```

### 5.4 App log file

```bash
tail -n 50 /home/pmpmt/tools_custom/backup_tool/src/backup_tool/backup.log
```

---

## 6. Manual test via systemd (recommended)

```bash
sudo systemctl start mybackup.service
journalctl -u mybackup.service -n 50
```

---

## 7. Modifying or disabling the schedule

### 7.1 Change frequency

Edit `OnUnitActiveSec` in `mybackup.timer` (e.g. `30min`), then:

```bash
sudo systemctl daemon-reload
sudo systemctl restart mybackup.timer
```

### 7.2 Stop / disable timer

```bash
sudo systemctl stop mybackup.timer
sudo systemctl disable mybackup.timer
```

---

## 8. Common pitfalls and troubleshooting

1. **Venv / module not found**  
   Confirm `ExecStart` uses the venv that has `pip install -r requirements.txt` and that `PYTHONPATH` includes `.../backup_tool/src`.

2. **Works manually, fails under systemd**  
   - Missing or unreadable **`.env`** (repo root) or **`src/backup_tool/backup_config.json`** for the service user.  
   - **`ProtectHome` / `ReadWritePaths`:** the service user must be allowed to read config and write the token file and `backup.log`.  
   - Wrong **`WorkingDirectory`** (unexpected folder snapshotted or missing `.backup_cache` parent permissions).

3. **OAuth / “non-interactive” errors**  
   Run once with a browser on the machine:

   ```bash
   cd /home/pmpmt
   PYTHONPATH=/home/pmpmt/tools_custom/backup_tool/src \
     BACKUP_INTERACTIVE=1 /home/pmpmt/tools_custom/backup_tool/.venv/bin/python -m backup_tool.main
   ```

   Ensure timer runs with `BACKUP_INTERACTIVE=0` (or unset).

4. **Edits to unit files**  
   After any change to `*.service` or `*.timer`:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart mybackup.timer
   ```

---

## 9. Quick command summary

```bash
sudo nano /etc/systemd/system/mybackup.service
sudo nano /etc/systemd/system/mybackup.timer
sudo systemctl daemon-reload
sudo systemctl enable mybackup.timer
sudo systemctl start mybackup.timer
systemctl status mybackup.timer
systemctl status mybackup.service
journalctl -u mybackup.service -n 50
```

This runs `backup_tool.main` on your schedule using systemd, with config in **`.env`** (repo root) and **`src/backup_tool/backup_config.json`**.
