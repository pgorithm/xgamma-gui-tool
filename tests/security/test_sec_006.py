"""SEC-006: Autostart directory under Path.home()/.config/autostart, fixed desktop name."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.security
def test_autostart_is_home_dot_config_autostart_fixed_desktop_name(tmp_path: Path) -> None:
    """Path follows Path.home() (HOME / USERPROFILE); filename is literal xgamma_gui_tool.desktop."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    xdg_alt = tmp_path / "xdg_alt"
    xdg_alt.mkdir()
    script = tmp_path / "sec006_subproc.py"
    body = f"""
import os, sys
from pathlib import Path
ROOT = Path({repr(str(REPO_ROOT))})
sys.path.insert(0, str(ROOT))
os.environ["HOME"] = {repr(str(fake_home))}
os.environ["XDG_CONFIG_HOME"] = {repr(str(xdg_alt))}
if sys.platform == "win32":
    os.environ["USERPROFILE"] = {repr(str(fake_home))}

import src.config_manager as cm

expected_dir = Path({repr(str(fake_home))}) / ".config" / "autostart"
expected_file = expected_dir / "xgamma_gui_tool.desktop"
assert cm.ConfigManager.AUTOSTART_DIR == expected_dir, cm.ConfigManager.AUTOSTART_DIR
assert cm.ConfigManager.DESKTOP_FILE == expected_file, cm.ConfigManager.DESKTOP_FILE
assert not str(cm.ConfigManager.DESKTOP_FILE).startswith({repr(str(xdg_alt))})
print("ok")
"""
    script.write_text(body, encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    assert "ok" in proc.stdout


@pytest.mark.security
def test_config_manager_source_fixed_relative_segments() -> None:
    """Static check: no getenv for autostart path; fixed .desktop basename."""
    src = REPO_ROOT / "src" / "config_manager.py"
    text = src.read_text(encoding="utf-8")
    assert "xgamma_gui_tool.desktop" in text
    assert "Path.home()" in text
    assert ".config" in text and "autostart" in text
    assert "XDG_CONFIG_HOME" not in text
    assert "getenv" not in text
