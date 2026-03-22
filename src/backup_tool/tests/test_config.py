"""Tests for config module."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from backup_tool.config import ConfigError, load_config, get_blacklist, get_token_file


@pytest.fixture
def temp_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "backup_config.json"
    config_path.write_text(
        json.dumps({"blacklist": [".git", "venv", ".backup_cache"]}),
        encoding="utf-8",
    )
    return config_path


class TestLoadConfig:
    def test_missing_config_raises(self) -> None:
        with patch("backup_tool.config.CONFIG_PATH", Path("/nonexistent/backup_config.json")):
            with patch("backup_tool.config.load_dotenv"):
                with pytest.raises(ConfigError, match="Config file not found"):
                    load_config()

    def test_valid_config_loads(
        self, temp_config: Path,
    ) -> None:
        with patch("backup_tool.config.CONFIG_PATH", temp_config):
            with patch("backup_tool.config.load_dotenv"):
                with patch.dict(
                    os.environ,
                    {"GOOGLE_CLIENT_ID": "cid", "GOOGLE_CLIENT_SECRET": "csec"},
                    clear=False,
                ):
                    data = load_config()
                    assert data["blacklist"] == [".git", "venv", ".backup_cache"]
                    assert data["GOOGLE_CLIENT_ID"] == "cid"
                    assert data["GOOGLE_CLIENT_SECRET"] == "csec"
                    assert data["GDRIVE_BACKUPS_FOLDER"] == "backups"
                    assert data["TOKEN_FILE"] == "gdrive_token.json"

    def test_missing_credentials_raises(self, temp_config: Path) -> None:
        with patch("backup_tool.config.CONFIG_PATH", temp_config):
            with patch("backup_tool.config.load_dotenv"):
                with patch.dict(os.environ, {}, clear=True):
                    with pytest.raises(ConfigError, match="GOOGLE_CLIENT_ID"):
                        load_config()

    def test_env_overrides_defaults(
        self, temp_config: Path,
    ) -> None:
        with patch("backup_tool.config.CONFIG_PATH", temp_config):
            with patch("backup_tool.config.load_dotenv"):
                with patch.dict(
                    os.environ,
                    {
                        "GOOGLE_CLIENT_ID": "x",
                        "GOOGLE_CLIENT_SECRET": "y",
                        "GDRIVE_BACKUPS_FOLDER": "mybackups",
                        "TOKEN_FILE": "my_token.json",
                    },
                    clear=False,
                ):
                    data = load_config()
                    assert data["GDRIVE_BACKUPS_FOLDER"] == "mybackups"
                    assert data["TOKEN_FILE"] == "my_token.json"


class TestConfigHelpers:
    def test_get_blacklist(
        self, temp_config: Path,
    ) -> None:
        with patch("backup_tool.config.CONFIG_PATH", temp_config):
            with patch("backup_tool.config.load_dotenv"):
                with patch.dict(
                    os.environ,
                    {"GOOGLE_CLIENT_ID": "a", "GOOGLE_CLIENT_SECRET": "b"},
                    clear=False,
                ):
                    assert get_blacklist() == [".git", "venv", ".backup_cache"]

    def test_get_token_file(
        self, temp_config: Path,
    ) -> None:
        with patch("backup_tool.config.CONFIG_PATH", temp_config):
            with patch("backup_tool.config.load_dotenv"):
                with patch.dict(
                    os.environ,
                    {"GOOGLE_CLIENT_ID": "a", "GOOGLE_CLIENT_SECRET": "b"},
                    clear=False,
                ):
                    assert get_token_file() == "gdrive_token.json"
