from __future__ import annotations

import os
from pathlib import Path

from .snapshot import create_snapshot_archive, cleanup_old_cache_files
from .gdrive import upload_snapshot
from .log import get_logger


logger = get_logger("backup.main")


def is_interactive_run() -> bool:
    """
    You should run manually once to authorize.
    For cron/systemd runs, this must be False.

    Set BACKUP_INTERACTIVE=1 to force interactive mode.
    """
    return os.environ.get("BACKUP_INTERACTIVE", "").strip() == "1"


def main() -> int:
    try:
        cwd = Path.cwd()

        logger.info(f"Backup working directory: {cwd}")

        # Create snapshot archive
        snap = create_snapshot_archive(source_dir=cwd)

        # Upload to Drive
        upload_snapshot(snap.archive_path, interactive=is_interactive_run())

        # Cleanup old cache files after successful upload (keep only the most recent)
        cache_dir = cwd / ".backup_cache"
        cleanup_old_cache_files(cache_dir, snap.archive_path)

        logger.info("Backup completed successfully.")
        return 0

    except Exception as e:
        logger.error(f"Backup failed: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
