"""SEC-007: autostart desktop path must not be written via symlink or non-regular file."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.config_manager import ConfigManager


@pytest.fixture
def autostart_dir(tmp_path: Path) -> Path:
    d = tmp_path / 'autostart'
    d.mkdir()
    return d


def test_save_to_regular_file_ok(autostart_dir: Path) -> None:
    cm = ConfigManager(autostart_dir=autostart_dir)
    r = cm.saveToAutostart('xgamma -rgamma 1 -ggamma 1 -bgamma 1')
    assert r.ok
    assert cm.desktopFile.is_file()
    assert 'Exec=xgamma' in cm.desktopFile.read_text(encoding='utf-8')


def test_save_refuses_symlink(autostart_dir: Path) -> None:
    victim = autostart_dir.parent / 'symlink_target.txt'
    victim.write_text('KEEP', encoding='utf-8')
    link = autostart_dir / ConfigManager.DESKTOP_BASENAME
    try:
        os.symlink(victim, link)
    except OSError:
        pytest.skip('symlink creation not supported in this environment')
    cm = ConfigManager(autostart_dir=autostart_dir)
    r = cm.saveToAutostart('xgamma -gamma 2')
    assert not r.ok
    assert r.error_message and 'symlink' in r.error_message
    assert victim.read_text(encoding='utf-8') == 'KEEP'


def test_save_refuses_directory_at_desktop_path(autostart_dir: Path) -> None:
    blocker = autostart_dir / ConfigManager.DESKTOP_BASENAME
    blocker.mkdir()
    cm = ConfigManager(autostart_dir=autostart_dir)
    r = cm.saveToAutostart('xgamma -gamma 1')
    assert not r.ok
    assert r.error_message and 'regular file' in r.error_message
